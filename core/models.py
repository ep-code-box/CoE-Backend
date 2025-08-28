import json
import os
from typing import List, Optional
from pydantic import BaseModel

class ModelInfo(BaseModel):
    """사용 가능한 LLM 모델의 정보를 담는 Pydantic 모델입니다."""
    # OpenWebUI 호환성을 위해 name 필드 추가
    model_id: str
    name: str
    description: str
    provider: str
    is_default: bool = False
    api_base: Optional[str] = None
    model_type: Optional[str] = "chat"

class ModelRegistry:
    """
    models.json 파일에서 모델 정보를 로드하고 관리하는 중앙 레지스트리입니다.
    싱글톤 패턴으로 구현되어 애플리케이션 전역에서 단일 인스턴스를 공유합니다.
    """
    _instance = None
    _models: List[ModelInfo] = []
    _default_model: Optional[ModelInfo] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        """models.json 파일에서 모델 목록을 로드하고 기본 모델을 설정합니다."""
        try:
            # 현재 파일 위치를 기준으로 models.json 경로를 찾습니다.
            current_dir = os.path.dirname(os.path.abspath(__file__))
            models_file_path = os.path.join(current_dir, '..', 'config', 'models.json')
            
            with open(models_file_path, 'r', encoding='utf-8') as f:
                models_data = json.load(f)
            
            self._models = [ModelInfo(**data) for data in models_data]
            
            # 기본 모델을 찾습니다.
            default_models = [model for model in self._models if model.is_default]
            if default_models:
                self._default_model = default_models[0]
            elif self._models:
                self._default_model = self._models[0] # 기본값이 없으면 첫 번째 모델을 사용
            
            print(f"✅ {len(self._models)}개의 모델을 성공적으로 로드했습니다. (기본 모델: {self.get_default_model().model_id if self._default_model else '없음'})")

        except FileNotFoundError:
            print(f"오류: 'models.json' 파일을 찾을 수 없습니다. {models_file_path} 경로를 확인하세요.")
            self._models = []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"오류: 'models.json' 파일 파싱 중 오류가 발생했습니다: {e}")
            self._models = []

    def get_models(self) -> List[ModelInfo]:
        """로드된 모든 모델의 목록을 반환합니다."""
        return self._models

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """주어진 ID에 해당하는 모델 정보를 반환합니다."""
        for model in self._models:
            if model.model_id == model_id:
                return model
        return None

    def get_default_model(self) -> Optional[ModelInfo]:
        """기본으로 설정된 모델 정보를 반환합니다."""
        return self._default_model

    def register_model(self, model_id: str, name: str, description: str, provider: str):
        """런타임에 새로운 모델을 동적으로 등록합니다."""
        if not self.get_model(model_id):
            new_model = ModelInfo(
                model_id=model_id,
                name=name,
                description=description,
                provider=provider
            )
            self._models.append(new_model)
            print(f"✅ 동적 모델 등록 완료: {model_id}")

# 애플리케이션 시작 시 모델 레지스트리 인스턴스를 생성합니다.
model_registry = ModelRegistry()
