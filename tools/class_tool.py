from typing import Dict, Any
from schemas import ChatState


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
    result = text_analyzer.analyze(user_content)
    return {"messages": [{"role": "assistant", "content": result}]}

# 예제 6: 조합 호출 (API 호출 결과를 클래스로 분석)
def class_analysis_node(state: ChatState) -> Dict[str, Any]:
    """Analyzes the 'body' of the data fetched from an API."""
    api_data = state.get("api_data")
    if not api_data or 'body' not in api_data:
        return {"messages": [{"role": "system", "content": "분석할 API 데이터가 없습니다."}]}
    
    analysis_result = text_analyzer.analyze(api_data['body'])
    return {"messages": [{"role": "assistant", "content": analysis_result}]}