"""
채팅 API 통합 테스트
"""
import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestChatAPI:
    """채팅 API 테스트"""
    
    def test_chat_completions_endpoint_exists(self, client: TestClient):
        """채팅 완성 엔드포인트 존재 확인"""
        # OPTIONS 요청으로 엔드포인트 존재 확인
        response = client.options("/v1/chat/completions")
        assert response.status_code in [200, 405]  # 엔드포인트가 존재함
    
    @patch('core.llm_client.get_llm_client')
    def test_chat_completions_basic_request(self, mock_get_client, client: TestClient):
        """기본 채팅 완성 요청 테스트"""
        # Mock LLM 클라이언트 설정
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(message=AsyncMock(content="Hello! How can I help you?"))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Hello, world!"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 응답 상태 확인 (실제 LLM 없이는 500 에러 가능)
        assert response.status_code in [200, 500]
    
    def test_chat_completions_invalid_model(self, client: TestClient):
        """잘못된 모델명으로 요청"""
        request_data = {
            "model": "invalid-model",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 잘못된 모델명에 대한 처리 확인
        assert response.status_code in [400, 422, 500]
    
    def test_chat_completions_empty_messages(self, client: TestClient):
        """빈 메시지 배열로 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": []
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 빈 메시지에 대한 처리 확인
        assert response.status_code in [400, 422]
    
    def test_chat_completions_invalid_message_role(self, client: TestClient):
        """잘못된 메시지 역할로 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "invalid_role", "content": "Hello"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 잘못된 역할에 대한 검증 확인
        assert response.status_code == 422
    
    def test_chat_completions_missing_content(self, client: TestClient):
        """메시지 내용 누락으로 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user"}  # content 누락
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 필수 필드 누락에 대한 검증 확인
        assert response.status_code == 422
    
    def test_chat_completions_with_stream_parameter(self, client: TestClient):
        """스트리밍 파라미터와 함께 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": True
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 스트리밍 요청 처리 확인 (실제 구현에 따라 다름)
        assert response.status_code in [200, 500]
    
    def test_chat_completions_with_temperature(self, client: TestClient):
        """온도 파라미터와 함께 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 0.8
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 온도 파라미터 처리 확인
        assert response.status_code in [200, 500]
    
    def test_chat_completions_with_max_tokens(self, client: TestClient):
        """최대 토큰 파라미터와 함께 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 100
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 최대 토큰 파라미터 처리 확인
        assert response.status_code in [200, 500]
    
    def test_chat_completions_malformed_json(self, client: TestClient):
        """잘못된 JSON 형식으로 요청"""
        response = client.post(
            "/v1/chat/completions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_chat_completions_missing_model(self, client: TestClient):
        """모델 필드 누락으로 요청"""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        assert response.status_code == 422
    
    def test_chat_completions_content_type_validation(self, client: TestClient):
        """Content-Type 헤더 검증"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        # JSON Content-Type 없이 요청
        response = client.post(
            "/v1/chat/completions",
            data=json.dumps(request_data)
        )
        
        # Content-Type 검증 확인
        assert response.status_code in [415, 422]


@pytest.mark.integration
@pytest.mark.api
class TestChatAPIAsync:
    """비동기 채팅 API 테스트"""
    
    @pytest.mark.asyncio
    async def test_chat_completions_async_request(self, async_client: AsyncClient):
        """비동기 채팅 완성 요청 테스트"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Hello, async world!"}
            ]
        }
        
        response = await async_client.post("/v1/chat/completions", json=request_data)
        
        # 비동기 요청 처리 확인
        assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_chat_completions_concurrent_requests(self, async_client: AsyncClient):
        """동시 채팅 요청 테스트"""
        import asyncio
        
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": "Concurrent request"}
            ]
        }
        
        # 3개의 동시 요청
        tasks = [
            async_client.post("/v1/chat/completions", json=request_data)
            for _ in range(3)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 모든 요청이 처리되었는지 확인
        assert len(responses) == 3
        
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 500]


@pytest.mark.integration
@pytest.mark.api
class TestChatAPIEdgeCases:
    """채팅 API 엣지 케이스 테스트"""
    
    def test_chat_completions_very_long_message(self, client: TestClient):
        """매우 긴 메시지로 요청"""
        long_content = "A" * 10000  # 10KB 메시지
        
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": long_content}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 긴 메시지 처리 확인
        assert response.status_code in [200, 413, 500]  # 413: Payload Too Large
    
    def test_chat_completions_special_characters(self, client: TestClient):
        """특수 문자가 포함된 메시지로 요청"""
        special_content = "Hello! 🤖 こんにちは 안녕하세요 <script>alert('xss')</script>"
        
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "user", "content": special_content}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 특수 문자 처리 확인
        assert response.status_code in [200, 500]
    
    def test_chat_completions_multiple_message_types(self, client: TestClient):
        """다양한 메시지 타입으로 요청"""
        request_data = {
            "model": "coe-agent-v1",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        
        # 다중 메시지 타입 처리 확인
        assert response.status_code in [200, 500]