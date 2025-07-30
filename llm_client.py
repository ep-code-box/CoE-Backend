import os
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from models import model_registry # ModelRegistry를 가져옵니다.

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 모델 정보 중앙 관리 ---
# ModelRegistry에서 기본 모델 정보를 가져옵니다.
default_model = model_registry.get_default_model()
if not default_model:
    raise ValueError("기본 모델을 찾을 수 없습니다. models.json 파일을 확인하세요.")

# 환경 변수에서 임베딩 관련 설정 가져오기
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
# EMBEDDING_PROVIDER 환경 변수 및 관련 로직을 제거하여 API 기반 임베딩으로 통일합니다.

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
    model=default_model.model_id, # ModelRegistry에서 가져온 기본 모델 ID를 사용합니다.
    streaming=True,
    client=client,  # 중앙 클라이언트 인스턴스를 전달
)

# 3) LangChain 연동을 위한 OpenAIEmbeddings Client 설정
# 로컬 임베딩 옵션을 제거하고, 항상 API 기반의 OpenAIEmbeddings를 사용하도록 단순화합니다.
embeddings_client = OpenAIEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    client=client # 중앙 클라이언트 인스턴스를 전달합니다.
)

print(f"✅ Initialized API-based Embedding Model ({EMBEDDING_MODEL_NAME}).")
