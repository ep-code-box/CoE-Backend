"""RAG pipeline proxy endpoints.

These routes expose a stable backend-facing interface while delegating
requests to the CoE-RagPipeline service. They allow the frontend (or
other clients) to rely on the backend only, avoiding direct access to
the RAG service.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["🧠 RAG"])

# Prefer explicit env vars; fall back to the in-cluster service name.
_RAG_BASE_URL = (
    os.getenv("RAG_PIPELINE_URL")
    or os.getenv("RAG_PIPELINE_BASE_URL")
    or "http://ragpipeline:8001"
).rstrip("/")
_RAG_TIMEOUT = float(os.getenv("RAG_PIPELINE_TIMEOUT", "300"))


class GitRepository(BaseModel):
    """Repository metadata required by the RAG pipeline."""

    url: HttpUrl = Field(..., description="Git repository URL")
    branch: Optional[str] = Field(default="main", description="Branch to analyze")
    name: Optional[str] = Field(default=None, description="Optional display name")


class AnalysisRequestPayload(BaseModel):
    """Subset of fields accepted by the RAG analysis endpoint."""

    repositories: List[GitRepository]
    include_ast: bool = True
    include_tech_spec: bool = True
    include_correlation: bool = True
    include_tree_sitter: bool = True
    include_static_analysis: bool = True
    include_dependency_analysis: bool = True
    generate_report: bool = True
    group_name: Optional[str] = None


class AnalysisStartResponse(BaseModel):
    """Response returned when analysis is queued or reused."""

    analysis_id: str
    status: str
    message: Optional[str] = None
    existing_analyses: Optional[List[str]] = None


class SearchRequestPayload(BaseModel):
    """Search request forwarded to the RAG pipeline."""

    query: str
    k: int = 5
    filter_metadata: Optional[Dict[str, Any]] = None
    analysis_id: Optional[str] = None
    repository_url: Optional[str] = None
    group_name: Optional[str] = None


class EmbedContentPayload(BaseModel):
    """Arbitrary content ingestion request."""

    source_type: str = Field(..., description="Type of content: text, file, or url")
    source_data: str = Field(..., description="Content payload or reference")
    group_name: Optional[str] = Field(default=None, description="Group name to bucket embeddings")
    title: Optional[str] = Field(default=None, description="Optional title for the content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata to store")


async def _proxy_request(
    method: str,
    path: str,
    *,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Forward an HTTP request to the RAG pipeline with shared error handling."""

    url = f"{_RAG_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=_RAG_TIMEOUT) as client:
            response = await client.request(method, url, json=payload, params=params)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        logger.error(
            "RAG pipeline returned %s for %s %s: %s",
            exc.response.status_code,
            method,
            url,
            detail,
        )
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.RequestError as exc:
        logger.error("Failed to reach RAG pipeline at %s: %s", url, exc)
        raise HTTPException(status_code=502, detail=f"Failed to reach RAG pipeline: {exc}") from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected error during RAG proxy request")
        raise HTTPException(status_code=500, detail="Unexpected RAG proxy error") from exc


@router.post("/analyze", response_model=AnalysisStartResponse)
async def start_analysis(request: AnalysisRequestPayload) -> AnalysisStartResponse:
    """Start (or reuse) a repository analysis via the RAG pipeline."""

    payload = request.model_dump(exclude_none=True)
    logger.info("Forwarding RAG analysis request to %s", _RAG_BASE_URL)
    result = await _proxy_request("POST", "/api/v1/analyze", payload=payload)
    return AnalysisStartResponse(**result)


@router.get("/results/{analysis_id}")
async def get_analysis_result(analysis_id: str) -> Dict[str, Any]:
    """Fetch a specific analysis result from the RAG pipeline."""

    result = await _proxy_request("GET", f"/api/v1/results/{analysis_id}")
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Unexpected response shape from RAG pipeline")
    return result


@router.get("/results")
async def list_analysis_results() -> List[Dict[str, Any]]:
    """List available analysis results maintained by the RAG pipeline."""

    result = await _proxy_request("GET", "/api/v1/results")
    if not isinstance(result, list):
        raise HTTPException(status_code=502, detail="Unexpected response shape from RAG pipeline")
    return result


@router.post("/search")
async def search_documents(request: SearchRequestPayload) -> List[Dict[str, Any]]:
    """Execute a semantic search against the RAG pipeline's vector store."""

    payload = request.model_dump(exclude_none=True)
    result = await _proxy_request("POST", "/api/v1/search", payload=payload)
    if isinstance(result, list):
        return result
    raise HTTPException(status_code=502, detail="Unexpected response shape from RAG pipeline")


@router.post("/ingest/rdb-schema")
async def ingest_rdb_schema() -> Dict[str, Any]:
    """Trigger RDB schema ingestion on the RAG pipeline."""

    result = await _proxy_request("POST", "/api/v1/ingest_rdb_schema")
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Unexpected response shape from RAG pipeline")
    return result


@router.post("/embed-content")
async def embed_content(request: EmbedContentPayload) -> Dict[str, Any]:
    """Proxy arbitrary content embedding requests to the RAG pipeline."""

    payload = request.model_dump(exclude_none=True)
    result = await _proxy_request("POST", "/api/v1/embed-content", payload=payload)
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Unexpected response shape from RAG pipeline")
    return result
