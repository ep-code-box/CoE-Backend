import os
from typing import Dict, Optional
from openai import AsyncOpenAI, OpenAI
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

# --- 모델별 클라이언트 인스턴스 ---
# 각 model_id별로 별도의 클라이언트를 생성하여 올바른 API 키와 엔드포인트를 사용합니다.
_clients: Dict[str, AsyncOpenAI] = {}

# --- Provider별 기본 설정 ---
_PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "openai": {
        "api_base_env": "OPENAI_API_BASE",
        "api_base_default": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "api_base_env": "ANTHROPIC_API_BASE",
        "api_base_default": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "sktax": {
        "api_key_env": "SKAX_API_KEY",
    },
    "local": {
        "api_key_default": "dummy_key",
    },
    "sktchat": {
        "api_key_env": "",
    },
}


def _resolve_base_url(model_info: ModelInfo) -> Optional[str]:
    """모델의 api_base를 우선 사용하고, 없으면 provider 기본값을 반환합니다."""
    if model_info.api_base:
        return model_info.api_base
    provider = (model_info.provider or "").lower()
    defaults = _PROVIDER_DEFAULTS.get(provider, {})
    env_key = defaults.get("api_base_env")
    if env_key:
        return os.getenv(env_key, defaults.get("api_base_default"))
    return defaults.get("api_base_default")


def _resolve_api_key(model_info: ModelInfo) -> Optional[str]:
    """provider에 따라 적절한 API 키를 반환합니다."""
    provider = (model_info.provider or "").lower()
    defaults = _PROVIDER_DEFAULTS.get(provider, {})
    env_key = defaults.get("api_key_env")
    if env_key:
        return os.getenv(env_key)
    return defaults.get("api_key_default")


# --- OpenAI 비호환 커스텀 provider ---
_CUSTOM_PROVIDERS = {"sktchat"}


def is_custom_provider(model_id: str) -> Optional[str]:
    """모델이 OpenAI 비호환 커스텀 provider를 사용하면 provider명을 반환합니다."""
    model_info = model_registry.get_model(model_id)
    if not model_info:
        return None
    provider = (model_info.provider or "").lower()
    return provider if provider in _CUSTOM_PROVIDERS else None


def get_api_key_for_model(model_id: str) -> Optional[str]:
    """모델 ID에 해당하는 API 키를 반환합니다."""
    model_info = model_registry.get_model(model_id)
    if not model_info:
        return None
    return _resolve_api_key(model_info)


def resolve_effective_model_id(model_id: Optional[str]) -> str:
    """실제 제공자에게 전달할 모델 ID를 반환합니다."""

    if not model_id:
        return default_model.model_id

    model_info = model_registry.get_model(model_id)
    if model_info is None:
        return model_id

    if model_info.provider_model_id:
        return model_info.provider_model_id

    provider = (model_info.provider or "").lower()
    if provider == "coe":
        return default_model.model_id

    return model_id


def _create_client_for_model(model_info: ModelInfo) -> AsyncOpenAI:
    """모델 정보를 기반으로 OpenAI 클라이언트를 생성합니다.

    - api_base: 모델에 직접 정의된 값을 우선 사용, 없으면 provider 기본값
    - api_key: provider에 따라 적절한 환경변수에서 로드
    """
    provider_raw = model_info.provider or ""
    provider = provider_raw.lower()

    # CoE 프로바이더는 다른 모델로 위임
    if provider == "coe":
        fallback_id = model_info.provider_model_id
        if not fallback_id:
            fallback_model = model_registry.get_default_model()
            if fallback_model is None:
                raise ValueError("기본 모델이 없어 CoE 프로바이더를 초기화할 수 없습니다.")
            fallback_id = fallback_model.model_id

        if fallback_id == model_info.model_id:
            fallback_model = model_registry.get_default_model()
            if fallback_model is None or fallback_model.model_id == model_info.model_id:
                raise ValueError("CoE 프로바이더가 사용할 대체 모델을 찾을 수 없습니다.")
            fallback_id = fallback_model.model_id

        return get_client_for_model(fallback_id)

    # 일반 프로바이더: api_base와 api_key를 모델/provider 설정에서 결정
    base_url = _resolve_base_url(model_info)
    api_key = _resolve_api_key(model_info)

    if not base_url:
        raise ValueError(
            f"모델 '{model_info.model_id}'의 api_base를 결정할 수 없습니다. "
            f"models.json에 api_base를 지정하거나 provider 기본값을 확인하세요."
        )
    if not api_key:
        raise ValueError(
            f"모델 '{model_info.model_id}'(provider={provider_raw})의 "
            f"API 키를 찾을 수 없습니다. 환경변수를 확인하세요."
        )

    return AsyncOpenAI(base_url=base_url, api_key=api_key)

def get_client_for_model(model_id: str) -> AsyncOpenAI:
    """모델 ID에 해당하는 프로바이더의 클라이언트를 반환합니다.
    
    model_id를 캐시 키로 사용하여, 같은 provider라도
    api_base가 다르면 별도 클라이언트를 생성합니다.
    """
    model_info = model_registry.get_model(model_id)
    if not model_info:
        raise ValueError(f"지원하지 않는 모델입니다: {model_id}")

    if model_id not in _clients:
        _clients[model_id] = _create_client_for_model(model_info)

    return _clients[model_id]

def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """모델 ID에 해당하는 모델 정보를 반환합니다."""
    return model_registry.get_model(model_id)

# --- 기본 클라이언트 (하위 호환성을 위해 유지) ---
# 기본 모델의 프로바이더에 해당하는 클라이언트를 기본 클라이언트로 설정합니다.
client = get_client_for_model(default_model.model_id)

# 1) 직접 사용을 위한 클라이언트 (예: router_node) → 위에서 생성한 `client` 인스턴스를 그대로 사용

# 2) LangChain 연동을 위한 ChatOpenAI Client 설정 (LCEL 체인용)
#    LangChain의 ChatOpenAI는 OpenAI SDK v1 리소스(client.chat.completions) 또는
#    api_key/base_url 설정로 동작합니다. 루트 AsyncOpenAI를 넘기면 `create`가 없어 오류가 납니다.

# 기본 모델의 base_url/api_key를 공용 헬퍼로 계산
_lc_base_url = _resolve_base_url(default_model)
_lc_api_key = _resolve_api_key(default_model)
_lc_effective_model = resolve_effective_model_id(default_model.model_id)

langchain_client = ChatOpenAI(
    model=_lc_effective_model,
    streaming=True,
    api_key=_lc_api_key,
    base_url=_lc_base_url,
)

print(f"✅ Initialized model-specific clients for {len(_clients)} models.")
