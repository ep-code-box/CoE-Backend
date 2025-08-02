from typing import Dict, Any
from core.schemas import ChatState


# 라우터 프롬프트에 사용될 도구 설명
class_tool_descriptions = [
    {
        "name": "class_call",
        "description": "텍스트를 분석합니다. (예: \"이 문장 분석해줘\")",
        "url_path": "/tools/class-call"
    },
    {
        "name": "combined_tool",
        "description": "API로 데이터를 가져와 클래스로 분석하는 조합 작업입니다. (예: \"1번 사용자 데이터 분석해줘\")",
        "url_path": "/tools/combined-tool"
    }
]

# 예제 2: Python 클래스 호출
class TextAnalytics:
    """A simple class for text analysis."""
    def analyze(self, text: str) -> str:
        length = len(text)
        words = len(text.split())
        return f"텍스트 분석 결과: 길이={length}, 단어 수={words}"

# Create a single instance to be used by nodes
text_analyzer = TextAnalytics()

def class_call_node(state: ChatState) -> Dict[str, Any]:
    """Analyzes the user's input text using the TextAnalytics class."""
    user_content = state.get("original_input", "분석할 내용이 없습니다.")

    # "명령: 분석할 텍스트" 형식에서 분석할 텍스트만 추출
    text_to_analyze = user_content
    if ':' in user_content:
        # 콜론(:) 뒤의 모든 내용을 분석 대상으로 삼습니다.
        text_to_analyze = user_content.split(':', 1)[1].strip()

    if not text_to_analyze:
        return {"messages": [{"role": "system", "content": "분석할 텍스트가 없습니다."}]}

    result = text_analyzer.analyze(text_to_analyze)
    return {"messages": [{"role": "assistant", "content": result}]}

# 예제 6: 조합 호출 (API 호출 결과를 클래스로 분석)
def class_analysis_node(state: ChatState) -> Dict[str, Any]:
    """Analyzes the 'body' of the data fetched from an API."""
    api_data = state.get("api_data")
    if not isinstance(api_data, dict) or 'body' not in api_data:
        return {"messages": [{"role": "system", "content": "분석할 API 데이터가 없거나 형식이 올바르지 않습니다."}]}
    
    analysis_result = text_analyzer.analyze(api_data['body'])
    return {"messages": [{"role": "assistant", "content": analysis_result}]}

def combined_tool_node(state: ChatState) -> Dict[str, Any]:
    """Combined tool that performs API call and analysis."""
    user_content = state.get("original_input", "")
    
    # API 호출과 분석을 조합한 작업 수행
    return {"messages": [{"role": "assistant", "content": f"Combined tool executed for: {user_content}"}]}