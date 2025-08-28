### **OpenAI Agents SDK MCP 표준 기반 서버 도입을 위한 변경 범위**

#### **개요**

이 문서는 OpenAI Agents SDK의 Model Context Protocol (MCP) 표준을 준수하는 서버를 구축하기 위한 변경 사항을 설명합니다. 이 MCP 서버는 AI 모델 및 클라이언트 애플리케이션(예: LangFlow, OpenAI Agents 등)이 사용할 수 있는 도구(tools), 리소스(resources), 프롬프트(prompts) 등을 JSON-RPC 형태로 표준화된 방식으로 제공하며, AI 에이전트와 백엔드를 연결하는 브로커 역할을 수행합니다.

#### **I. 새로운 MCP 서버 구축**

새로운 MCP 서버는 OpenAI Agents SDK MCP 표준을 준수하여, AI 모델 및 클라이언트 애플리케이션에 도구, 리소스, 프롬프트를 JSON-RPC 형태로 제공하는 역할을 수행합니다.

**A. 핵심 기능**

1.  **도구(tool) 노출**: 외부 API 호출, 데이터베이스 쿼리, 파일 시스템 접근 등 실제 동작을 수행하는 기능을 “도구”라는 개념으로 MCP 클라이언트에 노출합니다.
2.  **리소스(resource) 제공**: 읽기 전용 데이터(예: 모델 메타데이터, 설정값) 목록을 MCP 클라이언트가 조회할 수 있도록 지원합니다.
3.  **프롬프트(prompt) 관리**: 언어모델이 도구를 효율적으로 사용할 수 있도록 설계된 지시문 템플릿을 제공합니다.

(참고: 대화 기록 관리, RAG 통합 등 기존에 논의되었던 컨텍스트 관리 기능은 MCP 서버가 노출하는 '도구' 또는 '리소스'의 형태로 구현되거나, MCP 서버 내부에서 프롬프트 관리를 위해 활용될 수 있습니다.)

**B. 기술 스택 (예시)**

*   **언어**: Python
*   **통신 프로토콜**: JSON-RPC 2.0 (stdio, HTTP+SSE, Streamable HTTP 지원)
*   **백엔드 서비스 연동**: MCP 서버가 노출하는 도구, 리소스, 프롬프트의 실제 로직을 구현하기 위해 CoE-Backend, RAG 마이크로서비스 등 기존 백엔드 서비스와 연동합니다.

**C. API 설계 (JSON-RPC 2.0 메서드 예시)**

MCP 서버는 JSON-RPC 2.0 규격에 따라 클라이언트의 요청을 처리합니다. 주요 메서드는 다음과 같습니다.

*   `initialize`: 클라이언트 초기화 및 서버가 지원하는 도구, 리소스, 프롬프트 목록 반환.
*   `tools/list`: 서버가 노출하는 도구의 목록과 파라미터 스펙 반환.
*   `tools/call`: 지정된 도구를 호출하고 그 결과를 반환. (MCP 서버는 이 호출을 받아 CoE-Backend 등 실제 로직을 가진 백엔드 서비스로 전달)
*   `resources/list`: 서버가 제공하는 리소스의 목록 반환.
*   `resources/get`: 지정된 리소스의 내용을 반환.
*   `prompts/list`: 서버가 관리하는 프롬프트 템플릿의 목록 반환.
*   `prompts/get`: 지정된 프롬프트 템플릿의 내용을 반환.

**통신 흐름 예시:**

1.  **초기화**: 클라이언트가 `initialize` 요청 → 서버가 지원하는 도구·리소스·프롬프트 목록 반환
2.  **도구 탐색**: 클라이언트가 `tools/list` 요청 → 서버가 사용 가능한 도구명과 파라미터 스펙 응답
3.  **도구 실행**: 클라이언트가 `tools/call` 요청(도구 이름, 인수) → 서버가 내부 백엔드(API, DB 등) 호출 후 결과 반환

**D. 데이터 모델**

MCP 표준에 따라 다음과 같은 주요 데이터 모델이 정의됩니다.

*   **Tool**: `name`, `description`, `parameters` (JSON Schema), `return_type` 등 도구의 메타데이터 및 스펙.
*   **Resource**: `name`, `description`, `type`, `content` (또는 `uri`) 등 리소스의 메타데이터 및 내용.
*   **Prompt**: `name`, `description`, `template` (프롬프트 템플릿 내용), `variables` 등 프롬프트의 메타데이터 및 구조.

**E. 구현 고려사항**

*   **JSON-RPC 2.0 구현**: 표준 규격에 맞는 메시지 파싱, 메서드 디스패치, 에러 처리 구현.
*   **전송 메커니즘**: stdio, HTTP+SSE, Streamable HTTP 등 지원할 전송 방식을 결정하고 구현.
*   **백엔드 서비스 연동**: `tools/call` 요청을 받아 CoE-Backend 등 실제 로직을 가진 백엔드 서비스로 요청을 전달하고 결과를 받아오는 로직 구현.
*   **인증 및 권한 부여**: MCP 서버 API에 대한 접근 제어. (예: 내부 통신 제한, API 키 발급 및 검증)
*   **확장성**: 요청 처리량 증가에 따른 서버 확장 전략.
*   **에러 핸들링 및 로깅**: 견고한 에러 처리 및 상세 로깅.

#### **II. 기존 CoE-Backend 수정**

기존 CoE-Backend는 MCP 서버의 클라이언트 역할을 수행하며 컨텍스트 관련 작업을 MCP 서버에 위임합니다. 또한, MCP 서버의 요청에 따라 특정 기능을 수행하는 워커(Worker) 역할도 겸할 수 있습니다.

**A. 컨텍스트 관리 로직 분리**

*   **TODO**: 기존 컨텍스트 관리 로직 재정의
    *   **대상 파일**: `services/chat_service.py`, `core/database.py` (대화 기록 관련), `services/vector/` (RAG 관련)
    *   **작업 내용**:
        *   **대화 기록**: `services/chat_service.py` 내의 `save_message`, `get_messages`, `get_session` 등 대화 기록을 직접 데이터베이스에 저장하거나 조회하는 로직을 식별합니다. 이 로직들은 MCP 서버가 제공하는 '도구' (예: `chat/save_message`, `chat/get_history`) 또는 '리소스' (예: `session/details`)로 재정의되어야 합니다. `core/database.py`에서 직접적인 DB 접근 코드도 MCP 서버의 도구 구현으로 이동하거나 MCP 서버를 통해 접근하도록 변경을 고려합니다.
        *   **RAG 통합**: `services/vector/` 디렉토리 내의 `chroma_service.py`, `embedding_service.py` 등 RAG 관련 로직은 이미 별도의 마이크로서비스로 존재하므로, MCP 서버가 이 RAG 마이크로서비스를 호출하는 '도구'를 노출하도록 설계합니다. CoE-Backend에서는 더 이상 RAG 로직을 직접 수행하지 않고, MCP 서버의 RAG 관련 도구를 호출하도록 변경합니다.
        *   **프롬프트 관리**: 현재 CoE-Backend 내에 하드코딩되거나 파일로 관리되는 프롬프트 템플릿이 있다면, 이를 MCP 서버의 '프롬프트' 리소스로 이동하고, CoE-Backend는 MCP 서버의 `prompts/get` 메서드를 통해 프롬프트를 가져오도록 변경합니다.

**B. MCP 서버 클라이언트 구현**

*   **TODO**: MCP 서버 클라이언트 구현
    *   **대상 파일**: `core/mcp_client.py` (새로 생성)
    *   **작업 내용**:
        *   `core/mcp_client.py` 파일을 생성하고, `jsonrpcclient` 라이브러리 등을 사용하여 MCP 서버에 대한 JSON-RPC 클라이언트를 구현합니다.
        *   MCP 서버의 각 JSON-RPC 메서드(예: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/get`, `prompts/list`, `prompts/get`)에 대응하는 비동기 함수를 정의합니다.
        *   **예시 (`core/mcp_client.py`):**
            ```python
            from jsonrpcclient import request
            import httpx

            MCP_SERVER_URL = "http://localhost:8001/jsonrpc" # 사이드카 통신을 위해 localhost 사용

            async def call_mcp_method(method: str, *args, **kwargs):
                async with httpx.AsyncClient() as client:
                    response = await client.post(MCP_SERVER_URL, json=request(method, *args, **kwargs))
                    response.raise_for_status()
                    return response.json()['result']

            async def mcp_initialize():
                return await call_mcp_method("initialize")

            async def mcp_get_prompt(prompt_name: str):
                return await call_mcp_method("prompts/get", name=prompt_name)

            async def mcp_call_tool(tool_name: str, **tool_args):
                return await call_mcp_method("tools/call", name=tool_name, args=tool_args)
            ```
        *   MCP 서버와의 통신 실패(네트워크 오류, 타임아웃, JSON-RPC 에러 응답 등)에 대한 견고한 에러 처리 및 재시도 로직을 구현합니다.

**C. 기존 코드 수정**

*   **TODO**: 기존 코드 수정
    *   **MCP 클라이언트 사용**:
        *   **대상 파일**: `api/chat_api.py`, `services/chat_service.py`, `core/llm_client.py` 등
        *   **작업 내용**:
            *   `api/chat_api.py`의 `handle_llm_proxy_request` 함수에서 LLM 호출 시 필요한 프롬프트 템플릿이나 기타 리소스(예: 모델 메타데이터)를 MCP 서버의 `prompts/get` 또는 `resources/get` 메서드를 통해 가져오도록 수정합니다.
            *   `services/chat_service.py` 내에서 대화 기록을 관리하던 로직을 MCP 서버의 도구(예: `chat/save_message`, `chat/get_history`)를 호출하도록 변경합니다.
            *   `core/llm_client.py`에서 LLM에 전달할 메시지나 컨텍스트를 구성할 때, MCP 서버의 프롬프트나 리소스를 활용하도록 수정합니다.
            *   **예시 (`api/chat_api.py` 내 `handle_llm_proxy_request` 수정):**
                ```python
                from core.mcp_client import mcp_get_prompt, mcp_call_tool # 새로 생성할 클라이언트 임포트

                async def handle_llm_proxy_request(req: OpenAIChatRequest):
                    # ... (기존 코드) ...

                    # 프롬프트 템플릿을 MCP 서버에서 가져오는 예시
                    # if req.model == "my-agent-model":
                    #     system_prompt_template = await mcp_get_prompt("agent_system_prompt")
                    #     # system_prompt_template을 사용하여 req.messages에 시스템 메시지 추가 또는 수정

                    # ... (기존 코드) ...

                    # LLM이 도구 호출을 결정했을 때, MCP 서버의 tools/call을 통해 실제 도구 실행
                    # (이 부분은 LLM 응답 처리 로직에서 발생하며, MCP 서버가 CoE-Backend의 도구를 호출하는 방식)
                    # if tool_call_from_llm:
                    #     tool_result = await mcp_call_tool(tool_call_from_llm.name, **tool_call_from_llm.args)
                    #     # tool_result를 LLM에 다시 전달
                ```
    *   **도구 구현 로직 노출**:
        *   **대상 파일**: `tools/openai_tools.py`, `api/coding_assistant/code_api.py`, `services/` 내의 특정 서비스 등
        *   **작업 내용**:
            *   MCP 서버의 `tools/call` 메서드에 의해 호출될 실제 도구 구현 로직을 CoE-Backend 내부에 구현합니다. (예: `tools/openai_tools.py`에 정의된 `search_web`, `read_file` 등의 실제 함수). MCP 서버가 이 로직에 접근할 수 있는 형태로 노출해야 합니다. 이는 CoE-Backend 내부에 JSON-RPC 서버를 구현하여 MCP 서버의 `tools/call` 요청을 받아 해당 함수를 직접 실행하는 방식이 될 수 있습니다. 또는 CoE-Backend가 별도의 내부 API 엔드포인트를 제공하고 MCP 서버가 이를 호출하는 형태가 될 수도 있습니다.
            *   **예시 (CoE-Backend 내부에 도구 실행을 위한 JSON-RPC 엔드포인트 구현):**
                ```python
                # api/mcp_tool_endpoint.py (새로 생성)
                from fastapi import APIRouter, Request
                from jsonrpcserver import async_dispatch
                import json
                from tools.openai_tools import tool_functions # 기존 도구 함수 임포트

                router = APIRouter()

                @router.post("/jsonrpc/tools")
                async def call_tool_from_mcp(request: Request):
                    request_json = await request.json()
                    response = await async_dispatch(request_json, methods=tool_functions) # tool_functions는 MCP가 호출할 수 있는 도구 함수 맵
                    return response
                ```
                *   (참고: `tool_functions`는 `tools/openai_tools.py`에 정의된 `search_web`, `read_file` 등의 실제 함수들을 포함하는 딕셔너리입니다.)
    *   **기타 관련 모듈**: MCP 서버가 제공하는 리소스나 프롬프트에 의존하는 다른 모듈들도 MCP 클라이언트를 사용하도록 업데이트합니다.

**D. 의존성 업데이트**

*   **TODO**: 의존성 업데이트
    *   **대상 파일**: `requirements.txt`
    *   **작업 내용**:
        *   컨텍스트 관리와 직접적으로 관련된 데이터베이스 클라이언트 라이브러리(예: `psycopg2`, `pymongo`)의 직접적인 의존성을 제거합니다. (이 로직은 MCP 서버의 도구 구현으로 이동)
        *   MCP 서버와의 JSON-RPC 통신을 위한 클라이언트 라이브러리(예: `jsonrpcclient`, `httpx`)를 추가합니다.
        *   CoE-Backend가 MCP 서버로부터 `tools/call` 요청을 받아 처리하는 JSON-RPC 서버 역할을 수행한다면, `jsonrpcserver` 라이브러리도 추가해야 합니다.

#### **III. 배포 및 운영 (사이드카 모델)**

MCP 서버는 CoE-Backend 애플리케이션의 사이드카(Sidecar) 형태로 배포됩니다. 이는 두 서비스가 동일한 환경(예: Kubernetes Pod) 내에서 함께 실행되며, 생명 주기, 네트워크, 자원을 공유함을 의미합니다.

*   **배포 방식**:
    *   MCP 서버는 CoE-Backend와 동일한 배포 단위(예: Docker Compose 서비스, Kubernetes Pod) 내에 컨테이너로 포함됩니다.
    *   두 컨테이너는 함께 시작하고 종료됩니다.
*   **통신 방식**:
    *   CoE-Backend와 MCP 서버 간의 통신은 `localhost`를 통해 이루어집니다. (예: `http://localhost:8001/jsonrpc`)
    *   네트워크 설정이 단순화되며, 외부 네트워크 트래픽이 발생하지 않습니다.
*   **확장성**:
    *   CoE-Backend 인스턴스를 확장하면 MCP 서버 인스턴스도 자동으로 함께 확장됩니다.
    *   두 서비스의 자원 사용량은 함께 고려되어야 합니다.
*   **모니터링 및 로깅**:
    *   두 서비스의 로그는 동일한 로깅 시스템으로 통합될 수 있으며, 모니터링도 함께 이루어집니다.

#### **IV. 다음 단계**

이 문서는 OpenAI Agents SDK MCP 표준을 기반으로 한 서버 도입을 위한 변경 범위를 설명합니다. 이 문서를 검토하신 후, 제안된 방향이 적절한지 확인해주시면 됩니다.
