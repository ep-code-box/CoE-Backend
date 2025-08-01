from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain.schema import Document

from services.vector.chroma_service import ChromaService

router = APIRouter(prefix="/vector", tags=["vector"])

# Pydantic 모델들
class VectorSearchRequest(BaseModel):
    query: str
    k: int = 5
    filter_metadata: Optional[Dict[str, Any]] = None

class VectorSearchResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total_count: int

class VectorSearchWithScoreResponse(BaseModel):
    results: List[Dict[str, Any]]  # {"document": {...}, "score": float}
    total_count: int

class AddDocumentsRequest(BaseModel):
    documents: List[Dict[str, Any]]  # {"page_content": str, "metadata": dict}

class AddDocumentsResponse(BaseModel):
    document_ids: List[str]
    success_count: int

class DeleteDocumentsRequest(BaseModel):
    ids: List[str]

class CollectionInfoResponse(BaseModel):
    collection_name: str
    document_count: int
    host: str
    port: int
    error: Optional[str] = None

# ChromaService 의존성
def get_chroma_service() -> ChromaService:
    return ChromaService()

@router.post("/search", response_model=VectorSearchResponse)
async def search_similar_documents(
    request: VectorSearchRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """유사한 문서를 검색합니다."""
    try:
        documents = chroma_service.search_similar_documents(
            query=request.query,
            k=request.k,
            filter_metadata=request.filter_metadata
        )
        
        # Document 객체를 딕셔너리로 변환
        doc_dicts = []
        for doc in documents:
            doc_dicts.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return VectorSearchResponse(
            documents=doc_dicts,
            total_count=len(doc_dicts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"벡터 검색 실패: {str(e)}")

@router.post("/search_with_score", response_model=VectorSearchWithScoreResponse)
async def search_similar_documents_with_score(
    request: VectorSearchRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """유사한 문서를 점수와 함께 검색합니다."""
    try:
        results = chroma_service.search_similar_documents_with_score(
            query=request.query,
            k=request.k,
            filter_metadata=request.filter_metadata
        )
        
        # (Document, score) 튜플을 딕셔너리로 변환
        result_dicts = []
        for doc, score in results:
            result_dicts.append({
                "document": {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata
                },
                "score": score
            })
        
        return VectorSearchWithScoreResponse(
            results=result_dicts,
            total_count=len(result_dicts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"벡터 검색 실패: {str(e)}")

@router.post("/add", response_model=AddDocumentsResponse)
async def add_documents(
    request: AddDocumentsRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """문서들을 벡터 데이터베이스에 추가합니다."""
    try:
        # 딕셔너리를 Document 객체로 변환
        documents = []
        for doc_dict in request.documents:
            documents.append(Document(
                page_content=doc_dict.get("page_content", ""),
                metadata=doc_dict.get("metadata", {})
            ))
        
        doc_ids = chroma_service.add_documents(documents)
        
        return AddDocumentsResponse(
            document_ids=doc_ids,
            success_count=len(doc_ids)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 추가 실패: {str(e)}")

@router.delete("/delete")
async def delete_documents(
    request: DeleteDocumentsRequest,
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """문서들을 벡터 데이터베이스에서 삭제합니다."""
    try:
        success = chroma_service.delete_documents(request.ids)
        
        if success:
            return {"message": f"{len(request.ids)}개 문서가 성공적으로 삭제되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="문서 삭제 실패")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 삭제 실패: {str(e)}")

@router.get("/info", response_model=CollectionInfoResponse)
async def get_collection_info(
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    """컬렉션 정보를 반환합니다."""
    try:
        info = chroma_service.get_collection_info()
        return CollectionInfoResponse(**info)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 정보 조회 실패: {str(e)}")