# LangFlow 연동 가이드 (현재 구현)

## 1. 개요

이 문서는 CoE-Backend 내 LangFlow 연동의 실제 구현을 설명합니다. 현재 구조는 다음 두 경로를 모두 제공합니다.

- 서버 API 경로: 등록된 Flow를 DB에 저장하고, FastAPI 라우트를 동적으로 노출하여 HTTP로 실행합니다.
- 에이전트 도구 경로: LLM 에이전트가 도구 형태로 LangFlow를 조회/실행합니다.

기존 문서에 언급된 “2단계 LLM 라우팅” 방식은 구현되어 있지 않습니다. 현재는 LLM이 일반 도구들과 함께 LangFlow 관련 도구(목록/실행)를 선택하여 사용하는 방식입니다.

## 2. 동작 방식

- 서버 측 동적 엔드포인트 노출
  - Flow는 DB(`langflows`)에 저장됩니다.
  - 앱 시작 시와 주기적으로 스케줄러가 DB와 라우트를 동기화합니다.
  - 각 Flow는 `POST /flows/run/{endpoint}`로 실행 가능한 엔드포인트가 동적으로 추가됩니다.

- 에이전트 측 도구 연동
  - 에이전트 노드(`core/agent_nodes.py: tool_dispatcher_node`)는 컨텍스트별 서버/클라이언트 도구 스키마를 병합해 LLM에 제공합니다.
  - LangFlow 전용 도구(`tools/langflow_tool.py`): `list_langflows`, `execute_langflow`
    - `list_langflows`: 현재 컨텍스트에서 사용 가능한 Flow 목록을 반환합니다.
    - `execute_langflow(flow_name)`: 지정한 이름의 Flow를 내부 LangFlow 라이브러리로 실행합니다.
  - 컨텍스트 제한은 매핑 테이블(`langflow_tool_mappings`)을 통해 검증됩니다.

## 3. Flow 등록 API

- 엔드포인트: `POST /flows/`
- 설명: Flow를 생성하거나(없으면) 업데이트합니다(있으면).
- 본문 스키마: `core/schemas.py::FlowCreate`
- Request Body 예시:
  ```json
  {
    "endpoint": "generate-python-code-from-spec",
    "description": "요구사항 명세서를 입력으로 받아 Python 클래스를 생성하고 기본 문법 검사를 포함합니다.",
    "flow_id": "flow-generate-py-456",
    "flow_body": { /* LangFlow JSON Object */ },
    "contexts": ["aider", "openWebUi"]
  }
  ```
- 비고
  - 컨텍스트 지정: `contexts`(배열) 또는 `context` 필드 모두 지원합니다.
    - `context`는 문자열 또는 문자열 배열 형식 모두 허용됩니다(호환성 목적).
    - 서버는 제공된 값을 정규화하여 `langflow_tool_mappings`에 반영합니다.
  - 성공 시 DB에 저장하고, 해당 Flow의 실행 라우트가 `POST /flows/run/{endpoint}`로 등록됩니다.

보조 엔드포인트
- `GET /flows/` : 활성 Flow 목록 조회
- `DELETE /flows/{flow_id}` : Flow 비활성화(소프트 삭제) 및 라우트 비활성화

## 4. Flow 실행 API

- 엔드포인트: `POST /flows/run/{endpoint}`
- 요청 본문: Flow가 기대하는 입력 구조를 전달합니다. 기본 구현은 `user_input`으로 전달된 딕셔너리를 그대로 Flow 실행로직에 넘깁니다. 예시:
  ```json
  {
    "text": "문서 요약을 수행해줘"
  }
  ```
- 응답 예시:
  ```json
  {
    "success": true,
    "result": { /* Flow의 최종 출력 */ }
  }
  ```

주의
- 서버 동적 라우트는 샘플 실행기(`services/flow_router_service.py`)를 통해 동작합니다. 에이전트 도구 경로는 내부 LangFlow 라이브러리(`services/langflow/langflow_service.py`)로 직접 실행합니다.

## 5. 에이전트에서의 사용

- 도구 이름 및 설명(`tools/langflow_tool.py`)
  - `list_langflows`: 매개변수 없음. 현재 컨텍스트에 허용된 Flow 목록을 안내합니다.
  - `execute_langflow`: 매개변수 `flow_name`(필수). 해당 이름의 Flow를 실행합니다.
- 자동 파싱 보조: 사용자가 “실행/execute”라는 표현을 포함해 요청한 경우, 최근 메시지에서 flow_name을 추정하는 간단한 파서를 포함합니다(정확도 향상을 위해 명시적 전달 권장).
- 컨텍스트 검증: 실행 전 `langflow_tool_mappings`로 현재 컨텍스트 허용 여부를 검사합니다.
- 내부 실행: LangFlow 그래프는 라이브러리 기반으로 처리되며(`process_graph_cached`), 외부 LangFlow 서버 없이 동작합니다.

## 6. 데이터베이스 스키마(요지)

- `langflows`
  - `flow_id`, `name(endpoint)`, `description`, `flow_data(JSON)`, `is_active`, `created_at`, `updated_at`
- `langflow_tool_mappings`
  - `flow_id`, `context`, `description`, `created_at`, `updated_at`

## 7. 주요 모듈 맵

- `api/flows_api.py`: Flow 등록/조회/삭제 API (prefix: `/flows`)
- `services/flow_service.py`: 등록/업데이트/삭제 + 동적 라우트 추가/제거 연계
- `services/flow_router_service.py`: `POST /flows/run/{endpoint}` 동적 라우팅 추가/비활성화
- `services/scheduler_service.py`: 시작 시 및 주기적 라우트-DB 동기화
- `services/db_langflow_service.py`: Flow CRUD
- `services/langflow/langflow_service.py`: LangFlow 라이브러리 기반 내부 실행
- `tools/langflow_tool.py`: 에이전트용 `list_langflows`, `execute_langflow` 도구
- `services/tool_dispatcher.py`: 컨텍스트별 도구 스키마/함수 로딩, Python 도구/일부 LangFlow 경로 디스패치 유틸

참고
- `services/tool_dispatcher.py`에는 외부 LangFlow 서비스로의 실행(fallback) 유틸이 포함되어 있으며(`LANGFLOW_BASE_URL` 사용), 기본 에이전트 경로에서는 내부 실행을 사용합니다.

## 8. 등록 가이드라인

- `endpoint`: 고유 식별자이자 실행 엔드포인트 경로의 일부가 됩니다(`/flows/run/{endpoint}`).
- `description`: 목록/문서화에 사용됩니다. 사용 목적, 기대 입력/출력, 제약을 명확히 서술하세요.
- `contexts`: 노출 대상 프론트를 최소한으로 명시하세요(예: `aider`, `continue.dev`, `openWebUi`, `rag`, `sql`).
- `flow_body`: LangFlow UI에서 Export한 유효한 JSON을 그대로 사용하세요.

## 9. 변경 사항 요약

- 제거: “2단계 LLM 라우팅”에 의한 자동 Flow 선택은 현재 구현에 포함되지 않습니다.
- 추가: 에이전트 도구(`list_langflows`, `execute_langflow`)를 통해 명시적으로 Flow를 조회/실행합니다.
- 정정: Flow 등록 엔드포인트는 `POST /flows/`이며, 실행 엔드포인트는 `POST /flows/run/{endpoint}`입니다.

### 9.1 자동 라우팅 및 출력 정리(추가)

- 자동 라우팅(선제 실행)은 `services/tool_dispatcher.py`에 구현되어 있습니다.
  - Python 도구/Flow 후보를 컨텍스트 기준으로 수집하고, LLM/텍스트 전략으로 하나를 선택합니다.
  - Python 도구가 선택된 경우, 도구 JSON 스키마를 LLM에 제시하여 arguments(JSON)만 생성하도록 합니다(정규식 금지).
  - LangFlow가 선택된 경우, 내부 실행 후 최종 텍스트만 추출해 반환합니다(raw 노출 금지).
- 사용자 출력은 자연어 문장만 반환하도록 정리되었습니다(상태 배너/JSON 덤프 제거).
- 구성 변수:
  - `AUTO_ROUTE_STRATEGY=llm|text|off`, `AUTO_ROUTE_MODEL=gpt-4o-mini`(기본)

### 9.2 group_name 기반 필터링(추가)

- 요청의 `group_name`이 있으면 더 좁은 후보군만 노출할 수 있습니다.
  - Python 도구: 각 `*_map.py`에서 선택적으로 `allowed_groups: List[str]`를 선언하면 해당 그룹에만 노출됩니다.
  - LangFlow: `langflow_tool_mappings.context`에 `컨텍스트:그룹`(예: `aider:dev-team`) 값을 추가하면 해당 그룹에서만 노출됩니다(스키마 변경 없음).
- 자세한 원칙과 사용법은 `CoE-Backend/AUTO_ROUTING_GUIDE.md` 참고.

## 10. 빠른 실행 예시

- Flow 등록
  - 요청
    ```bash
    curl -X POST http://localhost:8000/flows/ \
      -H 'Content-Type: application/json' \
      -d '{
        "endpoint": "sample-summarizer",
        "description": "간단 요약 플로우",
        "flow_id": "lf-sample-001",
        "flow_body": { /* LangFlow JSON */ },
        "contexts": ["openWebUi", "aider"]
      }'
    ```
  - 응답: 저장된 Flow 정보가 반환되며, `POST /flows/run/sample-summarizer` 경로가 동적으로 등록됩니다.

- Flow 실행
  - 요청
    ```bash
    curl -X POST http://localhost:8000/flows/run/sample-summarizer \
      -H 'Content-Type: application/json' \
      -d '{
        "text": "이 문단을 간단히 요약해줘"
      }'
    ```
  - 응답(예)
    ```json
    { "success": true, "result": { /* 최종 출력 */ } }
    ```

- Flow 목록 조회
  - 요청
    ```bash
    curl http://localhost:8000/flows/
    ```

- Flow 삭제(비활성화)
  - 요청
    ```bash
    curl -X DELETE http://localhost:8000/flows/123   # 123: DB의 flow PK
    ```

에이전트 도구 사용(개념)
- `list_langflows`: 컨텍스트에 허용된 Flow 목록을 어시스턴트 응답으로 제공합니다.
- `execute_langflow`: `{"flow_name": "sample-summarizer"}` 형태로 호출되며, 내부 LangFlow 라이브러리로 실행합니다.

## 11. OpenAPI 문서

- 스웨거 UI: `http://localhost:8000/docs`
- OpenAPI 스펙: `http://localhost:8000/openapi.json`
- 비고
  - Flow 등록 후, 동적 실행 경로는 “Runnable Flows” 태그로 문서에 표시됩니다.
  - 서버 재시작 없이도 스케줄러가 주기적으로 라우트를 동기화합니다(`services/scheduler_service.py`).

## 12. 샘플 `flow_body` 스켈레톤

아래 예시는 `FlowCreate.flow_body`에 넣을 수 있는 최소 유효 구조 예시입니다. 실제 실행을 위해서는 LangFlow UI에서 Export한 JSON을 사용하는 것을 권장합니다.

```json
{
  "description": "간단한 입력을 받아 LLM 노드로 전달하는 예시",
  "name": "sample-summarizer",
  "id": "lf-sample-001",
  "is_component": false,
  "data": {
    "nodes": [
      {
        "id": "input-node",
        "type": "Input",
        "position": { "x": 100, "y": 120 },
        "data": {
          "label": "User Input",
          "params": {
            "key": "text"
          }
        }
      },
      {
        "id": "llm-node",
        "type": "LLM",
        "position": { "x": 420, "y": 120 },
        "data": {
          "label": "Chat Model",
          "params": {
            "model": "gpt-4o-mini",
            "system": "You are a concise assistant.",
            "prompt": "Summarize: {{text}}"
          }
        }
      }
    ],
    "edges": [
      {
        "id": "edge-input-to-llm",
        "source": "input-node",
        "target": "llm-node",
        "sourceHandle": "output",
        "targetHandle": "input"
      }
    ],
    "viewport": { "x": 0, "y": 0, "zoom": 1 }
  }
}
```

주의: `type`, `data.params` 등의 키는 사용하는 LangFlow 버전과 노드 구성에 따라 달라질 수 있습니다. 실제로는 LangFlow UI에서 설계 → Export 한 JSON을 그대로 사용하세요.
