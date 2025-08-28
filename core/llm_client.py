import os
from typing import Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from core.models import model_registry, ModelInfo # ModelRegistry를 가져옵니다.

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 모델 정보 중앙 관리 ---
# ModelRegistry에서 기본 모델 정보를 가져옵니다.
default_model = model_registry.get_default_model()
if not default_model:
    raise ValueError("기본 모델을 찾을 수 없습니다. models.json 파일을 확인하세요.")

# --- 프로바이더별 클라이언트 인스턴스 ---
# 각 프로바이더별로 별도의 클라이언트를 생성하여 올바른 API 키와 엔드포인트를 사용합니다.
_clients: Dict[str, OpenAI] = {}

def _create_client_for_provider(model_info: ModelInfo) -> OpenAI:
    """프로바이더별 OpenAI 클라이언트를 생성합니다."""
    provider = model_info.provider
    if provider == "sktax":
        return OpenAI(
            base_url=model_info.api_base,
            api_key=os.getenv("SKAX_API_KEY")
        )
    elif provider == "openai":
        return OpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
    elif provider == "anthropic":
        # Anthropic은 OpenAI 호환 API를 제공하지 않으므로 별도 처리가 필요할 수 있습니다.
        # 현재는 OpenAI 클라이언트로 처리하되, 향후 확장 가능하도록 구조를 유지합니다.
        return OpenAI(
            base_url=os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1"),
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    elif provider == "local":
        return OpenAI(
            base_url=model_info.api_base,
            api_key="dummy_key"  # Local models often don't need an API key
        )
    else:
        raise ValueError(f"지원하지 않는 프로바이더입니다: {provider}")

def get_client_for_model(model_id: str) -> OpenAI:
    """모델 ID에 해당하는 프로바이더의 클라이언트를 반환합니다."""
    model_info = model_registry.get_model(model_id)
    if not model_info:
        raise ValueError(f"지원하지 않는 모델입니다: {model_id}")
    
    provider = model_info.provider
    if provider not in _clients:
        _clients[provider] = _create_client_for_provider(model_info)
    
    return _clients[provider]

def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """모델 ID에 해당하는 모델 정보를 반환합니다."""
    return model_registry.get_model(model_id)

# --- 기본 클라이언트 (하위 호환성을 위해 유지) ---
# 기본 모델의 프로바이더에 해당하는 클라이언트를 기본 클라이언트로 설정합니다.
client = get_client_for_model(default_model.model_id)

# 1) 직접 사용을 위한 클라이언트 (예: router_node)
# 위에서 생성한 `client` 인스턴스를 그대로 사용합니다.

# 2) LangChain 연동을 위한 ChatOpenAI Client 설정 (LCEL 체인용)
langchain_client = ChatOpenAI(
    model=default_model.model_id, # ModelRegistry에서 가져온 기본 모델 ID를 사용합니다.
    streaming=True,
    client=client,  # 기본 클라이언트 인스턴스를 전달
)

print(f"✅ Initialized provider-specific clients for {len(_clients)} providers.")
