from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(
    tags=["🏥 Health Check"],
    prefix="",
    responses={
        200: {"description": "서비스가 정상적으로 작동 중입니다"},
        503: {"description": "서비스 이용 불가"}
    }
)


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    timestamp: datetime
    service: str = "CoE-Backend"
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-08-03T10:30:00.000Z",
                "service": "CoE-Backend"
            }
        }


@router.get(
    "/health", 
    response_model=HealthResponse,
    summary="서비스 상태 확인",
    description="""
    **CoE-Backend 서비스의 상태를 확인합니다.**
    
    이 엔드포인트는 다음을 확인합니다:
    - 서비스 실행 상태
    - 현재 시간
    - 서비스 식별자
    
    **사용 예시:**
    ```bash
    curl -X GET "http://localhost:8000/health"
    ```
    """,
    response_description="서비스 상태 정보"
)
async def health_check():
    """서비스 상태 확인 - 서비스가 정상적으로 실행 중인지 확인합니다."""
    return HealthResponse(
        status="healthy", 
        timestamp=datetime.now(),
        service="CoE-Backend"
    )