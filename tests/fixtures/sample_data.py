"""
테스트용 샘플 데이터 픽스처
"""
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any


@pytest.fixture
def sample_openai_chat_request():
    """샘플 OpenAI 채팅 요청"""
    return {
        "model": "coe-agent-v1",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "temperature": 0.7,
        "max_tokens": 1000,
        "stream": False
    }


@pytest.fixture
def sample_streaming_chat_request():
    """샘플 스트리밍 채팅 요청"""
    return {
        "model": "coe-agent-v1",
        "messages": [
            {"role": "user", "content": "Tell me a story"}
        ],
        "stream": True,
        "temperature": 0.8
    }


@pytest.fixture
def sample_chat_messages():
    """샘플 채팅 메시지 리스트"""
    return [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a high-level programming language."},
        {"role": "user", "content": "Can you show me an example?"}
    ]


@pytest.fixture
def sample_langflow_node():
    """샘플 LangFlow 노드"""
    return {
        "id": "text-input-1",
        "type": "TextInput",
        "position": {"x": 100.0, "y": 200.0},
        "data": {
            "text": "Hello, world!",
            "template": "input_template",
            "variables": ["user_input"]
        }
    }


@pytest.fixture
def sample_langflow_edge():
    """샘플 LangFlow 엣지"""
    return {
        "id": "edge-1",
        "source": "text-input-1",
        "target": "llm-node-1",
        "sourceHandle": "output",
        "targetHandle": "input"
    }


@pytest.fixture
def sample_langflow_workflow():
    """샘플 LangFlow 워크플로우"""
    return {
        "name": "simple_chat_workflow",
        "description": "A simple chat workflow for testing",
        "nodes": [
            {
                "id": "input-1",
                "type": "TextInput",
                "position": {"x": 0, "y": 0},
                "data": {"text": "User input"}
            },
            {
                "id": "llm-1",
                "type": "LLMNode",
                "position": {"x": 200, "y": 0},
                "data": {"model": "gpt-3.5-turbo"}
            },
            {
                "id": "output-1",
                "type": "TextOutput",
                "position": {"x": 400, "y": 0},
                "data": {"text": "Response"}
            }
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "input-1",
                "target": "llm-1"
            },
            {
                "id": "edge-2",
                "source": "llm-1",
                "target": "output-1"
            }
        ]
    }


@pytest.fixture
def sample_analysis_request():
    """샘플 분석 요청"""
    return {
        "analysis_id": "test-analysis-123",
        "repositories": [
            {
                "url": "https://github.com/test/repo1",
                "branch": "main",
                "path": "/src"
            },
            {
                "url": "https://github.com/test/repo2",
                "branch": "develop"
            }
        ],
        "include_ast": True,
        "include_tech_spec": True,
        "include_correlation": True
    }


@pytest.fixture
def sample_code_analysis_request():
    """샘플 코드 분석 요청"""
    return {
        "language": "python",
        "code": '''
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
'''
    }


@pytest.fixture
def sample_vector_documents():
    """샘플 벡터 문서"""
    return [
        {
            "content": "FastAPI is a modern web framework for building APIs with Python.",
            "metadata": {
                "source": "documentation",
                "category": "web_framework",
                "language": "python"
            }
        },
        {
            "content": "LangChain is a framework for developing applications powered by language models.",
            "metadata": {
                "source": "documentation",
                "category": "ai_framework",
                "language": "python"
            }
        },
        {
            "content": "Docker is a platform for developing, shipping, and running applications in containers.",
            "metadata": {
                "source": "documentation",
                "category": "containerization",
                "technology": "docker"
            }
        }
    ]


@pytest.fixture
def sample_embedding_vectors():
    """샘플 임베딩 벡터"""
    return [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.2, 0.3, 0.4, 0.5, 0.6],
        [0.3, 0.4, 0.5, 0.6, 0.7]
    ]


@pytest.fixture
def sample_user_data():
    """샘플 사용자 데이터"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow() - timedelta(hours=1)
    }


@pytest.fixture
def sample_jwt_payload():
    """샘플 JWT 페이로드"""
    return {
        "sub": "testuser",
        "user_id": 1,
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "type": "access"
    }


@pytest.fixture
def sample_tool_state():
    """샘플 도구 상태"""
    return {
        "messages": [
            {"role": "user", "content": "Convert this text to uppercase: hello world"}
        ],
        "next_node": "tool1",
        "original_input": "Convert this text to uppercase: hello world",
        "api_data": None
    }


@pytest.fixture
def sample_api_response():
    """샘플 API 응답"""
    return {
        "status": "success",
        "data": {
            "result": "Operation completed successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": "req-123456"
        },
        "metadata": {
            "version": "1.0.0",
            "processing_time": 0.123
        }
    }


@pytest.fixture
def sample_error_response():
    """샘플 에러 응답"""
    return {
        "status": "error",
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid input parameters",
            "details": {
                "field": "email",
                "reason": "Invalid email format"
            }
        },
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": "req-error-123"
    }


@pytest.fixture
def sample_health_response():
    """샘플 헬스체크 응답"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": "test",
        "services": {
            "database": "connected",
            "redis": "connected",
            "llm_client": "available"
        }
    }


@pytest.fixture
def sample_models_list():
    """샘플 모델 리스트"""
    return {
        "object": "list",
        "data": [
            {
                "id": "coe-agent-v1",
                "object": "model",
                "created": 1677610602,
                "owned_by": "coe-backend",
                "permission": [],
                "root": "coe-agent-v1",
                "parent": None
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
                "permission": [],
                "root": "gpt-3.5-turbo",
                "parent": None
            }
        ]
    }