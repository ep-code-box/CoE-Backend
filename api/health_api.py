from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str = "CoE-Backend"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    return HealthResponse(
        status="healthy", 
        timestamp=datetime.now(),
        service="CoE-Backend"
    )