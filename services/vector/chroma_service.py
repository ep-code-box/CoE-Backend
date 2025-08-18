import os
import logging
import uuid
from typing import List, Dict, Any, Optional

from langchain.schema import Document
import chromadb
from chromadb.config import Settings

from core.llm_client import get_embedding_client

logger = logging.getLogger(__name__)


class ChromaService:
    """ChromaDB 벡터 데이터베이스 서비스 (langchain-chroma 대신 chromadb 직접 사용)"""

    def __init__(self, 
                 chroma_host: Optional[str] = None,
                 chroma_port: Optional[int] = None,
                 collection_name: str = "coe_documents"):
        """
        ChromaService 초기화
        """
        self.chroma_host = chroma_host or os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = chroma_port or int(os.getenv("CHROMA_PORT", "6666")) # 기본 포트를 6666으로 수정
        self.collection_name = collection_name or os.getenv("CHROMA_COLLECTION_NAME", "coe_documents")

        # llm_client에서 중앙 관리되는 임베딩 클라이언트를 가져옵니다.
        self.embeddings = get_embedding_client()
        logger.info(f"✅ Initialized ChromaService with embedding model: '{self.embeddings.model}'")

        # ChromaDB 클라이언트 초기화
        try:
            self.chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            # 컬렉션을 직접 가져오거나 생성합니다.
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"✅ Connected to ChromaDB server at {self.chroma_host}:{self.chroma_port}")
            logger.info(f"✅ Using collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to ChromaDB: {e}")
            raise

    def search_similar_documents(self, 
                               query: str, 
                               k: int = 5,
                               filter_metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """유사한 문서를 검색합니다."""
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            where_filter = filter_metadata if filter_metadata else {}
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_filter
            )

            documents = []
            if results['documents'] and results['documents'][0]:
                for i, doc_text in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    documents.append(Document(page_content=doc_text, metadata=metadata))
            
            logger.info(f"Found {len(documents)} similar documents using '{self.embeddings.model}'")
            return documents
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            return []

    def search_similar_documents_with_score(self, 
                                          query: str, 
                                          k: int = 5,
                                          filter_metadata: Optional[Dict[str, Any]] = None) -> List[tuple]:
        """유사한 문서를 점수와 함께 검색합니다."""
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            where_filter = filter_metadata if filter_metadata else {}
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )

            doc_score_pairs = []
            if results['documents'] and results['documents'][0]:
                for i, doc_text in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 1.0
                    score = 1.0 - distance  # 유사도 점수로 변환
                    document = Document(page_content=doc_text, metadata=metadata)
                    doc_score_pairs.append((document, score))
            
            logger.info(f"Found {len(doc_score_pairs)} similar documents with scores using '{self.embeddings.model}'")
            return doc_score_pairs
        except Exception as e:
            logger.error(f"Failed to search similar documents with score: {e}")
            return []

    def add_documents(self, documents: List[Document]) -> List[str]:
        """문서들을 벡터 데이터베이스에 추가합니다."""
        try:
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            embeddings = self.embeddings.embed_documents(texts)
            
            doc_ids = [str(uuid.uuid4()) for _ in documents]
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=doc_ids
            )
            
            logger.info(f"Successfully added {len(documents)} documents using '{self.embeddings.model}'")
            return doc_ids
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            return []

    def delete_documents(self, ids: List[str]) -> bool:
        """문서들을 벡터 데이터베이스에서 삭제합니다."""
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Successfully deleted {len(ids)} documents from ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from ChromaDB: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보를 반환합니다."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "host": self.chroma_host,
                "port": self.chroma_port
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "collection_name": self.collection_name,
                "document_count": 0,
                "host": self.chroma_host,
                "port": self.chroma_port,
                "error": str(e)
            }