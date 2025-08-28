from typing import Dict, Any, Optional, List, Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from core.schemas import AgentState

# 분석 체인을 위한 전역 변수 (지연 초기화)
_analysis_chain = None

# 1. 감성 분석을 위한 Pydantic 모델 정의
class SentimentAnalysis(BaseModel):
    """텍스트의 감성을 분석한 결과"""
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="분석된 감성. 'positive', 'negative', 'neutral' 중 하나입니다."
    )


# 2. 요약 및 감성 분석을 위한 프롬프트 템플릿 정의
summary_prompt = ChatPromptTemplate.from_template(
    "다음 텍스트를 1~2 문장으로 간결하게 요약해줘:\n\n{text}"
)

sentiment_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 텍스트의 감성을 분석하는 전문가입니다. 주어진 텍스트가 긍정, 부정, 중립 중 어디에 해당하는지 판단하고, 반드시 지정된 JSON 형식으로만 응답해야 합니다."),
    ("user", "{text}")
])

def get_analysis_chain():
    """
    분석 체인을 초기화하고 반환합니다. (Singleton 패턴)
    """
    global _analysis_chain
    if _analysis_chain is None:
        # 지연 로딩: 체인이 필요할 때 클라이언트를 임포트합니다.
        from core.llm_client import langchain_client

        # .with_structured_output을 사용하여 LLM이 Pydantic 모델 형식으로 응답하도록 강제
        structured_llm = langchain_client.with_structured_output(SentimentAnalysis)

        # RunnablePassthrough.assign을 사용하여 요약과 감성 분석을 병렬로 처리
        _analysis_chain = RunnablePassthrough.assign(
            summary=(
                summary_prompt
                | langchain_client
                | StrOutputParser()
            ),
            sentiment=(
                sentiment_prompt
                | structured_llm
            )
        )
    return _analysis_chain


async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """
    LangChain Expression Language(LCEL)를 사용하여 텍스트를 요약하고 감성을 분석합니다.
    """
    text_to_analyze = ""
    if tool_input and 'text' in tool_input:
        text_to_analyze = tool_input['text']
    else:
        text_to_analyze = state.get("input", "요약할 내용이 없습니다.")

    if text_to_analyze == "요약할 내용이 없습니다.":
        return {"messages": [{"role": "assistant", "content": text_to_analyze}]}

    try:
        analysis_chain = get_analysis_chain()
        result = analysis_chain.invoke({"text": text_to_analyze})
        summary_text = result['summary']
        sentiment_text = result['sentiment'].sentiment
        response_message = f"텍스트 분석 결과입니다:\n- 요약: {summary_text}\n- 감성: {sentiment_text.capitalize()}"
        return {"messages": [{"role": "assistant", "content": response_message}]}
    except Exception as e:
        error_message = f"LangChain 체인 실행 중 오류가 발생했습니다: {e}"
        print(f"ERROR in langchain_chain_node: {error_message}")
        return {"messages": [{"role": "system", "content": error_message}]}

# --- Tool Schemas and Functions for LLM ---

available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "langchain_chain",
            "description": "LangChain을 사용해 텍스트를 요약하고 감성을 분석합니다. (예: \"이 긴 글을 요약해줘\")",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "요약 및 감성 분석할 텍스트"
                    }
                },
                "required": ["text"]
            }
        }
    }
]

tool_functions: Dict[str, callable] = {
    "langchain_chain": run
}
