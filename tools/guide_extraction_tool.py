import requests
import json
from typing import Dict, Any, Optional
from schemas import ChatState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 라우터 프롬프트에 사용될 도구 설명
guide_extraction_description = {
    "name": "guide_extraction",
    "description": "Git 레포지토리 분석 결과를 바탕으로 표준개발가이드, 공통코드화, 공통함수 가이드를 추출합니다. (예: \"이 프로젝트의 개발 가이드를 추출해줘\")"
}

# 가이드 추출을 위한 프롬프트 템플릿
GUIDE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 소프트웨어 개발 전문가입니다. 주어진 Git 레포지토리 분석 결과를 바탕으로 다음 3가지 가이드를 추출해주세요:

1. **표준개발가이드**: 코딩 스타일, 네이밍 컨벤션, 프로젝트 구조, 아키텍처 패턴 등
2. **공통코드화**: 중복 코드 패턴, 재사용 가능한 컴포넌트, 공통 모듈화 방안 등  
3. **공통함수 가이드**: 자주 사용되는 함수 패턴, 유틸리티 함수, 헬퍼 함수 등

각 가이드는 구체적이고 실용적인 내용으로 작성해주세요. 분석 결과에서 실제 코드 패턴과 구조를 참고하여 가이드를 만들어주세요.

응답 형식:
## 표준개발가이드
[구체적인 가이드 내용]

## 공통코드화 가이드  
[구체적인 가이드 내용]

## 공통함수 가이드
[구체적인 가이드 내용]"""),
    ("user", "Git 레포지토리 분석 결과:\n{analysis_data}\n\nGit 주소: {git_urls}")
])

def get_rag_analysis_result(analysis_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """CoE-RagPipeline에서 분석 결과를 가져옵니다."""
    try:
        # CoE-RagPipeline 서버 URL (기본값)
        rag_pipeline_url = "http://127.0.0.1:8001"
        
        if analysis_id:
            # 특정 분석 결과 조회
            response = requests.get(f"{rag_pipeline_url}/results/{analysis_id}")
        else:
            # 최신 분석 결과 목록 조회
            response = requests.get(f"{rag_pipeline_url}/results")
            if response.status_code == 200:
                results = response.json()
                if results:
                    # 가장 최근 완료된 분석 결과 선택
                    latest_result = max(results, key=lambda x: x.get('created_at', ''))
                    analysis_id = latest_result['analysis_id']
                    response = requests.get(f"{rag_pipeline_url}/results/{analysis_id}")
                else:
                    return None
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except requests.RequestException as e:
        print(f"RAG Pipeline 연결 오류: {e}")
        return None

def extract_git_urls_from_analysis(analysis_data: Dict[str, Any]) -> str:
    """분석 결과에서 Git URL들을 추출합니다."""
    git_urls = []
    
    if 'repositories' in analysis_data:
        for repo in analysis_data['repositories']:
            if 'git_info' in repo and 'remote_url' in repo['git_info']:
                git_urls.append(repo['git_info']['remote_url'])
    
    return ", ".join(git_urls) if git_urls else "Git URL 정보 없음"

def guide_extraction_node(state: ChatState) -> Dict[str, Any]:
    """Git 레포지토리 분석 결과를 바탕으로 개발 가이드를 추출합니다."""
    
    # 사용자 입력에서 analysis_id 추출 시도
    user_content = state.get("original_input", "")
    analysis_id = None
    
    # 간단한 패턴 매칭으로 analysis_id 추출
    words = user_content.split()
    for word in words:
        if len(word) > 30 and '-' in word:  # UUID 형태로 추정
            analysis_id = word
            break
    
    # RAG Pipeline에서 분석 결과 가져오기
    analysis_data = get_rag_analysis_result(analysis_id)
    
    if not analysis_data:
        return {
            "messages": [{
                "role": "assistant", 
                "content": "분석 결과를 찾을 수 없습니다. CoE-RagPipeline에서 먼저 Git 레포지토리 분석을 수행해주세요.\n\n사용법:\n1. CoE-RagPipeline에서 Git 레포지토리 분석 실행\n2. 분석 완료 후 analysis_id와 함께 가이드 추출 요청\n\n예시: \"analysis_id abc-123-def로 개발 가이드를 추출해줘\""
            }]
        }
    
    try:
        # Git URL 추출
        git_urls = extract_git_urls_from_analysis(analysis_data)
        
        # 분석 데이터를 JSON 문자열로 변환 (LLM이 읽기 쉽게)
        analysis_json = json.dumps(analysis_data, indent=2, ensure_ascii=False)
        
        # LLM 클라이언트 가져오기
        from llm_client import langchain_client
        
        # 가이드 추출 체인 실행
        chain = GUIDE_EXTRACTION_PROMPT | langchain_client | StrOutputParser()
        
        result = chain.invoke({
            "analysis_data": analysis_json,
            "git_urls": git_urls
        })
        
        return {
            "messages": [{
                "role": "assistant",
                "content": f"📋 **Git 레포지토리 개발 가이드 추출 완료**\n\n**분석 대상**: {git_urls}\n**분석 ID**: {analysis_data.get('analysis_id', 'N/A')}\n\n{result}"
            }],
            "extracted_guides": result,
            "analysis_id": analysis_data.get('analysis_id'),
            "git_urls": git_urls
        }
        
    except Exception as e:
        error_message = f"가이드 추출 중 오류가 발생했습니다: {str(e)}"
        print(f"ERROR in guide_extraction_node: {error_message}")
        return {
            "messages": [{
                "role": "system",
                "content": error_message
            }]
        }