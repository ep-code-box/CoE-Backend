# LangFlow 의미 기반 실행 가이드 (v2)

## 1. 개요 (Overview)

이 문서는 CoE-Backend 프로젝트에 구현된 LangFlow 연동 기능의 새로운 아키텍처를 설명합니다.

기존의 각 Flow를 개별 API 엔드포인트로 노출하는 방식에서, **중앙 AI 에이전트가 사용자의 의도를 분석하여 가장 적합한 Flow를 동적으로 찾아 실행**하는 방식으로 변경되었습니다. 이는 고정된 규칙이 아닌, 대화의 맥락과 의미를 기반으로 최적의 워크플로우를 선택하는 더 유연하고 지능적인 시스템을 지향합니다.

## 2. 핵심 개념: 2단계 LLM 라우팅

LangFlow 실행은 2단계에 걸친 LLM의 판단을 통해 이루어집니다.

1.  **1단계 (도구 유형 결정)**: 사용자의 요청을 받은 `tool_dispatcher`는 먼저 LLM에게 "이 요청을 처리하기 위해 간단한 Python 도구를 쓸까, 아니면 복잡한 LangFlow 워크플로우를 쓸까?"라고 질문합니다. 이때 LLM은 등록된 모든 Python 도구와 `run_best_langflow_workflow`라는 단 하나의 LangFlow 실행 도구 중에서 하나를 선택합니다.

2.  **2단계 (최적 Flow 결정)**: 만약 LLM이 `run_best_langflow_workflow`를 선택하면, `tool_dispatcher`는 다시 한번 LLM에게 질문합니다. 현재 `context`에 해당하는 모든 LangFlow의 `description`(설명) 목록을 보여주며, "사용자의 원래 질문에 가장 적합한 Flow는 이 목록 중 어느 것인가?"라고 물어 최적의 Flow 하나를 최종적으로 선택합니다.

이러한 2단계 구조를 통해, 시스템은 먼저 작업의 종류를 판단하고, 그 다음 해당 종류에 맞는 최적의 세부 워크플로우를 찾아내는 정교한 의사결정을 수행합니다.

## 3. LangFlow 등록 방법

새로운 아키텍처에서 LangFlow를 효과적으로 사용하려면, 등록 시 **`description`과 `context`를 명확하게 작성하는 것이 매우 중요합니다.**

-   **`description` (설명)**: 2단계 라우팅에서 LLM이 최적의 Flow를 판단하는 **유일한 근거**입니다. 이 Flow가 어떤 역할을 하는지, 어떤 입력에 적합한지, 어떤 결과를 내어주는지를 상세하고 명확하게 작성해야 AI가 올바른 선택을 할 수 있습니다.
-   **`context` (실행 환경)**: 이 Flow가 어떤 프론트엔드 환경(예: `aider`, `openWebUi`)에서 사용될 수 있는지를 지정합니다.

#### `POST /v1/flows`
- **설명**: 새로운 Flow를 등록합니다.
- **Request Body Example**:
  ```json
  {
    "endpoint": "generate-python-code-from-spec",
    "description": "사용자의 기능 요구사항 명세서(영어 또는 한글)를 입력받아, 그에 맞는 Python 클래스 또는 함수 코드를 자동으로 생성하는 전체 워크플로우입니다. 코드 생성 후에는 문법 검사까지 완료합니다.",
    "flow_id": "flow-generate-py-456",
    "flow_body": { /* LangFlow JSON Object */ },
    "context": "aider"
  }
  ```

## 4. 아키텍처 및 주요 모듈

- **`services/tool_dispatcher.py`**: **프로젝트의 두뇌**. 위에서 설명한 2단계 LLM 라우팅을 포함한 모든 의사결정과 실행을 총괄합니다.
- **`api/flows_api.py`**: LangFlow를 등록(`POST /v1/flows`)하고 관리하는 API 엔드포인트를 제공합니다.
- **`core/database.py`**: 등록된 LangFlow의 정보(`name`, `description`, `context` 등)가 `langflows` 테이블에 저장됩니다.
- **`services/db_service.py`**: `LangFlowService`가 데이터베이스 CRUD 로직을 담당합니다.

(참고: 기존의 `LangflowToolMapping` 테이블과 `flow_router_service`, `scheduler_service` 등은 더 이상 LangFlow의 동적 실행에 직접적으로 관여하지 않거나 역할이 변경되었습니다.)