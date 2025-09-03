from fastapi import APIRouter, HTTPException
from typing import List, Union, Optional
from pydantic import BaseModel
import os
import logging
import httpx # Import httpx for making async HTTP requests

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

# Get RAG Pipeline URL from environment variable
RAG_PIPELINE_URL = os.getenv("RAG_PIPELINE_URL", "http://localhost:8001") # Default to localhost:8001 for local development

@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """Delegates embedding requests to CoE-RagPipeline."""
    try:
        rag_embeddings_url = f"{RAG_PIPELINE_URL}/api/v1/embeddings" # Corrected endpoint

        async with httpx.AsyncClient() as client:
            response = await client.post(rag_embeddings_url, json=request.model_dump(), timeout=30.0)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        rag_response_data = response.json()

        # Validate and return the response from RAG Pipeline
        # Assuming RAG Pipeline returns a compatible OpenAI-like embedding response
        return EmbeddingResponse(**rag_response_data)

    except httpx.HTTPStatusError as e:
        logger.error(f"Error from RAG Pipeline embedding service: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from RAG Pipeline embedding service: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Failed to delegate embedding request to RAG Pipeline: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delegate embedding request to RAG Pipeline: {str(e)}"
        )