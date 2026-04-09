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

# --- 프로바이더별 클라이언트 인스턴스 ---
# 각 프로바이더별로 별도의 클라이언트를 생성하여 올바른 API 키와 엔드포인트를 사용합니다.
_clients: Dict[str, AsyncOpenAI] = {}


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


def _create_client_for_provider(model_info: ModelInfo) -> AsyncOpenAI:
    """프로바이더별 OpenAI 클라이언트를 생성합니다."""

    provider_raw = model_info.provider or ""
    provider = provider_raw.lower()

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

    if provider == "sktax":
        return AsyncOpenAI(
            base_url=model_info.api_base,
            api_key=os.getenv("SKAX_API_KEY")
        )
    if provider == "openai":
        return AsyncOpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
    if provider == "anthropic":
        # Anthropic은 OpenAI 호환 API를 제공하지 않으므로 별도 처리가 필요할 수 있습니다.
        # 현재는 OpenAI 클라이언트로 처리하되, 향후 확장 가능하도록 구조를 유지합니다.
        return AsyncOpenAI(
            base_url=os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1"),
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    if provider == "local":
        return AsyncOpenAI(
            base_url=model_info.api_base,
            api_key="dummy_key"  # Local models often don't need an API key
        )

    raise ValueError(f"지원하지 않는 프로바이더입니다: {provider_raw}")

def get_client_for_model(model_id: str) -> AsyncOpenAI:
    """모델 ID에 해당하는 프로바이더의 클라이언트를 반환합니다."""
    model_info = model_registry.get_model(model_id)
    if not model_info:
        raise ValueError(f"지원하지 않는 모델입니다: {model_id}")
    
    provider = (model_info.provider or "").lower()
    if provider not in _clients:
        _clients[provider] = _create_client_for_provider(model_info)

    return _clients[provider]

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

# 기본 모델 프로바이더에 맞춰 ChatOpenAI에 전달할 base_url/api_key 계산
provider = default_model.provider
if provider == "sktax":
    _lc_base_url = default_model.api_base
    _lc_api_key = os.getenv("SKAX_API_KEY")
elif provider == "openai":
    _lc_base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    _lc_api_key = os.getenv("OPENAI_API_KEY")
elif provider == "local":
    _lc_base_url = default_model.api_base
    _lc_api_key = "dummy_key"
else:
    # 기타 프로바이더도 OpenAI 호환 게이트웨이를 사용하는 경우에 한해 그대로 시도
    _lc_base_url = getattr(default_model, "api_base", None) or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    _lc_api_key = os.getenv("OPENAI_API_KEY")

langchain_client = ChatOpenAI(
    model=default_model.model_id,  # ModelRegistry에서 가져온 기본 모델 ID 사용
    streaming=True,
    api_key=_lc_api_key,
    base_url=_lc_base_url,
)

print(f"✅ Initialized provider-specific clients for {len(_clients)} providers.")

# --- SK AX Quality Agent (Polaris) 전용 클라이언트 모듈화 ---
class PolarisAgentClient:
    """SK AX Quality Agent (Polaris) 통신용 래퍼 클라이언트"""
    def __init__(self, context: str = "", group_name: str = ""):
        self.context = (context or "").lower()
        self.group_name = (group_name or "").lower()
        # 환경(APP_ENV)에 따른 URL 기본값 분기
        app_env = os.getenv("APP_ENV", "dev").lower()
        is_prd = app_env == "prd"
        
        if is_prd:
            default_url = "http://172.31.166.70:8000/api/agent/v1/chats"
        else:
            default_url = "http://172.31.228.183:8000/api/agent/v1/chats"

        self.api_url = os.getenv("AGENT_API_URL", default_url)
        
        # 시스템 식별자 기반 API KEY 분기
        # MIDER 시스템일 경우
        if self.context == "mider" or self.group_name == "mider":
            self.api_key = os.getenv("MIDER_API_KEY", os.getenv("MIDER_AGENT_API_KEY", ""))
        # AX CODE 시스템일 경우
        elif self.context == "ax_code" or self.group_name == "ax_code":
            self.api_key = os.getenv("AX_CODE_API_KEY", os.getenv("AX_CODE_AGENT_API_KEY", ""))
        else:
            # 설정이 없으면 기본 에이전트 키
            self.api_key = os.getenv("AGENT_API_KEY", "")

    async def create_chat_completion(self, req_model: str, user_query: str, req_stream: bool):
        import httpx
        import json
        import uuid
        import time
        from fastapi import HTTPException
        from fastapi.responses import StreamingResponse
            
        user_id = "agent_developer"
        
        # models.json 설정(ModelRegistry)을 통해 동적으로 model_cd 바인딩
        from core.llm_client import get_model_info
        model_info = get_model_info(req_model)
        
        target_model_cd = "GPT5_2" # 기본값
        if model_info and model_info.provider_model_id:
            target_model_cd = model_info.provider_model_id
        elif req_model and "codex" in req_model.lower():
            target_model_cd = "GPT5_2_CODEX"
            
        payload = {
            "user_id": user_id,
            "message": user_query,
            "model_cd": target_model_cd,
            "usecase_mode": "GENERAL",
            "stream": req_stream
        }
        
        headers = {
            "X-AGENT-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        client = httpx.AsyncClient(timeout=30.0)
        
        if req_stream:
            async def _stream_generator():
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as resp:
                    if resp.status_code != 200:
                        error_data = await resp.aread()
                        raise HTTPException(status_code=resp.status_code, detail=f"Agent API Error: {error_data.decode('utf-8')}")
                    
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("type") == "token":
                                chunk_id = f"chatcmpl-{uuid.uuid4()}"
                                delta_content = data.get('data', '')
                                chunk_data = {'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': req_model, 'choices': [{'index': 0, 'delta': {'content': delta_content}, 'finish_reason': None}]}
                                yield f"data: {json.dumps(chunk_data)}\n\n"
                            elif data.get("type") == "error":
                                chunk_id = f"chatcmpl-{uuid.uuid4()}"
                                error_reason = data.get('reason')
                                delta_content = f"\n[Error: {error_reason}]"
                                chunk_data = {'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': req_model, 'choices': [{'index': 0, 'delta': {'content': delta_content}, 'finish_reason': 'stop'}]}
                                yield f"data: {json.dumps(chunk_data)}\n\n"
                        except json.JSONDecodeError:
                            pass
                    yield "data: [DONE]\n\n"
            return StreamingResponse(_stream_generator(), media_type="text/event-stream")
        else:
            resp = await client.post(self.api_url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Agent API Error: {resp.text}")
            
            lines = resp.text.split("\n")
            full_content = ""
            for line in lines:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "token":
                        full_content += data.get("data", "")
                    elif data.get("type") == "error":
                        full_content += f"\n[Error: {data.get('reason')}]"
                except:
                    pass
                    
            await client.aclose()
            
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req_model or "quality-agent",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": full_content}, "finish_reason": "stop"}]
            }
