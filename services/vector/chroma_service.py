import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import OpenAIEmbeddings
from .embedding_service import EmbeddingService
from langchain_chroma import Chroma
from langchain.schema import Document
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaService:
    """ChromaDB 벡터 데이터베이스 서비스"""
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None,
                 chroma_host: Optional[str] = None,
                 chroma_port: Optional[int] = None,
                 collection_name: str = "coe_documents"):
        """
        ChromaService 초기화
        
        Args:
            openai_api_key: OpenAI API 키
            openai_api_base: OpenAI API 베이스 URL
            chroma_host: ChromaDB 호스트
            chroma_port: ChromaDB 포트
            collection_name: ChromaDB 컬렉션 이름
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_api_base = openai_api_base or os.getenv("OPENAI_API_BASE")
        self.chroma_host = chroma_host or os.getenv("CHROMA_HOST", "chroma")
        self.chroma_port = chroma_port or int(os.getenv("CHROMA_PORT", "8000"))
        self.collection_name = collection_name or os.getenv("CHROMA_COLLECTION_NAME", "coe_documents")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        # OpenAI 임베딩 서비스 초기화
        try:
            self.embedding_service = EmbeddingService(
                openai_api_key=self.openai_api_key,
                openai_api_base=self.openai_api_base
            )
            if self.embedding_service.health_check():
                logger.info("Using OpenAI embedding service")
                self.use_local_embeddings = True  # OpenAI를 기본으로 사용
            else:
                logger.warning("OpenAI embedding service not available")
                self.use_local_embeddings = False
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI embedding service: {e}")
            self.use_local_embeddings = False
        
        # OpenAI Embeddings 초기화 (fallback)
        embedding_kwargs = {"api_key": self.openai_api_key}
        if self.openai_api_base:
            embedding_kwargs["base_url"] = self.openai_api_base
            
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        
        # ChromaDB 클라이언트 초기화
        try:
            self.chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            self.vectorstore = Chroma(
                client=self.chroma_client,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            
            logger.info(f"Connected to ChromaDB server at {self.chroma_host}:{self.chroma_port}")
            logger.info(f"Using collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def search_similar_documents(self, 
                               query: str, 
                               k: int = 5,
                               filter_metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        유사한 문서를 검색합니다.
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            filter_metadata: 메타데이터 필터
            
        Returns:
            유사한 문서 리스트
        """
        try:
            # OpenAI 임베딩 서비스 사용 시 직접 검색
            if self.use_local_embeddings:
                logger.info("Using OpenAI embedding service for search")
                
                # 쿼리 임베딩 생성
                query_embedding = self.embedding_service.create_embeddings([query])[0]
                
                # ChromaDB에서 직접 검색
                collection = self.chroma_client.get_collection(self.collection_name)
                
                # 검색 수행
                where_filter = filter_metadata if filter_metadata else None
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=where_filter
                )
                
                # Document 객체로 변환
                documents = []
                if results['documents'] and results['documents'][0]:
                    for i, doc_text in enumerate(results['documents'][0]):
                        metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                        documents.append(Document(page_content=doc_text, metadata=metadata))
                
                logger.info(f"Found {len(documents)} similar documents using local embeddings")
                return documents
            else:
                # OpenAI 임베딩 사용 (기존 방식)
                if filter_metadata:
                    results = self.vectorstore.similarity_search(
                        query, 
                        k=k, 
                        filter=filter_metadata
                    )
                else:
                    results = self.vectorstore.similarity_search(query, k=k)
                
                logger.info(f"Found {len(results)} similar documents using OpenAI embeddings")
                return results
            
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            return []
    
    def search_similar_documents_with_score(self, 
                                          query: str, 
                                          k: int = 5,
                                          filter_metadata: Optional[Dict[str, Any]] = None) -> List[tuple]:
        """
        유사한 문서를 점수와 함께 검색합니다.
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            filter_metadata: 메타데이터 필터
            
        Returns:
            (문서, 점수) 튜플 리스트
        """
        try:
            # 로컬 임베딩 서비스 사용 시 직접 검색
            if self.use_local_embeddings:
                logger.info("Using local embedding service for search with score")
                
                # 쿼리 임베딩 생성
                query_embedding = self.embedding_service.create_embeddings([query])[0]
                
                # ChromaDB에서 직접 검색
                collection = self.chroma_client.get_collection(self.collection_name)
                
                # 검색 수행
                where_filter = filter_metadata if filter_metadata else None
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=where_filter,
                    include=['documents', 'metadatas', 'distances']
                )
                
                # (Document, score) 튜플로 변환
                doc_score_pairs = []
                if results['documents'] and results['documents'][0]:
                    for i, doc_text in enumerate(results['documents'][0]):
                        metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                        # ChromaDB는 거리를 반환하므로 유사도 점수로 변환 (1 - distance)
                        distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 1.0
                        score = 1.0 - distance
                        document = Document(page_content=doc_text, metadata=metadata)
                        doc_score_pairs.append((document, score))
                
                logger.info(f"Found {len(doc_score_pairs)} similar documents with scores using local embeddings")
                return doc_score_pairs
            else:
                # OpenAI 임베딩 사용 (기존 방식)
                if filter_metadata:
                    results = self.vectorstore.similarity_search_with_score(
                        query, 
                        k=k, 
                        filter=filter_metadata
                    )
                else:
                    results = self.vectorstore.similarity_search_with_score(query, k=k)
                
                logger.info(f"Found {len(results)} similar documents with scores using OpenAI embeddings")
                return results
            
        except Exception as e:
            logger.error(f"Failed to search similar documents with score: {e}")
            return []
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        문서들을 벡터 데이터베이스에 추가합니다.
        
        Args:
            documents: 추가할 문서 리스트
            
        Returns:
            추가된 문서의 ID 리스트
        """
        try:
            # 로컬 임베딩 서비스 사용 시 직접 임베딩 생성
            if self.use_local_embeddings:
                logger.info("Using local embedding service for document addition")
                
                # 문서 텍스트 추출
                texts = [doc.page_content for doc in documents]
                
                # 로컬 임베딩 서비스로 임베딩 생성
                embeddings = self.embedding_service.create_embeddings(texts)
                
                # ChromaDB에 직접 추가
                collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                
                # 문서 ID 생성
                import uuid
                doc_ids = [str(uuid.uuid4()) for _ in documents]
                
                # 메타데이터 준비
                metadatas = [doc.metadata for doc in documents]
                
                # ChromaDB에 추가
                collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=doc_ids
                )
                
                logger.info(f"Successfully added {len(documents)} documents using local embeddings")
                return doc_ids
            else:
                # OpenAI 임베딩 사용 (기존 방식)
                doc_ids = self.vectorstore.add_documents(documents)
                logger.info(f"Successfully added {len(documents)} documents using OpenAI embeddings")
                return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            return []
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        문서들을 벡터 데이터베이스에서 삭제합니다.
        
        Args:
            ids: 삭제할 문서 ID 리스트
            
        Returns:
            삭제 성공 여부
        """
        try:
            self.vectorstore.delete(ids=ids)
            logger.info(f"Successfully deleted {len(ids)} documents from ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from ChromaDB: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        컬렉션 정보를 반환합니다.
        
        Returns:
            컬렉션 정보 딕셔너리
        """
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            count = collection.count()
            
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