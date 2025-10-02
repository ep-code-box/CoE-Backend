"""Async client for interacting with the CoE RAG pipeline."""
from __future__ import annotations

from typing import Any, Sequence

import httpx


class RagClient:
    """Minimal async client used by the guide agent."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client

    async def __aenter__(self) -> "RagClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def semantic_search(
        self,
        *,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
        analysis_id: str | None = None,
        repository_url: str | None = None,
        group_name: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"query": query, "k": k}
        if filter_metadata:
            payload["filter_metadata"] = filter_metadata
        if analysis_id:
            payload["analysis_id"] = analysis_id
        if repository_url:
            payload["repository_url"] = repository_url
        if group_name:
            payload["group_name"] = group_name

        body = await self._request_json("POST", "/api/v1/search", json=payload)
        return list(body or [])

    async def search_source_summaries(
        self,
        *,
        analysis_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        params = {"query": query, "top_k": top_k}
        body = await self._request_json(
            "GET",
            f"/api/v1/source-summary/search/{analysis_id}",
            params=params,
        )
        data = (body or {}).get("data", {})
        return list(data.get("results", []) or [])

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        if self._client is None:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, json=json, params=params)
        else:
            response = await self._client.request(method, url, json=json, params=params)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()
