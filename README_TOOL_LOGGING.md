# 🔧 도구 로깅 기능 가이드

CoE-Backend에 추가된 도구 선택 및 실행 추적 로깅 기능에 대한 가이드입니다.

## 📋 개요

AI 에이전트가 사용자의 요청에 대해 어떤 도구를 선택하고 실행하는지 추적할 수 있도록 로깅 기능이 추가되었습니다.

## 🔍 로그 종류

### 1. 도구 선택 로그 (TOOL_SELECTION)
라우터에서 LLM이 사용자 요청에 적합한 도구를 선택할 때 기록됩니다.

```
2025-08-05 12:44:34,700 - 🔧 TOOL_TRACKER - INFO - TOOL_SELECTED: 'api_call' | USER_INPUT: '안녕하세요'
```

### 2. 도구 실행 시작 로그 (TOOL_EXECUTION_START)
선택된 도구가 실행을 시작할 때 기록됩니다.

```
2025-08-05 12:44:34,701 - 🔧 TOOL_TRACKER - INFO - TOOL_EXECUTION_START: 'api_call'
```

### 3. 도구 실행 완료 로그 (TOOL_EXECUTION_COMPLETE)
도구 실행이 성공적으로 완료될 때 실행 시간과 함께 기록됩니다.

```
2025-08-05 12:44:35,123 - 🔧 TOOL_TRACKER - INFO - TOOL_EXECUTION_COMPLETE: 'api_call' | DURATION: 0.42s
```

### 4. 도구 실행 오류 로그 (TOOL_EXECUTION_ERROR)
도구 실행 중 오류가 발생할 때 기록됩니다.

```
2025-08-05 12:44:35,123 - 🔧 TOOL_TRACKER - ERROR - TOOL_EXECUTION_ERROR: 'api_call' | DURATION: 0.15s | ERROR: Connection timeout
```

## 🎯 로그 포맷

### 전용 도구 추적 로거
도구 관련 로그는 `tool_tracker` 전용 로거를 사용하여 다른 시스템 로그와 구분됩니다.

```
포맷: %(asctime)s - 🔧 TOOL_TRACKER - %(levelname)s - %(message)s
예시: 2025-08-05 12:44:34,700 - 🔧 TOOL_TRACKER - INFO - TOOL_SELECTED: 'api_call' | USER_INPUT: '안녕하세요'
```

### 로그 메시지 구조
- **TOOL_SELECTED**: `'도구명' | USER_INPUT: '사용자입력(100자까지)'`
- **TOOL_EXECUTION_START**: `'도구명'`
- **TOOL_EXECUTION_COMPLETE**: `'도구명' | DURATION: X.XXs`
- **TOOL_EXECUTION_ERROR**: `'도구명' | DURATION: X.XXs | ERROR: 오류메시지`

## 🔧 구현 세부사항

### 1. 라우터 로깅 (`routers/router.py`)
- 도구 선택 시점에서 로깅
- 사용자 입력과 선택된 도구를 함께 기록
- 선택 오류 시에도 로깅

### 2. 도구 실행 래퍼 (`core/tool_wrapper.py`)
- 모든 도구 노드를 래핑하여 실행 추적
- 실행 시간 측정 및 기록
- 예외 처리 및 오류 로깅

### 3. 그래프 빌더 통합 (`core/graph_builder.py`)
- 도구 레지스트리에서 로드한 모든 도구에 자동으로 래퍼 적용
- 기존 도구 코드 수정 없이 로깅 기능 추가

### 4. API 도구 로깅 (`api/tools/dynamic_tools_api.py`)
- REST API를 통한 직접 도구 실행도 로깅
- 에이전트 실행과 구분하여 `API_TOOL_EXECUTION` 태그 사용

## 📊 로그 활용 방법

### 1. 실시간 모니터링
```bash
# 도구 관련 로그만 필터링
tail -f server.log | grep "TOOL_TRACKER"

# 특정 도구의 실행만 추적
tail -f server.log | grep "TOOL_TRACKER" | grep "api_call"
```

### 2. 성능 분석
```bash
# 도구별 실행 시간 분석
grep "TOOL_EXECUTION_COMPLETE" server.log | grep "DURATION"

# 가장 느린 도구 찾기
grep "TOOL_EXECUTION_COMPLETE" server.log | sort -k8 -nr
```

### 3. 오류 추적
```bash
# 실행 실패한 도구들 확인
grep "TOOL_EXECUTION_ERROR" server.log

# 특정 기간의 오류 분석
grep "2025-08-05 12:" server.log | grep "TOOL_EXECUTION_ERROR"
```

## 🧪 테스트

### 테스트 스크립트 실행
```bash
python3 test_tool_logging.py
```

이 스크립트는 다양한 시나리오로 AI 에이전트를 테스트하여 로깅 기능이 올바르게 작동하는지 확인합니다.

### 수동 테스트
```bash
# 1. 서버 시작
python3 main.py

# 2. API 요청 (별도 터미널)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "coe-agent-v1", "messages": [{"role": "user", "content": "안녕하세요"}], "stream": false}'

# 3. 서버 로그에서 도구 추적 로그 확인
```

## 🎛️ 설정

### 로그 레벨 조정
`main.py`에서 도구 추적 로거의 레벨을 조정할 수 있습니다:

```python
tool_logger.setLevel(logging.DEBUG)  # 더 상세한 로그
tool_logger.setLevel(logging.WARNING)  # 오류만 로그
```

### 로그 파일 저장
파일로 로그를 저장하려면 `FileHandler`를 추가하세요:

```python
file_handler = logging.FileHandler('tool_tracking.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - 🔧 TOOL_TRACKER - %(levelname)s - %(message)s'))
tool_logger.addHandler(file_handler)
```

## 🔍 문제 해결

### 로그가 출력되지 않는 경우
1. 서버가 정상적으로 시작되었는지 확인
2. 도구 래퍼가 적용되었는지 확인 (`Successfully wrapped X tools` 메시지)
3. 로그 레벨이 적절히 설정되었는지 확인

### 중복 로그가 출력되는 경우
`tool_logger.propagate = False` 설정이 적용되었는지 확인하세요.

## 📈 향후 개선 사항

1. **구조화된 로그**: JSON 형태로 로그 출력하여 분석 도구와 연동
2. **메트릭 수집**: Prometheus 등과 연동하여 도구 사용 통계 수집
3. **대시보드**: 실시간 도구 사용 현황을 시각화하는 웹 대시보드
4. **알림 시스템**: 특정 도구의 실행 실패율이 높을 때 알림 발송

## 🤝 기여

도구 로깅 기능 개선에 대한 제안이나 버그 리포트는 언제든 환영합니다!