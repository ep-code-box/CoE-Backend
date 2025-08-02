import os
import logging
from typing import List, Union, Optional
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """OpenAI 임베딩 서비스 클래스"""
    
    def __init__(self, openai_api_key: Optional[str] = None, openai_api_base: Optional[str] = None):
        """
        EmbeddingService 초기화
        
        Args:
            openai_api_key: OpenAI API 키
            openai_api_base: OpenAI API 베이스 URL
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_api_base = openai_api_base or os.getenv("OPENAI_API_BASE")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        # OpenAI Embeddings 초기화
        embedding_kwargs = {"api_key": self.openai_api_key}
        if self.openai_api_base:
            embedding_kwargs["base_url"] = self.openai_api_base
            
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        
    def create_embeddings(self, texts: Union[str, List[str]], model: str = "text-embedding-3-large") -> List[List[float]]:
        """
        텍스트들을 임베딩으로 변환합니다.
        
        Args:
            texts: 임베딩할 텍스트(들)
            model: 사용할 모델 이름 (OpenAI embedding 모델)
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            # 입력 텍스트 정규화
            if isinstance(texts, str):
                input_texts = [texts]
            else:
                input_texts = texts
            
            # OpenAI 임베딩 생성
            embeddings = self.embeddings.embed_documents(input_texts)
            
            logger.info(f"Successfully created {len(embeddings)} embeddings using OpenAI")
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI 임베딩 생성 중 오류 발생: {e}")
            raise Exception(f"OpenAI 임베딩 생성 실패: {str(e)}")
    
    def health_check(self) -> bool:
        """
        OpenAI 임베딩 서비스 상태 확인
        
        Returns:
            서비스 정상 여부
        """
        try:
            # 간단한 테스트 텍스트로 임베딩 생성 시도
            test_embedding = self.embeddings.embed_query("test")
            return len(test_embedding) > 0
        except Exception as e:
            logger.error(f"OpenAI 임베딩 서비스 상태 확인 실패: {e}")
            return False