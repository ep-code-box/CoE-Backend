"""
CoE-Backend 테스트 설정 및 공통 픽스처
"""
import os
import sys
import pytest
import asyncio
from fastapi import FastAPI
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 필요한 모델 import
from core.database import User
from core.auth import get_current_user

# 테스트 환경에서 langflow 관련 import 에러 방지
os.environ["SKIP_LANGFLOW_INIT"] = "true"

from api.chat_api import router as chat_router, set_agent_info
from api.health_api import router as health_router
from services.chat_service import ChatService, get_chat_service
from core.llm_client import get_model_info

# Mock get_db 함수 (더 이상 사용되지 않지만, 기존 코드와의 호환성을 위해 유지)
def get_db_mock():
    return Mock()

# Mock get_current_user 함수
def get_current_user_mock():
    user = Mock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user

# Mock ChatService 인스턴스
@pytest.fixture
def mock_chat_service():
    mock_service = Mock(spec=ChatService)
    mock_service.get_or_create_session.return_value = {
        "session_id": "test-session-123",
        "conversation_turns": 0,
        "max_turns": 3,
        "is_active": True
    }
    mock_service.save_chat_message.return_value = Mock()
    mock_service.update_session_turns.return_value = {
        "session_id": "test-session-123",
        "conversation_turns": 1,
        "max_turns": 3,
        "is_active": True
    }
    mock_service.log_api_call.return_value = Mock()
    return mock_service

# Mock User 클래스 정의
class MockUser:
    def __init__(self, id=1, username="testuser", email="test@example.com", is_active=True):
        self.id = id
        self.username = username
        self.email = email
        self.is_active = is_active


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock 데이터베이스 세션"""
    return Mock()


@pytest.fixture
def mock_user():
    """Mock 사용자 객체"""
    user = Mock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_chat_service):
    """FastAPI 테스트 클라이언트"""
    test_app = FastAPI()
    test_app.include_router(chat_router)
    test_app.include_router(health_router)

    # 의존성 오버라이드
    test_app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    test_app.dependency_overrides[get_current_user] = get_current_user_mock
    
    with TestClient(test_app) as client:
        yield client
    
    # 의존성 오버라이드 정리
    test_app.dependency_overrides.clear()


@pytest.fixture
async def async_client(mock_chat_service) -> AsyncGenerator[AsyncClient, None]:
    """비동기 HTTP 클라이언트"""
    test_app = FastAPI()
    test_app.include_router(chat_router)
    test_app.include_router(health_router)

    # 의존성 오버라이드
    test_app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    test_app.dependency_overrides[get_current_user] = get_current_user_mock
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
    
    # 의존성 오버라이드 정리
    test_app.dependency_overrides.clear()


@pytest.fixture
def mock_llm_client():
    """Mock LLM 클라이언트"""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


@pytest.fixture
def mock_embeddings():
    """Mock 임베딩 서비스"""
    mock_embeddings = AsyncMock()
    mock_embeddings.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    mock_embeddings.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return mock_embeddings


@pytest.fixture
def mock_vector_store():
    """Mock 벡터 스토어"""
    mock_store = AsyncMock()
    mock_store.add_documents = AsyncMock()
    mock_store.similarity_search = AsyncMock(return_value=[])
    return mock_store


@pytest.fixture
def sample_chat_state():
    """샘플 채팅 상태"""
    return {
        "messages": [
            {"role": "user", "content": "Hello, world!"}
        ],
        "original_input": "Hello, world!",
        "current_tool": None,
        "tool_results": []
    }


@pytest.fixture
def sample_user_message():
    """샘플 사용자 메시지"""
    return {"role": "user", "content": "Test message"}


@pytest.fixture
def sample_assistant_message():
    """샘플 어시스턴트 메시지"""
    return {"role": "assistant", "content": "Test response"}


@pytest.fixture(autouse=True)
def setup_test_env():
    """테스트 환경 설정"""
    # 환경 변수 설정
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    yield
    
    # 정리
    test_vars = ["APP_ENV", "DATABASE_URL", "OPENAI_API_KEY"]
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API 응답"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    }


@pytest.fixture
def mock_streaming_response():
    """Mock 스트리밍 응답"""
    return [
        {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": " world!"},
                    "finish_reason": "stop"
                }
            ]
        }
    ]