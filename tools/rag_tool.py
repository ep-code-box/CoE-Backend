from typing import Dict, Any

from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings

from llm_client import langchain_client
from schemas import ChatState

# 라우터 프롬프트에 사용될 도구 설명
rag_tool_description = {
    "name": "rag_retrieval",
    "description": "프로젝트 아키텍처나 내부 문서와 관련된 질문에 답변합니다. (예: '프로젝트 아키텍처에 대해 설명해줘')"
}

# ChromaDB 클라이언트 초기화 (영구 저장소 사용)
vectorstore = Chroma(persist_directory="./db", embedding_function=OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 2}) # 상위 2개 문서 검색

# RAG 프롬프트 템플릿
template = """
당신은 주어진 컨텍스트 정보를 바탕으로 사용자의 질문에 답변하는 AI 어시스턴트입니다.
컨텍스트에 답변이 없는 경우, 아는 대로 답변하지 말고 정보가 없다고 솔직하게 말하세요.

Context:
{context}

Question:
{question}

Answer:
"""
prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    """검색된 문서들을 하나의 문자열로 결합합니다."""
    return "\n\n".join(doc.page_content for doc in docs)

# RAG 체인 구성
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | langchain_client
    | StrOutputParser()
)

def rag_retrieval_node(state: ChatState) -> Dict[str, Any]:
    """벡터 데이터베이스에서 관련 문서를 검색하여 사용자의 질문에 답변합니다."""
    question = state.get("original_input", "")
    if not question:
        return {"messages": [{"role": "system", "content": "질문을 찾을 수 없습니다."}]}
    
    answer = rag_chain.invoke(question)
    return {"messages": [{"role": "assistant", "content": answer}]}