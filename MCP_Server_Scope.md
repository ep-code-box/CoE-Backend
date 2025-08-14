### **Model Context Protocol (MCP) 서버 도입을 위한 변경 범위**

#### **개요**

이 문서는 Model Context Protocol (MCP) 서버를 구축하고, 이 서버가 LLM 컨텍스트 관리뿐만 아니라 클라이언트(예: LangFlow)와 백엔드 서비스(예: CoE-Backend) 사이의 요청 라우팅 및 오케스트레이션 역할을 수행하도록 하는 변경 사항을 설명합니다. 이 아키텍처는 시스템의 모듈성, 확장성 및 유연성을 향상시킵니다.

#### **I. 새로운 MCP 서버 구축**

새로운 MCP 서버는 LLM과의 상호작용에 필요한 컨텍스트를 관리하고, 클라이언트 요청을 적절한 백엔드 서비스로 라우팅하며, 필요한 경우 여러 서비스 간의 호출을 오케스트레이션하는 역할을 수행합니다.

**A. 핵심 기능**

1.  **대화 기록 관리**: 사용자 및 어시스턴트 메시지를 세션/스레드별로 저장, 조회, 업데이트합니다.
2.  **외부 지식 통합 (RAG)**: 기존 RAG 마이크로서비스를 호출하여 외부 문서, 데이터베이스 등에서 검색된 관련 정보를 가져와 모델 컨텍스트에 주입할 수 있도록 제공합니다.
3.  **도구 사용 결과 저장**: 모델이 사용한 도구의 입력, 출력, 실행 상태 등을 저장하여 다음 턴의 컨텍스트로 활용합니다.
4.  **세션 및 사용자 관리**: 다양한 대화 세션 또는 사용자별 컨텍스트를 구분하고 관리합니다.
5.  **컨텍스트 압축/요약**: LLM의 토큰 한계를 고려하여, 필요한 경우 컨텍스트를 요약하거나 가장 관련성 높은 부분만 선택하여 제공하는 로직을 포함합니다.
6.  **요청 처리 및 오케스트레이션**: 클라이언트(예: LangFlow)로부터 받은 요청을 처리하기 위해, MCP 서버 내부적으로 CoE-Backend 등 적절한 백엔드 서비스의 API를 호출하고, 필요한 경우 여러 서비스 간의 호출 흐름을 조정하여 결과를 통합하여 반환합니다.

**B. 기술 스택 (예시)**

*   **언어**: Python
*   **웹 프레임워크**: FastAPI (비동기 처리 및 자동 문서화 용이)
*   **데이터베이스**:
    *   대화 기록 및 세션 메타데이터: PostgreSQL, MongoDB 등 (현재 `core/database.py`에서 사용하는 DB와 연동 또는 별도 구축)
    *   (참고: RAG를 위한 벡터 데이터베이스는 별도의 RAG 마이크로서비스에서 관리됩니다.)
*   **LLM 클라이언트**: 컨텍스트 요약 등을 위해 LLM 호출이 필요할 수 있음.

**C. API 설계 (RESTful API 예시)**

MCP 서버는 클라이언트(예: LangFlow)로부터 요청을 받아 처리하고, 필요한 경우 CoE-Backend 등 적절한 백엔드 서비스의 API를 호출하여 결과를 통합하여 반환합니다.

*   `POST /sessions`: 새 대화 세션 생성
*   `GET /sessions/{session_id}`: 특정 세션 정보 조회
*   `POST /sessions/{session_id}/messages`: 세션에 메시지 추가
*   `GET /sessions/{session_id}/messages`: 세션의 대화 기록 조회
*   `GET /sessions/{session_id}/context`: LLM에 전달할 최종 컨텍스트 생성 및 반환 (대화 기록, RAG 마이크로서비스 호출 결과, 도구 결과 등 통합)
    *   (참고: RAG 기능은 기존 RAG 마이크로서비스의 API를 호출하여 수행됩니다.)

**D. 데이터 모델**

*   `Session`: `session_id`, `user_id`, `created_at`, `updated_at`, `metadata`
*   `Message`: `message_id`, `session_id`, `role`, `content`, `timestamp`, `tool_calls`, `tool_call_id`
*   `KnowledgeChunk`: `chunk_id`, `content`, `embedding`, `source`, `metadata`
*   `ToolExecution`: `execution_id`, `session_id`, `tool_name`, `tool_input`, `tool_output`, `timestamp`

**E. 구현 고려사항**

*   **인증 및 권한 부여**: MCP 서버 API에 대한 접근 제어.
*   **확장성**: 컨텍스트 데이터 증가에 따른 데이터베이스 및 서버 확장 전략.
*   **에러 핸들링 및 로깅**: 견고한 에러 처리 및 상세 로깅.

#### **II. 기존 CoE-Backend 수정**

기존 CoE-Backend는 MCP 서버의 클라이언트 역할을 수행하며 컨텍스트 관련 작업을 MCP 서버에 위임합니다. 또한, MCP 서버의 요청에 따라 특정 기능을 수행하는 워커(Worker) 역할도 겸할 수 있습니다.

**A. 컨텍스트 관리 로직 분리**

*   **`services/chat_service.py`**: 현재 대화 기록을 직접 관리하는 로직(예: 데이터베이스에 메시지 저장/조회)을 제거하거나 MCP 서버 호출로 대체합니다.
*   **`core/llm_client.py`**: LLM 호출 시 컨텍스트를 구성하는 로직(예: 메시지 목록 준비)에서 MCP 서버를 통해 컨텍스트를 가져오도록 변경합니다.
*   **RAG 관련 로직**: 만약 현재 백엔드 내에 RAG를 위한 문서 검색 및 임베딩 로직이 있다면, 이를 MCP 서버로 이동하거나 MCP 서버의 RAG API를 호출하도록 변경합니다.

**B. MCP 서버 클라이언트 구현**

*   **새 모듈 생성**: `core/mcp_client.py` 또는 `services/mcp_service.py`와 같은 새로운 Python 모듈을 생성합니다.
*   **API 호출 캡슐화**: 이 모듈은 MCP 서버의 API 엔드포인트들을 호출하는 함수들을 포함합니다 (예: `create_session()`, `add_message()`, `get_context()`).
*   **에러 처리 및 재시도**: MCP 서버와의 통신 실패에 대한 견고한 에러 처리 로직을 포함합니다.

**C. 기존 코드 수정**

*   **`api/chat_api.py`**: `handle_llm_proxy_request` 함수 및 기타 채팅 관련 API 엔드포인트에서 컨텍스트가 필요할 때, 직접 컨텍스트를 구성하는 대신 새로 구현된 MCP 클라이언트를 통해 컨텍스트를 가져오도록 수정합니다.
*   **`services/chat_service.py`**: 대화 시작, 메시지 처리 등에서 MCP 클라이언트를 사용하여 세션 및 메시지를 관리하도록 변경합니다.
*   **MCP에 의해 호출될 API 노출**: MCP 서버가 CoE-Backend의 특정 기능을 호출해야 하는 경우(예: 특정 도구 실행, 내부 로직 수행 등), CoE-Backend는 해당 기능을 API 엔드포인트로 노출해야 합니다.
*   **기타 관련 모듈**: 컨텍스트에 의존하는 다른 모듈들도 MCP 클라이언트를 사용하도록 업데이트합니다.

**D. 의존성 업데이트**

*   기존 백엔드의 `requirements.txt`에서 컨텍스트 관리와 직접적으로 관련된 데이터베이스 클라이언트 라이브러리(예: `psycopg2`, `pymongo`)의 직접적인 의존성을 제거하거나, MCP 서버와의 통신에 필요한 라이브러리(예: `httpx`, `requests`)를 추가합니다.

#### **III. 배포 및 운영**

*   **별도 배포**: MCP 서버는 기존 CoE-Backend와 독립적으로 배포되어야 합니다.
*   **네트워크 구성**: CoE-Backend와 MCP 서버 간의 안전하고 효율적인 통신을 위한 네트워크 설정 (내부망 통신, 방화벽 규칙 등).
*   **모니터링 및 로깅**: 두 서비스 모두에 대한 독립적인 모니터링 및 로깅 시스템 구축.

#### **IV. 다음 단계**

이 문서를 검토하신 후, 제안된 방향이 적절한지 확인해주시면 됩니다. 특히, MCP 서버의 내부 구현에 특정 "Model Context Protocol" 표준(예: LangChain의 Memory 모듈 방식)을 적용하고 싶으시다면 알려주시기 바랍니다.
