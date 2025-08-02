from fastapi import APIRouter, HTTPException
from typing import List, Union, Optional
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["embeddings"])

# OpenAI 호환 임베딩 요청/응답 모델
class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "text-embedding-3-large"
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None
    user: Optional[str] = None

class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int

class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: EmbeddingUsage

@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """OpenAI 호환 임베딩 API 엔드포인트"""
    try:
        # 입력 텍스트 정규화
        if isinstance(request.input, str):
            texts = [request.input]
        else:
            texts = request.input
        
        # OpenAI 임베딩 서비스 사용
        from services.vector.embedding_service import EmbeddingService
        
        embedding_service = EmbeddingService()
        embeddings = embedding_service.create_embeddings(texts, model=request.model)
        
        # OpenAI 호환 형식으로 변환
        embedding_data = []
        for i, embedding in enumerate(embeddings):
            embedding_data.append(EmbeddingData(
                embedding=embedding,
                index=i
            ))
        
        # 토큰 수 계산 (간단한 추정)
        total_tokens = sum(len(text.split()) for text in texts)
        
        return EmbeddingResponse(
            data=embedding_data,
            model=request.model,
            usage=EmbeddingUsage(
                prompt_tokens=total_tokens,
                total_tokens=total_tokens
            )
        )
        
    except Exception as e:
        logger.error(f"OpenAI 임베딩 생성 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI 임베딩 생성 중 오류가 발생했습니다: {str(e)}"
        )