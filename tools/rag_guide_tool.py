import re
from typing import Dict, Any, Optional, List

from fastapi import HTTPException
from pydantic import ValidationError

from core.schemas import AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools.core.utils import is_git_url_reachable # Assuming this utility is available

from api.rag_api import (
    AnalysisRequestPayload,
    AnalysisStartResponse,
    GitRepository,
    SearchRequestPayload,
    get_analysis_result as api_get_analysis_result,
    ingest_rdb_schema as api_ingest_rdb_schema,
    list_analysis_results as api_list_analysis_results,
    search_documents as api_search_documents,
    start_analysis as api_start_analysis,
)

def extract_git_url(text: str) -> Optional[str]:
    """텍스트에서 Git URL을 추출합니다."""
    match = re.search(r'https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:/[^\s]*)?', text)
    if match:
        return match.group(0)
    return None

async def trigger_rag_analysis(git_url: str, group_name: Optional[str] = None) -> Optional[str]:
    """CoE-RagPipeline에 Git 레포지토리 분석을 요청합니다."""

    try:
        payload = AnalysisRequestPayload(
            repositories=[GitRepository(url=git_url, branch="master")],
            group_name=group_name,
        )
        result: AnalysisStartResponse = await api_start_analysis(payload)
        return result.analysis_id
    except ValidationError as exc:
        print(f"잘못된 분석 요청 파라미터: {exc}")
        return None
    except HTTPException as exc:
        print(f"CoE-RagPipeline 분석 요청 오류: {exc.status_code} - {exc.detail}")
        return None
    except Exception as exc:
        print(f"CoE-RagPipeline 분석 중 예외 발생: {exc}")
        return None

async def get_rag_analysis_result(analysis_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """CoE-RagPipeline에서 분석 결과를 가져옵니다."""

    try:
        if analysis_id:
            return await api_get_analysis_result(analysis_id)

        results = await api_list_analysis_results()
        if not results:
            return None

        latest_result = max(results, key=lambda item: item.get("created_at", ""))
        analysis_id = latest_result.get("analysis_id")
        if not analysis_id:
            return None

        return await api_get_analysis_result(analysis_id)
    except HTTPException as exc:
        print(f"RAG Pipeline 연결 오류: {exc.status_code} - {exc.detail}")
        return None
    except Exception as exc:
        print(f"RAG Pipeline 결과 조회 중 예외 발생: {exc}")
        return None

async def search_rag_context(query: str, analysis_id: str, k: int = 5) -> str:
    """CoE-RagPipeline의 검색 API를 사용하여 관련 컨텍스트를 가져옵니다."""

    try:
        payload = SearchRequestPayload(
            query=query,
            k=k,
            analysis_id=analysis_id,
            filter_metadata={"analysis_id": analysis_id},
        )
        results = await api_search_documents(payload)

        context_parts = []
        for index, res in enumerate(results):
            score = res.get("score")
            metadata = res.get("metadata", {})
            document_type = metadata.get("document_type", "N/A")
            content = res.get("content", "")

            if score is None:
                context_parts.append(
                    f"문서 {index + 1} (유사도 정보 없음, 유형: {document_type}):\n{content}"
                )
            else:
                context_parts.append(
                    f"문서 {index + 1} (유사도: {score:.2f}, 유형: {document_type}):\n{content}"
                )

        return "\n\n---\n\n".join(context_parts) if context_parts else "관련 컨텍스트를 찾을 수 없습니다."
    except HTTPException as exc:
        return f"검색 API 오류: {exc.status_code} - {exc.detail}"
    except Exception as exc:
        return f"RAG Pipeline 검색 중 예외 발생: {exc}"

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
    action: Optional[str] = None

    # tool_input에서 파라미터 추출
    if tool_input:
        analysis_id = tool_input.get("analysis_id")
        git_url = tool_input.get("git_url")
        group_name = tool_input.get("group_name")
        action = tool_input.get("action")
        if tool_input.get("list_results"):
            action = action or "list_results"
        if tool_input.get("ingest_schema"):
            action = "ingest_schema"

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

    if action is None:
        lowered = user_question.lower()
        list_keywords = ["목록", "list", "hist", "기존 분석", "최근 분석", "결과 조회", "result list"]
        ingest_keywords_primary = ["스키마", "schema", "rdb", "database"]
        ingest_keywords_secondary = ["ingest", "임베딩", "업데이트", "갱신", "등록", "추가", "새로", "refresh"]

        if any(keyword in lowered for keyword in ingest_keywords_primary) and any(
            keyword in lowered for keyword in ingest_keywords_secondary
        ):
            action = "ingest_schema"
        elif any(keyword in lowered for keyword in list_keywords):
            action = "list_results"

    if action == "ingest_schema":
        try:
            result = await api_ingest_rdb_schema()
            return {
                "messages": [{
                    "role": "assistant",
                    "content": (
                        "RDB 스키마 임베딩을 요청했습니다.\n"
                        "완료 결과:\n"
                        f"{result}"
                    ),
                }],
                "ingest_result": result,
            }
        except HTTPException as exc:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": (
                        f"RDB 스키마 임베딩 중 오류가 발생했습니다. (status {exc.status_code})\n"
                        f"detail: {exc.detail}"
                    ),
                }],
                "ingest_error": {
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                },
            }
        except Exception as exc:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"RDB 스키마 임베딩 중 예기치 않은 오류가 발생했습니다: {exc}",
                }],
                "ingest_error": {"message": str(exc)},
            }

    if action == "list_results":
        try:
            results = await api_list_analysis_results()
        except HTTPException as exc:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": (
                        f"분석 결과 목록을 가져오는 데 실패했습니다. (status {exc.status_code})\n"
                        f"detail: {exc.detail}"
                    ),
                }],
                "list_error": {
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                },
            }
        except Exception as exc:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"분석 결과 목록을 가져오는 중 예기치 않은 오류가 발생했습니다: {exc}",
                }],
                "list_error": {"message": str(exc)},
            }

        if not results:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "아직 저장된 분석 결과가 없습니다. Git URL을 제공하여 새 분석을 시작해보세요.",
                }],
                "analysis_results": [],
            }

        summary_lines = []
        for idx, item in enumerate(results[:5], start=1):
            item_id = item.get("analysis_id", "-" )
            status_text = item.get("status", "unknown")
            created_at = item.get("created_at") or item.get("analysis_date")
            source = item.get("source") or "unknown"
            summary_lines.append(
                f"{idx}. ID: {item_id} | 상태: {status_text} | 생성: {created_at} | 출처: {source}"
            )

        summary_text = "\n".join(summary_lines)

        extra_notice = "" if len(results) <= 5 else f"(총 {len(results)}건 중 최근 5건만 표시했습니다.)"

        return {
            "messages": [{
                "role": "assistant",
                "content": (
                    "현재 이용 가능한 분석 결과 목록입니다:\n"
                    f"{summary_text}\n"
                    f"{extra_notice}"
                ).strip(),
            }],
            "analysis_results": results,
        }

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

    if not analysis_id:
        return {
            "messages": [{
                "role": "assistant",
                "content": (
                    "분석 결과를 사용하려면 Git 레포지토리 URL을 제공하거나, "
                    "이미 완료된 분석의 `analysis_id`를 알려주세요.\n"
                    "예시: `analysis_id abc-123-def 로 개발 가이드를 추출해줘`"
                ),
            }]
        }

    # RAG Pipeline에서 분석 결과 가져오기
    analysis_data = await get_rag_analysis_result(analysis_id)

    if not analysis_data:
        return {
            "messages": [{
                "role": "assistant", 
                "content": "분석 결과를 찾을 수 없습니다. CoE-RagPipeline에서 먼저 Git 레포지토리 분석을 수행해주세요.\n\n사용법:\n1. CoE-RagPipeline에서 Git 레포지토리 분석 실행\n2. 분석 완료 후 analysis_id와 함께 가이드 추출 요청\n\n예시: \"analysis_id abc-123-def로 개발 가이드를 추출해줘\""
            }]
        }

    analysis_id = analysis_data.get("analysis_id", analysis_id)
    status = str(analysis_data.get("status", "")).lower()

    if status and status != "completed":
        progress_info = analysis_data.get("progress") or {}
        step = progress_info.get("step")
        percent = progress_info.get("percent")
        updated_at = progress_info.get("updated_at")

        progress_lines: List[str] = []
        if percent is not None:
            progress_lines.append(f"진행률: {percent}%")
        if step:
            progress_lines.append(f"현재 단계: {step}")
        if updated_at:
            progress_lines.append(f"업데이트 시각: {updated_at}")

        progress_text = "\n".join(progress_lines) if progress_lines else "진행 상태 정보를 불러올 수 없습니다."

        return {
            "messages": [{
                "role": "assistant",
                "content": (
                    f"분석이 아직 진행 중입니다. (상태: {status})\n"
                    f"analysis_id: `{analysis_id}`\n"
                    f"{progress_text}\n"
                    "분석이 완료되면 동일한 analysis_id로 다시 요청해주세요."
                ),
            }],
            "analysis_id": analysis_id,
            "status": status,
            "progress": progress_info,
        }
    
    try:
        # "analysis_id"와 같은 키워드를 제거하여 순수한 질문을 만듭니다.
        clean_question = user_question.replace(f"analysis_id {analysis_id}", "").strip()
        if not clean_question:
            clean_question = "이 프로젝트의 전반적인 개발 가이드라인" # 기본 질문
            
        context = await search_rag_context(query=clean_question, analysis_id=analysis_id)
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
            "description": "git주소나 analysis_id를 가 없다면 해당 툴을 사용하지 않습니다. git 주소가 있다면 Git 레포지토리 분석을 시작하고, 분석 결과를 바탕으로 표준개발가이드, 공통코드화, 공통함수 가이드를 추출합니다. 또는 기존 analysis_id를 사용하여 가이드를 추출합니다. group_name을 지정하여 분석 결과를 그룹화할 수 있습니다.",
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
                    },
                    "action": {
                        "type": "string",
                        "description": "수행할 작업을 직접 지정합니다. 예: 'list_results', 'ingest_schema'"
                    },
                    "list_results": {
                        "type": "boolean",
                        "description": "True로 설정하면 사용 가능한 분석 결과 목록을 반환합니다."
                    },
                    "ingest_schema": {
                        "type": "boolean",
                        "description": "True로 설정하면 RDB 스키마 임베딩을 트리거합니다."
                    }
                }
            }
        }
    }
]

tool_functions: Dict[str, callable] = {
    "rag_guide_tool": run
}

tool_contexts: List[str] = ["rag"]
