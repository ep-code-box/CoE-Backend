import requests
import os
from typing import Dict, Any
from core.schemas import ChatState

def sql_agent_tool_node(state: ChatState) -> Dict[str, Any]:
    """
    SQL 에이전트를 호출하여 데이터베이스에 대한 자연어 질문을 처리하고,
    결과를 상태의 메시지 목록에 추가합니다.
    """
    # ChatState에서 마지막 사용자 메시지를 가져옵니다.
    if not state.get("messages"):
        return {"messages": [{"role": "assistant", "content": "오류: 대화 기록을 찾을 수 없습니다."}]}
        
    query = state["messages"][-1].get("content")
    if not query:
        return {"messages": [{"role": "assistant", "content": "오류: 마지막 메시지에서 내용을 찾을 수 없습니다."}]}

    rag_pipeline_base_url = os.getenv("RAG_PIPELINE_BASE_URL", "http://localhost:8001")
    sql_agent_url = f"{rag_pipeline_base_url}/api/v1/run_sql_query"
    
    result = {}
    try:
        response = requests.post(sql_agent_url, json={"query": query})
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        result = response.json()
    except requests.exceptions.RequestException as e:
        result = {"status": "error", "message": f"RAG Pipeline SQL Agent 호출 오류: {e}"}
    except requests.exceptions.JSONDecodeError:
        result = {"status": "error", "message": f"잘못된 JSON 응답을 받았습니다: {response.text}"}

    content = ""
    if result.get("status") == "success":
        content = result.get("result", "성공적으로 실행되었지만 결과가 없습니다.")
    else:
        content = f"SQL Agent 오류: {result.get('message', '알 수 없는 오류가 발생했습니다.')}"
        
    return {"messages": [{"role": "assistant", "content": content}]}

# 도구 설명을 정의합니다. `_description` 접미사는 도구 레지스트리에서 자동으로 인식됩니다.
sql_agent_tool_description = {
    "name": "sql_agent_tool",
    "description": "데이터베이스에 대한 질문에 답변하고 SQL 쿼리를 실행하여 정보를 가져오는 도구입니다. 자연어 질문을 입력하세요.",
    "url_path": "/tools/sql-agent" # API 엔드포인트로 노출하기 위한 경로
}