from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from schemas import ChatState
from llm_client import langchain_client # LangChain용 클라이언트 가져오기


# 예제 5: LangChain 통합 (LCEL)
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", "다음 텍스트를 한 문장으로 요약해주세요."),
    ("user", "{text}")
])
summary_chain = summary_prompt | langchain_client | StrOutputParser()

def langchain_chain_node(state: ChatState) -> Dict[str, Any]:
    """LangChain 체인을 사용하여 사용자의 입력 텍스트를 요약합니다."""
    user_content = state.get("original_input", "요약할 내용이 없습니다.")
    summary = summary_chain.invoke({"text": user_content})
    return {"messages": [{"role": "assistant", "content": f"요약: {summary}"}]}