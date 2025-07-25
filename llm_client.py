import os
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# .env 파일에서 환경 변수 로드
load_dotenv()

# 사용할 모델 이름
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")

# 1) 직접 사용을 위한 OpenAI Client 설정 (예: router_node)
client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "https://guest-api.sktax.chat/v1"),
    api_key=os.getenv("OPENAI_API_KEY")
)

# 2) LangChain 연동을 위한 ChatOpenAI Client 설정 (LCEL 체인용)
langchain_client = ChatOpenAI(
    model_name=MODEL_NAME,
    openai_api_base=os.getenv("OPENAI_API_BASE", "https://guest-api.sktax.chat/v1"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    streaming=True,
)