# 🔄 LangFlow 실제 엔진 연동 가이드

이 문서는 CoE-Backend에서 실제 LangFlow 엔진과 연동하여 플로우를 실행하는 방법을 설명합니다.

## ✨ 새로 추가된 기능

### 1. 실제 LangFlow 엔진 연동
- 기존 시뮬레이션 코드를 실제 LangFlow API 호출로 교체
- HTTP 클라이언트를 통한 LangFlow 서버와의 통신
- 비동기 처리를 통한 성능 최적화

### 2. 새로운 REST API 엔드포인트

#### `POST /flows/execute`
저장된 LangFlow를 실제 LangFlow 엔진으로 실행합니다.

**요청 예시:**
```bash
curl -X POST "http://localhost:8000/flows/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_name": "my_flow",
    "inputs": {
      "input_value": "안녕하세요!",
      "message": "테스트 메시지"
    },
    "tweaks": {
      "temperature": 0.7
    },
    "langflow_url": "http://localhost:7860"
  }'
```

**응답 예시:**
```json
{
  "success": true,
  "session_id": "abc123-def456",
  "outputs": {
    "text": "안녕하세요! 어떻게 도와드릴까요?",
    "sender": "AI"
  },
  "execution_time": 2.34
}
```

#### `GET /flows/health`
LangFlow 서버 상태를 확인합니다.

**응답 예시:**
```json
{
  "langflow_url": "http://localhost:7860",
  "is_healthy": true,
  "status": "connected"
}
```

### 3. 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# LangFlow 설정
LANGFLOW_URL=http://localhost:7860
LANGFLOW_API_KEY=your_langflow_api_key_here
```

## 🚀 사용 방법

### 1. LangFlow 서버 실행

먼저 LangFlow 서버를 실행해야 합니다:

```bash
# LangFlow 설치 (Python 3.10-3.13 필요)
pip install langflow

# LangFlow 서버 실행
langflow run --host 0.0.0.0 --port 7860
```

### 2. CoE-Backend 서버 실행

```bash
# 의존성 설치 (새로 추가된 httpx, aiohttp 포함)
pip install -r requirements.txt

# 서버 실행
python main.py
```

### 3. 플로우 저장 및 실행

#### 3.1 플로우 저장
```bash
curl -X POST "http://localhost:8000/flows/save" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hello_world",
    "description": "간단한 인사 플로우",
    "flow_data": {
      "id": "hello-world-001",
      "name": "hello_world",
      "data": {
        "nodes": [...],
        "edges": [...]
      }
    }
  }'
```

#### 3.2 플로우 실행
```bash
curl -X POST "http://localhost:8000/flows/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_name": "hello_world",
    "inputs": {
      "input_value": "안녕하세요!"
    }
  }'
```

### 4. 채팅 인터페이스를 통한 실행

기존 채팅 API를 통해서도 플로우를 실행할 수 있습니다:

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "coe-agent-v1",
    "messages": [
      {
        "role": "user",
        "content": "hello_world 실행"
      }
    ]
  }'
```

## 🧪 테스트

포함된 테스트 스크립트를 사용하여 모든 기능을 테스트할 수 있습니다:

```bash
# 전체 테스트 실행
python test_langflow_api.py

# 특정 플로우만 테스트
python test_langflow_api.py --flow my_flow_name

# 다른 서버 URL로 테스트
python test_langflow_api.py --url http://localhost:8000
```

테스트 스크립트는 다음을 확인합니다:
- LangFlow 서버 연결 상태
- 플로우 목록 조회
- 샘플 플로우 저장
- 플로우 실행 및 결과 확인

## 🔧 구현 세부사항

### 1. LangFlowExecutionService 클래스

`services/langflow/langflow_service.py`에 구현된 서비스 클래스:

- **execute_flow_by_name()**: 플로우 이름으로 실행
- **execute_flow_by_id()**: 플로우 ID로 직접 실행
- **check_langflow_health()**: 서버 상태 확인

### 2. 비동기 처리

LangFlow API 호출은 비동기로 처리되어 성능을 최적화합니다:

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(url, json=payload, headers=headers)
```

### 3. 오류 처리

다양한 오류 상황에 대한 처리:
- 연결 오류 (LangFlow 서버 미실행)
- 타임아웃 오류
- API 응답 오류
- 플로우 찾기 실패

### 4. 기존 도구와의 통합

`tools/langflow_tool.py`의 시뮬레이션 코드가 실제 실행 코드로 교체되어, 채팅 인터페이스를 통해서도 실제 LangFlow를 실행할 수 있습니다.

## 📋 요구사항

- **Python**: 3.10-3.13
- **LangFlow**: 최신 버전
- **새로운 의존성**: httpx, aiohttp
- **환경 변수**: LANGFLOW_URL, LANGFLOW_API_KEY (선택적)

## 🚨 주의사항

1. **LangFlow 서버 실행**: 플로우 실행 전에 LangFlow 서버가 실행되어 있어야 합니다.
2. **플로우 ID**: 저장된 플로우에 유효한 ID가 있어야 실행 가능합니다.
3. **네트워크 연결**: LangFlow 서버와의 네트워크 연결이 필요합니다.
4. **타임아웃**: 복잡한 플로우는 실행 시간이 오래 걸릴 수 있습니다.

## 🔍 문제 해결

### LangFlow 서버 연결 실패
```bash
# 서버 상태 확인
curl http://localhost:7860/health

# 환경 변수 확인
echo $LANGFLOW_URL
```

### 플로우 실행 실패
```bash
# 플로우 목록 확인
curl http://localhost:8000/flows/list

# 특정 플로우 조회
curl http://localhost:8000/flows/my_flow_name
```

### 로그 확인
서버 로그에서 자세한 오류 정보를 확인할 수 있습니다:
```bash
tail -f server.log
```

## 🎯 다음 단계

1. **스트리밍 지원**: 실시간 플로우 실행 결과 스트리밍
2. **플로우 모니터링**: 실행 상태 및 성능 모니터링
3. **배치 실행**: 여러 플로우 동시 실행
4. **캐싱**: 플로우 실행 결과 캐싱
5. **웹훅**: 플로우 완료 시 알림 기능