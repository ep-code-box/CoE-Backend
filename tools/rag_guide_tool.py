import requests
import re
import httpx
import os
from typing import Dict, Any, Optional, List
from core.schemas import AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# RAG Pipeline의 기본 URL (환경 변수 또는 설정 파일에서 가져오는 것이 좋음)
RAG_PIPELINE_BASE_URL = os.getenv("RAG_PIPELINE_BASE_URL", "http://localhost:8001")

def extract_git_url(text: str) -> Optional[str]:
    """텍스트에서 Git URL을 추출합니다."""
    match = re.search(r'https://git\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:/[^\s]*)?', text)
    if match:
        return match.group(0)
    return None

async def trigger_rag_analysis(git_url: str, group_name: Optional[str] = None) -> Optional[str]:
    """CoE-RagPipeline에 Git 레포지토리 분석을 요청합니다."""
    analyze_url = f"{RAG_PIPELINE_BASE_URL}/api/v1/analyze"
    
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
            if group_name:
                payload["group_name"] = group_name

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

def get_rag_analysis_result(analysis_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """CoE-RagPipeline에서 분석 결과를 가져옵니다."""
    try:
        if analysis_id:
            response = requests.get(f"{RAG_PIPELINE_BASE_URL}/api/v1/results/{analysis_id}")
        else:
            response = requests.get(f"{RAG_PIPELINE_BASE_URL}/api/v1/results")
            if response.status_code == 200:
                results = response.json()
                if results:
                    latest_result = max(results, key=lambda x: x.get('created_at', ''))
                    analysis_id = latest_result['analysis_id']
                    response = requests.get(f"{RAG_PIPELINE_BASE_URL}/api/v1/results/{analysis_id}")
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
        search_url = f"{RAG_PIPELINE_BASE_URL}/api/v1/search"
        params = {"query": query, "k": k}
        filter_metadata = {"analysis_id": analysis_id}
        
        response = requests.post(search_url, params=params, json={"filter": filter_metadata})
        
        if response.status_code == 200:
            results = response.json()
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
            if 'repository' in repo and 'url' in repo['repository']:
                git_urls.append(repo['repository']['url'])
    
    return ", ".join(git_urls) if git_urls else "Git URL 정보 없음"

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

async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """
    Git 레포지토리 분석 결과를 바탕으로 개발 가이드를 추출하거나, RAG 분석을 트리거합니다.
    """
    user_content = state.get("input", "")
    user_question = user_content # 원본 질문 저장
    
    analysis_id = None
    git_url = None
    group_name = None

    # tool_input에서 파라미터 추출
    if tool_input:
        analysis_id = tool_input.get("analysis_id")
        git_url = tool_input.get("git_url")
        group_name = tool_input.get("group_name")
    
    # tool_input에 없으면 user_content에서 추출 시도
    if not analysis_id:
        # 간단한 패턴 매칭으로 analysis_id 추출
        words = user_content.split()
        for word in words:
            if "analysis_id" in user_question.lower() and len(word) > 30 and '-' in word:
                analysis_id = word
                break
    
    if not git_url:
        git_url = extract_git_url(user_content)

    # Git URL이 감지되었고 analysis_id가 없는 경우, RAG 분석을 트리거
    if git_url and not analysis_id:
        # if not await is_git_url_reachable(git_url):
        #     return {"error": f"제공된 Git 레포지토리 URL에 접근할 수 없습니다: {git_url}"}

        analysis_id = await trigger_rag_analysis(git_url, group_name)
        
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
        
        return {"messages": [{"role": "assistant", "content": response_content}]}
    
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
        return {
            "messages": [{
                "role": "system",
                "content": error_message
            }]
        }

# --- Tool Schemas and Functions for LLM ---

available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "rag_guide_tool",
            "description": "Git 레포지토리 분석을 시작하고, 분석 결과를 바탕으로 표준개발가이드, 공통코드화, 공통함수 가이드를 추출합니다. 또는 기존 analysis_id를 사용하여 가이드를 추출합니다. group_name을 지정하여 분석 결과를 그룹화할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "git_url": {
                        "type": "string",
                        "description": "분석할 Git 레포지토리 URL (선택 사항)"
                    },
                    "analysis_id": {
                        "type": "string",
                        "description": "기존 분석 ID (선택 사항)"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "분석 결과를 묶을 그룹명 (선택 사항)"
                    }
                }
            }
        }
    }
]

tool_functions: Dict[str, callable] = {
    "rag_guide_tool": run
}
