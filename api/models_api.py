"""
모델 관련 API 엔드포인트들을 담당하는 모듈입니다.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from core.models import model_registry

router = APIRouter(tags=["📂 Models"])


@router.get("/v1/models")
async def list_models():
    """
    models.json에 정의된 사용 가능한 모든 모델의 목록을 반환합니다.
    OpenAI의 /v1/models 엔드포인트와 호환되는 형식입니다.
    """
    all_models = model_registry.get_models()
    model_data = [
        {"id": model.model_id, "name": model.name, "object": "model", "created": 1686935002, "owned_by": model.provider}
        for model in all_models
    ]
    return JSONResponse(content={
        "object": "list",
        "data": model_data
    })

@router.get("/v1/tags")
async def list_tags():
    """
    OpenWebUI와의 호환성을 위해 /v1/models와 동일한 모델 목록을 반환합니다.
    """
    return await list_models()