import requests
import json
import re # New import
import httpx # New import
from typing import Dict, Any, Optional
from core.schemas import ChatState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools.utils import is_git_url_reachable # New import

def extract_git_url(text: str) -> Optional[str]:
    """텍스트에서 Git URL을 추출합니다."""
    # 간단한 Git URL 패턴 매칭 (더 정교한 패턴이 필요할 수 있음)
    match = re.search(r'https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:/[^\s]*)?', text)
    if match:
        return match.group(0)
    return None

async def trigger_rag_analysis(git_url: str) -> Optional[str]:
    """CoE-RagPipeline에 Git 레포지토리 분석을 요청합니다."""
    rag_pipeline_url = "http://127.0.0.1:8001" # CoE-RagPipeline URL
    analyze_url = f"{rag_pipeline_url}/api/v1/analyze"
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "repositories": [
                    {
                        "url": git_url,
                        "branch": "master"
                    }
                ],
                "include_ast": True,
                "include_tech_spec": True,
                "include_correlation": True
            }
            response = await client.post(analyze_url, json=payload, timeout=300) # 5분 타임아웃
            response.raise_for_status() # HTTP 오류 발생 시 예외 발생
            
            result = response.json()
            return result.get("analysis_id")
    except httpx.RequestError as e:
        print(f"CoE-RagPipeline 분석 요청 오류: {e}")
        return None
    except Exception as e:
        print(f"CoE-RagPipeline 분석 중 예외 발생: {e}")
        return None

# 라우터 프롬프트에 사용될 도구 설명
guide_extraction_description = {
    "name": "guide_extraction",
    "description": "Git 레포지토리 분석을 시작하고, 분석 결과를 바탕으로 표준개발가이드, 공통코드화, 공통함수 가이드를 추출합니다. (예: \"이 프로젝트의 개발 가이드를 추출해줘\" 또는 \"git repository에 대해 개발가이드 만들어줘. 주소는 https://github.com/ep-code-box/CoE-Backend\") Git 분석 결과가 이미 있다면 해당 analysis_id를 사용하여 가이드를 추출할 수도 있습니다. git(깃) 분석결과를 가져오기도 합니다.",
    "url_path": "/tools/guide-extraction"
}

# 가이드 추출을 위한 프롬프트 템플릿
GUIDE_EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""당신은 소프트웨어 개발 전문가입니다. 제공된 '컨텍스트'와 '사용자 질문'을 바탕으로 다음 3가지 가이드를 추출해주세요:

1. **표준개발가이드**: 코딩 스타일, 네이밍 컨벤션, 프로젝트 구조, 아키텍처 패턴 등
2. **공통코드화**: 중복 코드 패턴, 재사용 가능한 컴포넌트, 공통 모듈화 방안 등  
3. **공통함수 가이드**: 자주 사용되는 함수 패턴, 유틸리티 함수, 헬퍼 함수 등

각 가이드는 컨텍스트를 기반으로 구체적이고 실용적인 내용으로 작성해주세요.

응답 형식:
## 표준개발가이드
[구체적인 가이드 내용]
## 공통코드화 가이드  
[구체적인 가이드 내용]
## 공통함수 가이드
[구체적인 가이드 내용]

---
**컨텍스트:**
{context}

**사용자 질문:**
{question}
""")

def get_rag_analysis_result(analysis_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """CoE-RagPipeline에서 분석 결과를 가져옵니다."""
    try:
        # CoE-RagPipeline 서버 URL (기본값)
        rag_pipeline_url = "http://127.0.0.1:8001"
        
        if analysis_id:
            # 특정 분석 결과 조회
            response = requests.get(f"{rag_pipeline_url}/api/v1/results/{analysis_id}")
        else:
            # 최신 분석 결과 목록 조회
            response = requests.get(f"{rag_pipeline_url}/api/v1/results")
            if response.status_code == 200:
                results = response.json()
                if results:
                    # 가장 최근 완료된 분석 결과 선택
                    latest_result = max(results, key=lambda x: x.get('created_at', ''))
                    analysis_id = latest_result['analysis_id']
                    response = requests.get(f"{rag_pipeline_url}/api/v1/results/{analysis_id}")
                else:
                    return None
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except requests.RequestException as e:
        print(f"RAG Pipeline 연결 오류: {e}")
        return None

def search_rag_context(query: str, analysis_id: str, k: int = 5) -> str:
    """CoE-RagPipeline의 검색 API를 사용하여 관련 컨텍스트를 가져옵니다."""
    try:
        rag_pipeline_url = "http://127.0.0.1:8001"
        search_url = f"{rag_pipeline_url}/api/v1/search"
        params = {"query": query, "k": k}
        # analysis_id를 메타데이터 필터로 사용하여 검색 범위를 제한
        filter_metadata = {"analysis_id": analysis_id}
        
        response = requests.post(search_url, params=params, json={"filter": filter_metadata})
        
        if response.status_code == 200:
            results = response.json()
            # 검색 결과를 LLM이 이해하기 쉬운 형식의 문자열로 조합
            context_parts = []
            for i, res in enumerate(results):
                context_parts.append(f"문서 {i+1} (유사도: {res['score']:.2f}, 유형: {res['metadata'].get('document_type', 'N/A')}):\n{res['content']}")
            return "\n\n---\n\n".join(context_parts) if context_parts else "관련 컨텍스트를 찾을 수 없습니다."
        else:
            return f"검색 API 오류: {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return f"RAG Pipeline 검색 연결 오류: {e}"

def extract_git_urls_from_analysis(analysis_data: Dict[str, Any]) -> str:
    """분석 결과에서 Git URL들을 추출합니다."""
    git_urls = []
    
    if 'repositories' in analysis_data:
        for repo in analysis_data['repositories']:
            # 스키마 변경에 따라 경로 수정
            if 'repository' in repo and 'url' in repo['repository']:
                git_urls.append(repo['repository']['url'])
    
    return ", ".join(git_urls) if git_urls else "Git URL 정보 없음"

async def guide_extraction_node(state: ChatState) -> Dict[str, Any]:
    """Git 레포지토리 분석 결과를 바탕으로 개발 가이드를 추출합니다."""
    
    print("DEBUG: Entering guide_extraction_node")
    # 사용자 입력에서 analysis_id 추출 시도
    user_content = state.get("original_input", "")
    user_question = user_content # 원본 질문 저장
    print(f"DEBUG: user_content = {user_content}")
    analysis_id = None
    
    # 간단한 패턴 매칭으로 analysis_id 추출
    words = user_content.split()
    for word in words:
        # "analysis_id" 키워드 바로 다음 단어를 ID로 간주
        if "analysis_id" in user_question.lower() and len(word) > 30 and '-' in word:
            analysis_id = word
            break
    print(f"DEBUG: analysis_id = {analysis_id}")

    git_url = extract_git_url(user_content)
    print(f"DEBUG: git_url = {git_url}")

    # Git URL이 감지되었고 analysis_id가 없는 경우, RAG 분석을 트리거
    if git_url and not analysis_id:
        print(f"DEBUG: Git URL detected and no analysis_id. Checking reachability...")
        # if not await is_git_url_reachable(git_url):
        #     response_content = (
        #         f"제공된 Git 레포지토리 URL에 접근할 수 없습니다: {git_url}\n"
        #         f"URL이 올바른지, 레포지토리가 공개되어 있는지 확인해주세요."
        #     )
        #     print(f"DEBUG: Git URL not reachable. Returning error.")
        #     return {
        #         "messages": [{
        #             "role": "assistant", 
        #             "content": response_content
        #         }]
        #     }

        print(f"DEBUG: Git URL is reachable. Triggering RAG analysis.")
        analysis_id = await trigger_rag_analysis(git_url)
        
        if analysis_id:
            response_content = (
                f"Git 레포지토리 분석을 시작합니다: {git_url}\n"
                f"분석 ID: `{analysis_id}`\n"
                f"분석이 완료되면 이 ID를 사용하여 가이드를 추출할 수 있습니다. "
                f"예시: `analysis_id {analysis_id} 로 개발 가이드를 추출해줘`"
            )
        else:
            response_content = (
                f"Git 레포지토리 분석 요청에 실패했습니다: {git_url}\n"
                f"CoE-RagPipeline 서버가 실행 중인지 확인해주세요."
            )
        
        print(f"DEBUG: Returning early after triggering analysis or failure.")
        return {
            "messages": [{
                "role": "assistant", 
                "content": response_content
            }]
        }
    
    print("DEBUG: Proceeding to existing analysis logic.")
    # RAG Pipeline에서 분석 결과 가져오기
    analysis_data = get_rag_analysis_result(analysis_id)
    
    if not analysis_data:
        print(f"DEBUG: No analysis data found for ID: {analysis_id}")
        return {
            "messages": [{
                "role": "assistant", 
                "content": "분석 결과를 찾을 수 없습니다. CoE-RagPipeline에서 먼저 Git 레포지토리 분석을 수행해주세요.\n\n사용법:\n1. CoE-RagPipeline에서 Git 레포지토리 분석 실행\n2. 분석 완료 후 analysis_id와 함께 가이드 추출 요청\n\n예시: \"analysis_id abc-123-def로 개발 가이드를 추출해줘\""
            }]
        }
    
    try:
        print("DEBUG: Proceeding to RAG search and guide extraction.")
        # RAG 검색을 통해 컨텍스트 가져오기
        # "analysis_id"와 같은 키워드를 제거하여 순수한 질문을 만듭니다.
        clean_question = user_question.replace(f"analysis_id {analysis_id}", "").strip()
        if not clean_question:
            clean_question = "이 프로젝트의 전반적인 개발 가이드라인" # 기본 질문
            
        context = search_rag_context(query=clean_question, analysis_id=analysis_id)
        git_urls = extract_git_urls_from_analysis(analysis_data)
        
        # LLM 클라이언트 가져오기
        from core.llm_client import langchain_client
        
        # 가이드 추출 체인 실행
        chain = GUIDE_EXTRACTION_PROMPT | langchain_client | StrOutputParser()
        result = chain.invoke({
            "context": context,
            "question": clean_question
        })
        
        print("DEBUG: Guide extraction complete.")
        return {
            "messages": [{
                "role": "assistant",
                "content": f"📋 **RAG 기반 개발 가이드 추출 완료**\n\n**분석 대상**: {git_urls}\n**분석 ID**: {analysis_id}\n\n{result}"
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