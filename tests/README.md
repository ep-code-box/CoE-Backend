# CoE-Backend 테스트 가이드

이 문서는 CoE-Backend 프로젝트의 테스트 구조와 실행 방법을 설명합니다.

## 📁 테스트 구조

```
tests/
├── __init__.py                 # 테스트 패키지 초기화
├── conftest.py                 # 공통 픽스처 및 설정
├── README.md                   # 이 파일
├── unit/                       # 단위 테스트
│   ├── test_auth.py           # 인증 모듈 테스트
│   ├── test_schemas.py        # 스키마 모듈 테스트
│   ├── test_tools.py          # 도구 시스템 테스트
│   └── test_services.py       # 서비스 레이어 테스트
├── integration/                # 통합 테스트
│   ├── test_health_api.py     # 헬스체크 API 테스트
│   └── test_chat_api.py       # 채팅 API 테스트
└── fixtures/                   # 테스트 데이터
    └── sample_data.py         # 샘플 데이터 픽스처
```

## 🚀 테스트 실행

### 전체 테스트 실행
```bash
# 모든 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=. --cov-report=html
```

### 특정 테스트 실행
```bash
# 단위 테스트만 실행
pytest tests/unit/

# 통합 테스트만 실행
pytest tests/integration/

# 특정 파일 테스트
pytest tests/unit/test_auth.py

# 특정 테스트 함수 실행
pytest tests/unit/test_auth.py::TestPasswordUtils::test_password_hashing
```

### 마커별 테스트 실행
```bash
# 단위 테스트만 실행
pytest -m unit

# API 테스트만 실행
pytest -m api

# 도구 테스트만 실행
pytest -m tools

# 느린 테스트 제외
pytest -m "not slow"
```

### 병렬 테스트 실행
```bash
# 4개 프로세스로 병렬 실행
pytest -n 4

# 자동으로 CPU 코어 수만큼 병렬 실행
pytest -n auto
```

## 🏷️ 테스트 마커

프로젝트에서 사용하는 테스트 마커들:

- `@pytest.mark.unit`: 단위 테스트
- `@pytest.mark.integration`: 통합 테스트
- `@pytest.mark.api`: API 엔드포인트 테스트
- `@pytest.mark.tools`: 도구 시스템 테스트
- `@pytest.mark.slow`: 실행 시간이 긴 테스트

## 🔧 테스트 환경 설정

### 필수 의존성 설치
```bash
# 테스트 의존성 설치
pip install -r requirements-test.txt
```

### 환경 변수
테스트 실행 시 자동으로 설정되는 환경 변수들:
- `APP_ENV=test`
- `DATABASE_URL=sqlite:///:memory:`
- `OPENAI_API_KEY=test-key`

### Mock 설정
`conftest.py`에서 제공하는 주요 픽스처들:
- `mock_db`: Mock 데이터베이스 세션
- `mock_user`: Mock 사용자 객체
- `client`: FastAPI 테스트 클라이언트
- `async_client`: 비동기 HTTP 클라이언트
- `mock_llm_client`: Mock LLM 클라이언트

## 📊 커버리지 리포트

### HTML 리포트 생성
```bash
pytest --cov=. --cov-report=html
# htmlcov/index.html 파일 생성됨
```

### 터미널 리포트
```bash
pytest --cov=. --cov-report=term-missing
```

### 커버리지 목표
- 전체 커버리지: 80% 이상
- 핵심 모듈 커버리지: 90% 이상

## 🧪 테스트 작성 가이드

### 단위 테스트 작성
```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestMyModule:
    def test_function_success(self):
        # Given
        input_data = "test_input"
        
        # When
        result = my_function(input_data)
        
        # Then
        assert result == "expected_output"
    
    def test_function_error_handling(self):
        with pytest.raises(ValueError):
            my_function(invalid_input)
```

### 통합 테스트 작성
```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
@pytest.mark.api
class TestMyAPI:
    def test_endpoint_success(self, client: TestClient):
        response = client.get("/api/endpoint")
        
        assert response.status_code == 200
        assert "expected_field" in response.json()
```

### 비동기 테스트 작성
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_async_function(async_client: AsyncClient):
    response = await async_client.get("/async-endpoint")
    assert response.status_code == 200
```

## 🔍 디버깅

### 테스트 디버깅
```bash
# 상세한 출력과 함께 실행
pytest -v -s

# 첫 번째 실패에서 중단
pytest -x

# 마지막 실패한 테스트만 재실행
pytest --lf

# 실패한 테스트와 관련된 테스트들 재실행
pytest --ff
```

### 로그 출력
```bash
# 로그 출력 포함
pytest -s --log-cli-level=INFO
```

## 📝 테스트 베스트 프랙티스

### 1. 테스트 구조
- **Given-When-Then** 패턴 사용
- 테스트 함수명은 `test_`로 시작
- 명확하고 설명적인 테스트 이름 사용

### 2. Mock 사용
- 외부 의존성은 항상 Mock 처리
- 데이터베이스, API 호출, 파일 시스템 접근 등

### 3. 픽스처 활용
- 공통 테스트 데이터는 픽스처로 관리
- `conftest.py`에 공통 픽스처 정의

### 4. 테스트 격리
- 각 테스트는 독립적으로 실행 가능해야 함
- 테스트 간 상태 공유 금지

### 5. 에러 케이스 테스트
- 정상 케이스뿐만 아니라 에러 케이스도 테스트
- 경계값 테스트 포함

## 🚨 CI/CD 통합

### GitHub Actions
```yaml
- name: Run tests
  run: |
    pytest --cov=. --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

### 테스트 실패 시 대응
1. 로컬에서 실패한 테스트 재현
2. 디버깅 모드로 원인 파악
3. 수정 후 관련 테스트들 재실행
4. 커버리지 확인

## 📚 추가 리소스

- [pytest 공식 문서](https://docs.pytest.org/)
- [FastAPI 테스팅 가이드](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio 문서](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)