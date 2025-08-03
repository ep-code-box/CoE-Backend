"""
헬스체크 API 통합 테스트
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.api
class TestHealthAPI:
    """헬스체크 API 테스트"""
    
    def test_health_check_endpoint(self, client: TestClient):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # 응답 구조 검증
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        
        # 상태 값 검증
        assert data["status"] == "healthy"
        assert isinstance(data["timestamp"], str)
    
    def test_health_check_response_format(self, client: TestClient):
        """헬스체크 응답 형식 검증"""
        response = client.get("/health")
        data = response.json()
        
        # 필수 필드 존재 확인
        required_fields = ["status", "timestamp", "service"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        # 데이터 타입 검증
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["service"], str)
    
    def test_health_check_headers(self, client: TestClient):
        """헬스체크 응답 헤더 검증"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
    
    def test_health_check_multiple_requests(self, client: TestClient):
        """헬스체크 다중 요청 테스트"""
        # 여러 번 요청해도 일관된 응답
        responses = []
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200
            responses.append(response.json())
        
        # 모든 응답이 healthy 상태
        for data in responses:
            assert data["status"] == "healthy"
            assert "timestamp" in data
    
    def test_health_check_method_not_allowed(self, client: TestClient):
        """헬스체크 엔드포인트 POST 요청 테스트"""
        response = client.post("/health")
        assert response.status_code == 405  # Method Not Allowed