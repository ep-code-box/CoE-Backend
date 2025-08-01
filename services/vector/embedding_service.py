import os
import requests
import logging
from typing import List, Union, Optional

logger = logging.getLogger(__name__)

class EmbeddingService:
    """임베딩 서비스 클래스"""
    
    def __init__(self, service_url: Optional[str] = None):
        """
        EmbeddingService 초기화
        
        Args:
            service_url: 임베딩 서비스 URL
        """
        self.service_url = service_url or os.getenv("EMBEDDING_SERVICE_URL", "http://koEmbeddings:6668")
        
    def create_embeddings(self, texts: Union[str, List[str]], model: str = "ko-sentence-bert") -> List[List[float]]:
        """
        텍스트들을 임베딩으로 변환합니다.
        
        Args:
            texts: 임베딩할 텍스트(들)
            model: 사용할 모델 이름
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            # 입력 텍스트 정규화
            if isinstance(texts, str):
                input_texts = [texts]
            else:
                input_texts = texts
            
            # 임베딩 서비스에 요청
            response = requests.post(
                f"{self.service_url}/embed",
                headers={"Content-Type": "application/json"},
                json={"inputs": input_texts},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"임베딩 서비스 오류: {response.status_code} - {response.text}")
                raise Exception(f"임베딩 생성 실패: {response.text}")
            
            # 임베딩 결과 파싱
            embeddings = response.json()
            
            if not isinstance(embeddings, list):
                raise Exception("임베딩 서비스에서 예상치 못한 응답 형식을 받았습니다.")
            
            logger.info(f"Successfully created {len(embeddings)} embeddings")
            return embeddings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"임베딩 서비스 연결 오류: {e}")
            raise Exception(f"임베딩 서비스에 연결할 수 없습니다: {str(e)}")
        except Exception as e:
            logger.error(f"임베딩 생성 중 오류 발생: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        임베딩 서비스 상태 확인
        
        Returns:
            서비스 정상 여부
        """
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False