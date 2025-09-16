import os
from typing import Dict, Any, Optional, List
from core.schemas import AgentState

# Disabled by default. Set ENABLE_SQL_AGENT=true to re-enable.
ENABLE_SQL_AGENT = os.getenv("ENABLE_SQL_AGENT", "false").lower() == "true"

# Unified RAG base URL (only used if enabled)
RAG_PIPELINE_BASE_URL = os.getenv("RAG_PIPELINE_URL") or os.getenv("RAG_PIPELINE_BASE_URL", "http://ragpipeline:8001")

async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    if not ENABLE_SQL_AGENT:
        return {"messages": [{"role": "assistant", "content": "SQL Agent 도구는 비활성화되어 있습니다."}]}
    # If ever re-enabled, implement a safe backend-handled SQL route rather than calling RAG directly.
    return {"messages": [{"role": "assistant", "content": "현재 구성에서는 SQL Agent 호출이 지원되지 않습니다."}]}

# --- Tool Schemas and Functions for LLM ---

if ENABLE_SQL_AGENT:
    available_tools: List[Dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "sql_agent_tool",
                "description": "데이터베이스에 대한 질문에 답변하고 SQL 쿼리를 실행하여 정보를 가져오는 도구입니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL 에이전트에게 전달할 자연어 쿼리"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    tool_functions: Dict[str, callable] = {"sql_agent_tool": run}
    tool_contexts: List[str] = ["sql"]
else:
    available_tools: List[Dict[str, Any]] = []
    tool_functions: Dict[str, callable] = {}
    tool_contexts: List[str] = []
