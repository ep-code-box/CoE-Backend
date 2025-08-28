import requests
import os
from typing import Dict, Any, Optional, List
from core.schemas import AgentState

# RAG Pipeline의 기본 URL (환경 변수 또는 설정 파일에서 가져오는 것이 좋음)
RAG_PIPELINE_BASE_URL = os.getenv("RAG_PIPELINE_BASE_URL", "http://localhost:8001")

async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """
    SQL 에이전트를 호출하여 데이터베이스에 대한 자연어 질문을 처리하고,
    결과를 상태의 메시지 목록에 추가합니다.
    """
    query = None
    if tool_input and 'query' in tool_input:
        query = tool_input['query']
    else:
        # ChatState에서 마지막 사용자 메시지를 가져옵니다.
        if not state.get("history"):
            return {"messages": [{"role": "assistant", "content": "오류: 대화 기록을 찾을 수 없습니다."}]}
            
        query = state["history"][-1].get("content")
        if not query:
            return {"messages": [{"role": "assistant", "content": "오류: 마지막 메시지에서 내용을 찾을 수 없습니다."}]}

    sql_agent_url = f"{RAG_PIPELINE_BASE_URL}/api/v1/run_sql_query"
    
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

# --- Tool Schemas and Functions for LLM ---

available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "sql_agent_tool",
            "description": "데이터베이스에 대한 질문에 답변하고 SQL 쿼리를 실행하여 정보를 가져오는 도구입니다. 자연어 질문을 입력하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL 에이전트에게 전달할 자연어 쿼리"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

tool_functions: Dict[str, callable] = {
    "sql_agent_tool": run
}

tool_contexts: List[str] = ["sql"]
