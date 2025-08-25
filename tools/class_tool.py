from typing import Dict, Any, List, Optional
from core.schemas import AgentState

# --- Tool Implementations ---

class TextAnalytics:
    """A simple class for text analysis."""
    def analyze(self, text: str) -> str:
        length = len(text)
        words = len(text.split())
        return f"텍스트 분석 결과: 길이={length}, 단어 수={words}"

text_analyzer = TextAnalytics()

async def class_call_run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> str:
    """
    Analyzes the user's input text using the TextAnalytics class.
    """
    text_to_analyze = ""
    if tool_input and 'text' in tool_input:
        text_to_analyze = tool_input['text']
    else:
        user_content = state.get("input", "분석할 내용이 없습니다.")
        if ':' in user_content:
            text_to_analyze = user_content.split(':', 1)[1].strip()
        else:
            text_to_analyze = user_content

    if not text_to_analyze:
        return "분석할 텍스트가 없습니다."

    return text_analyzer.analyze(text_to_analyze)

async def combined_tool_run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> str:
    """
    Combined tool that performs API call and analysis.
    """
    # This is a placeholder. In a real scenario, this tool would call other tools
    # or services to fetch data and then analyze it.
    user_input = state.get("input", "")
    return f"Combined tool executed for: {user_input}"

# --- Tool Schemas and Functions for LLM ---

available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "class_call",
            "description": "텍스트를 분석합니다. (예: \"이 문장 분석해줘\")",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "분석할 텍스트"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "combined_tool",
            "description": "API로 데이터를 가져와 클래스로 분석하는 조합 작업입니다. (예: \"1번 사용자 데이터 분석해줘\")",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

tool_functions: Dict[str, callable] = {
    "class_call": class_call_run,
    "combined_tool": combined_tool_run,
}
