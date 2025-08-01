from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["test"])


class TestRequest(BaseModel):
    message: str


class TestResponse(BaseModel):
    echo: str
    received: str


@router.post("/test", response_model=TestResponse)
async def test_endpoint(request: TestRequest):
    """간단한 테스트 엔드포인트"""
    return TestResponse(
        echo=f"Echo: {request.message}",
        received=request.message
    )