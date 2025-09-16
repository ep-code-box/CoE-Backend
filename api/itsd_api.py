import os
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
import httpx


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/itsd", tags=["ITSD"])

# Prefer RAG_PIPELINE_URL; default to service DNS in compose network
RAG_BASE = os.getenv("RAG_PIPELINE_URL", "http://coe-ragpipeline:8001").rstrip("/")


class ItsdRecommendationRequest(BaseModel):
    title: str
    description: str


@router.post(
    "/recommend-assignee",
    summary="ITSD 담당자 추천 (proxy)",
    response_model=str,
)
async def recommend_assignee(
    req: ItsdRecommendationRequest,
    page: int = 1,
    page_size: int = 5,
    # Optional fusion overrides (per request)
    use_rrf: bool | None = None,
    w_title: float | None = None,
    w_content: float | None = None,
    rrf_k0: int | None = None,
    top_k_each: int | None = None,
) -> str:
    url = f"{RAG_BASE}/api/v1/itsd/recommend-assignee"
    try:
        async with httpx.AsyncClient() as client:
            params = {"page": page, "page_size": page_size}
            if use_rrf is not None:
                params["use_rrf"] = use_rrf
            if w_title is not None:
                params["w_title"] = w_title
            if w_content is not None:
                params["w_content"] = w_content
            if rrf_k0 is not None:
                params["rrf_k0"] = rrf_k0
            if top_k_each is not None:
                params["top_k_each"] = top_k_each
            resp = await client.post(url, json=req.model_dump(), params=params, timeout=120.0)
            resp.raise_for_status()
            # RAG returns JSON string (Markdown)
            data = resp.json()
            return data if isinstance(data, str) else str(data)
    except httpx.HTTPStatusError as e:
        logger.error("RAG ITSD recommend error: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Failed to call RAG ITSD recommend: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG ITSD recommend failed: {e}")


@router.post(
    "/embed-requests",
    summary="ITSD 요청 데이터(Excel) 임베딩 (proxy)",
)
async def embed_requests(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel(.xlsx) 파일만 업로드할 수 있습니다.",
        )

    url = f"{RAG_BASE}/api/v1/itsd/embed-requests"
    try:
        contents = await file.read()
        files = {"file": (file.filename, contents, file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        async with httpx.AsyncClient() as client:
            # simple retry for transient disconnects
            last_exc = None
            for _ in range(2):
                try:
                    resp = await client.post(url, files=files, timeout=300.0)
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.ReadError, httpx.ProtocolError) as rexc:
                    last_exc = rexc
                    continue
            if last_exc:
                raise last_exc
    except httpx.HTTPStatusError as e:
        logger.error("RAG ITSD embed error: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Failed to call RAG ITSD embed: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG ITSD embed failed: {e}")


@router.post(
    "/embed-requests-async",
    summary="ITSD 요청 데이터(Excel) 임베딩 — 비동기 (proxy)",
)
async def embed_requests_async(file: UploadFile = File(...)):
    """프론트엔드가 백엔드를 경유해 RAG 비동기 임베딩 API를 호출할 수 있게 하는 프록시."""
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel(.xlsx) 파일만 업로드할 수 있습니다.",
        )

    url = f"{RAG_BASE}/api/v1/itsd/embed-requests-async"
    try:
        contents = await file.read()
        files = {"file": (file.filename, contents, file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        async with httpx.AsyncClient() as client:
            last_exc = None
            for _ in range(2):
                try:
                    resp = await client.post(url, files=files, timeout=120.0)
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.ReadError, httpx.ProtocolError) as rexc:
                    last_exc = rexc
                    continue
            if last_exc:
                raise last_exc
    except httpx.HTTPStatusError as e:
        logger.error("RAG ITSD async embed error: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Failed to call RAG ITSD async embed: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG ITSD async embed failed: {e}")


@router.get(
    "/embed-requests-status/{job_id}",
    summary="임베딩 작업 상태 조회 (proxy)",
)
async def embed_status(job_id: str):
    url = f"{RAG_BASE}/api/v1/itsd/embed-requests-status/{job_id}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("RAG ITSD status error: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Failed to call RAG ITSD status: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG ITSD status failed: {e}")
