# LangFlow 동적 API 연동 가이드

## 1. 개요 (Overview)

이 문서는 CoE-Backend 프로젝트에 구현된 LangFlow 동적 API 연동 기능에 대한 기술적인 내용과 사용법을 안내합니다.

이 기능의 핵심 목표는, LangFlow로 생성된 워크플로우(JSON 형태)를 데이터베이스에 저장하고, 이를 기반으로 실행 가능한 REST API 엔드포인트를 동적으로 생성 및 관리하는 것입니다. 이를 통해 서버 재시작 없이도 새로운 AI 워크플로우를 실시간으로 시스템에 통합하고 노출할 수 있습니다.

## 2. 핵심 기능 (Core Features)

- **동적 API 생성**: `POST /flows/` API를 통해 Flow를 등록하면, 해당 Flow를 실행할 수 있는 `POST /flows/run/{endpoint}` API가 실시간으로 생성됩니다.
- **데이터베이스 기반 관리**: 모든 Flow 정보는 `langflows` 데이터베이스 테이블에 영구적으로 저장 및 관리됩니다.
- **실시간 동기화**: 백그라운드 스케줄러가 주기적으로 데이터베이스 상태를 확인하여, 실행 중인 서버의 API 라우트 상태를 최신으로 동기화합니다.
- **모듈화된 아키텍처**: 기능별로 역할이 명확하게 분리된 서비스 모듈을 통해 유지보수성과 확장성을 높였습니다.

## 3. API 명세 (API Specification)

### Flow 관리 API

#### `POST /flows/`
- **설명**: 새로운 Flow를 등록하고, 해당 Flow를 실행할 수 있는 동적 API를 생성합니다.
- **Request Body**:
  ```json
  {
    "endpoint": "string (required, unique)",
    "description": "string (optional)",
    "flow_body": { /* LangFlow JSON Object */ },
    "flow_id": "string (required, unique)"
  }
  ```
- **Request Body Example**:
  ```json
  {
    "endpoint": "my-greeting-flow",
    "description": "A simple flow that returns a greeting.",
    "flow_id": "flow-abc-123",
    "flow_body": {
      "name": "Greeting Flow",
      "id": "flow-abc-123",
      "description": "A simple example flow",
      "data": {
        "nodes": [
          {
            "id": "node-1",
            "type": "InputNode",
            "position": {"x": 100, "y": 100},
            "data": {
              "input_name": "user_name",
              "input_type": "string"
            }
          },
          {
            "id": "node-2",
            "type": "OutputNode",
            "position": {"x": 400, "y": 100},
            "data": {
              "output_template": "Hello, {user_name}!"
            }
          }
        ],
        "edges": [
          {
            "id": "edge-1-2",
            "source": "node-1",
            "target": "node-2",
            "sourceHandle": "output",
            "targetHandle": "input"
          }
        ]
      }
    }
  }
  ```
- **Response**: 생성된 Flow의 상세 정보 (`FlowRead` 스키마)

#### `GET /flows/`
- **설명**: 데이터베이스에 등록된 모든 Flow의 목록을 조회합니다.
- **Response**: Flow 상세 정보의 배열 (`List[FlowRead]`)

#### `DELETE /flows/{flow_id}`
- **설명**: ID를 기준으로 특정 Flow를 비활성화(soft-delete)하고, 관련된 동적 API를 제거합니다.
- **Response**: 비활성화된 Flow의 상세 정보 (`FlowRead`)

### 동적으로 생성된 Flow 실행 API

#### `POST /flows/run/{endpoint}`
- **설명**: `/flows/`를 통해 등록된 Flow를 실행합니다. `{endpoint}` 부분은 Flow 등록 시 사용했던 `endpoint` 문자열로 대체됩니다.
- **Request Body**:
  ```json
  {
    "user_input": "any"
    /* Flow 실행에 필요한 자유로운 형태의 JSON 데이터 */
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "result": { /* langflow 라이브러리의 실행 결과 */ }
  }
  ```

## 4. 아키텍처 및 주요 모듈

이번 기능은 다음과 같은 모듈들의 유기적인 상호작용을 통해 구현되었습니다.

- **`main.py`**: FastAPI 애플리케이션의 메인 진입점. `lifespan` 관리자를 통해 서비스 생명주기를 관리하고 라우터를 포함합니다.

- **`core/lifespan.py`**: 애플리케이션의 시작/종료 이벤트를 관리합니다. `FlowRouterService`와 `SchedulerService`를 이곳에서 초기화하고 시작/종료합니다.

- **`core/database.py`**: `LangFlow` SQLAlchemy DB 모델을 정의합니다.

- **`core/schemas.py`**: `FlowCreate`, `FlowRead` 등 API에서 사용하는 Pydantic 데이터 모델을 정의합니다.

- **`api/flows_api.py`**: Flow 관리를 위한 API 엔드포인트(`POST /flows/`, `GET /flows/` 등)를 정의하는 최상위 API 계층입니다.

- **`services/db_service.py`**: `LangFlowService` 클래스가 Flow 데이터의 데이터베이스 CRUD(생성, 조회, 수정, 삭제) 로직을 전담합니다.

- **`services/flow_router_service.py`**: 실제 API 엔드포인트를 동적으로 생성(`add_flow_route`)하고 제거(`remove_flow_route`)하는 핵심 로직을 담당합니다.

- **`services/scheduler_service.py`**: 백그라운드에서 주기적으로 실행되며, `db_service`와 `flow_router_service`를 사용하여 DB와 실제 라우트의 상태를 동기화합니다.

- **`services/flow_service.py`**: API 계층과 다른 서비스들 사이의 '조정자(Orchestrator)' 역할을 합니다. 예를 들어, Flow 생성 요청이 오면 `db_service`에 저장을 요청하고, `flow_router_service`에 라우트 생성을 요청하는 흐름을 관리합니다.

## 5. 실행 흐름 (Execution Flow)

### Flow 신규 등록 시
1. 클라이언트가 `POST /flows/`로 요청을 보냅니다.
2. `api/flows_api.py`가 요청을 받아 `services/flow_service.py`의 `create_and_register_flow` 함수를 호출합니다.
3. `flow_service`는 `services/db_service.py`를 호출하여 받은 Flow 정보를 DB에 저장합니다.
4. DB 저장이 성공하면, `flow_service`는 `services/flow_router_service.py`를 호출하여 `POST /flows/run/{endpoint}` 라우트를 FastAPI 앱에 동적으로 추가합니다.
5. 최종적으로 생성된 Flow 정보를 클라이언트에 반환합니다.

### 서버 시작 시
1. `main.py`가 `core/lifespan.py`에 정의된 `lifespan` 관리자를 실행합니다.
2. `lifespan` 관리자가 `SchedulerService`를 초기화하고 `sync_routes_from_db` 함수를 호출합니다.
3. `sync_routes_from_db`는 DB에 저장된 모든 활성 Flow를 조회하여 `flow_router_service`를 통해 API 엔드포인트를 일괄적으로 생성합니다.
4. 이후, `SchedulerService`는 백그라운드에서 주기적으로 동기화 작업을 계속 수행합니다.
