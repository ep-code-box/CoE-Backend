import os
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

# .env 파일에서 환경 변수 로드
load_dotenv()

# 사용할 모델 이름 (Chat, Embedding)
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "api")  # 'api' 또는 'local'

# --- 중앙 OpenAI 클라이언트 인스턴스 ---
# 이 단일 클라이언트는 모든 서비스에서 공유됩니다.
# API 주소, 키 등 모든 설정이 일관되게 유지되도록 보장합니다.
client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "https://guest-api.sktax.chat/v1"),
    api_key=os.getenv("OPENAI_API_KEY")
)

# 1) 직접 사용을 위한 클라이언트 (예: router_node)
# 위에서 생성한 `client` 인스턴스를 그대로 사용합니다.

# 2) LangChain 연동을 위한 ChatOpenAI Client 설정 (LCEL 체인용)
langchain_client = ChatOpenAI(
    model=MODEL_NAME,
    streaming=True,
    client=client,  # 중앙 클라이언트 인스턴스를 전달
)

# 3) LangChain 연동을 위한 OpenAIEmbeddings Client 설정
embeddings_client = OpenAIEmbeddings(
    model=EMBEDDING_MODEL_NAME, client=client.embeddings
) if EMBEDDING_PROVIDER == "api" else HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={'device': 'cpu'},  # GPU 사용 시 'cuda'로 변경
    encode_kwargs={'normalize_embeddings': True}
)

if EMBEDDING_PROVIDER == 'local':
    print("✅ Initialized Local Embedding Model (BAAI/bge-m3).")
else:
    print("✅ Initialized API-based Embedding Model.")
