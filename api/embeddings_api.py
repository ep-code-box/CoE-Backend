from fastapi import APIRouter, HTTPException
from typing import List, Union, Optional
from pydantic import BaseModel
import requests
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["embeddings"])

# OpenAI 호환 임베딩 요청/응답 모델
class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "ko-sentence-bert"
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
        
        # 임베딩 서비스 URL 설정
        embedding_service_url = os.getenv("EMBEDDING_SERVICE_URL", "http://koEmbeddings:6668")
        
        # 임베딩 서비스에 요청
        response = requests.post(
            f"{embedding_service_url}/embed",
            headers={"Content-Type": "application/json"},
            json={"inputs": texts},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"임베딩 서비스 오류: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500, 
                detail=f"임베딩 생성 실패: {response.text}"
            )
        
        # 임베딩 결과 파싱
        embeddings = response.json()
        
        if not isinstance(embeddings, list):
            raise HTTPException(
                status_code=500,
                detail="임베딩 서비스에서 예상치 못한 응답 형식을 받았습니다."
            )
        
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
        
    except requests.exceptions.RequestException as e:
        logger.error(f"임베딩 서비스 연결 오류: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"임베딩 서비스에 연결할 수 없습니다: {str(e)}"
        )
    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"임베딩 생성 중 오류가 발생했습니다: {str(e)}"
        )