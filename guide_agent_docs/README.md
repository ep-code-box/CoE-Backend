# Guide Agent Overview

LangGraph 기반 가이드 에이전트는 개발자가 어떤 작업을 진행해야 할지 빠르게 정리해 주는 상호작용형 보조자입니다. `/v1/chat/completions` 요청이 특정 조건을 만족하면 일반 에이전트 대신 가이드 그래프를 실행하여 요약, 계획, 추천, 참고 인사이트를 Markdown으로 반환합니다.

## High-Level Flow

1. 클라이언트가 `context="guide"` 또는 전용 `tool_input` 플래그로 요청을 보냅니다.
2. 서버는 `GuideAgent` 에게 전달할 `DeveloperContext`와 `SessionMemory`를 구성합니다.
3. LangGraph 그래프가 사용자의 질문, 선택된 프로필, 경로 목록, RAG 검색 결과를 토대로 계획과 추천을 생성합니다.
4. 결과는 `format_result_as_markdown` 유틸리티로 Markdown 메시지로 직렬화되며, 필요 시 추천 도구 실행 안내가 추가됩니다.
5. 추천 도구가 존재하면 세션에 대기 상태로 저장되고, 사용자의 후속 `guide_confirm`/`guide_cancel` 요청으로 실행 여부가 정해집니다.

## Triggering the Guide Agent

| 조건 | 설명 |
| --- | --- |
| `context="guide"` | 가장 간단한 진입 방법이며, 채팅 세션이 자동으로 가이드 모드로 전환됩니다. |
| `tool_input.guide_mode=true` | 일반 컨텍스트에서도 가이드를 실행합니다. Truthy 문자열(`"yes"`, `"1"`)도 허용됩니다. |
| `tool_input.guide_agent=true` / `tool_input.run_guide=true` | 예약된 추가 플래그로, UI나 스크립트에서 유연하게 사용할 수 있습니다. |

검증 로직은 `api/chat_api.py::_should_route_to_guide` 에 있으며, `tests/test_guide_agent.py` 에서 경계 케이스를 포함해 검증합니다.

## Request Payload Hints

- `tool_input.paths`: 문자열 리스트 또는 콤마 구분 문자열로 최대 10개의 경로를 전달합니다. LangGraph는 이 목록을 우선적으로 분석 대상으로 삼습니다.
- `tool_input.profile`: 명시하지 않으면 `group_name` 또는 `default` 프로필이 사용됩니다. 팀 단위 별도 프롬프트를 운영할 때 활용합니다.
- `tool_input.language` / `tool_input.locale`: 응답에 사용할 선호 언어를 소문자 코드로 넘깁니다. 기본값은 `ko` 입니다.
- 메타데이터에는 컨텍스트, 그룹, 요청 헤더 등을 포함시켜 추적성을 높입니다.
- 외부 RAG 파이프라인의 엔드포인트는 `GUIDE_AGENT_RAG_URL` 환경 변수로 지정하며, 미설정 시 `http://coe-ragpipeline-dev:8001` 가 사용됩니다. RAG 호출은 `core/guide_agent/rag_client.py` 를 통해 이루어집니다.

## Response Contract

- 메시지는 OpenAI 호환 응답의 `choices[0].message.content`에 Markdown 문자열로 포함됩니다.
- 기본 섹션
  - `**요약**`: 가이드가 파악한 핵심 상황 요약
  - `**계획 체크리스트**`: 따라야 할 단계 목록
  - `**추천 사항**`: 우선순위와 근거, 후속 행동이 포함된 권장 작업
  - `**참고 인사이트**`: 추가로 참고할 만한 아이디어/검색 결과
- 추천 도구가 있을 경우 `**권장 도구 실행 안내**` 섹션이 뒤따릅니다.

## Tool Suggestion Handshake

1. 가이드가 특정 도구 또는 LangFlow 실행이 필요하다고 판단하면 `tool_dispatcher.maybe_execute_best_tool` 을 사용해 세션에 권장 액션을 저장합니다.
2. 응답 메시지 끝에는 실행/취소 방법이 안내됩니다.
3. 사용자가 `tool_input.guide_confirm=true` 로 다시 요청하면 세션에 저장된 권장 도구가 실행됩니다.
4. 인자가 필요하면 `tool_input.guide_tool_args={...}` 로 JSON 인자를 함께 전달합니다. 이 값은 기존 권장 인자를 덮어씁니다.
5. 실행을 원하지 않으면 `tool_input.guide_cancel=true` 로 대기 중인 액션을 제거합니다.

세션 상태는 `services/chat_service.py` 를 통해 관리되며, 완료되면 일반 에이전트 히스토리와 동일하게 저장됩니다.

## Testing & Debugging

- `pytest -k "guide_agent"` 로 핵심 플로우를 빠르게 검증할 수 있습니다.
- RAG 응답이 비어 있을 때도 그래프가 정상적으로 요약을 생성해야 하므로, 로그에서 `Guide auto-route suggestion failed` 메시지가 반복된다면 설정을 확인하세요.
- 로컬 개발 중에는 `.env` 에 `GUIDE_AGENT_RAG_URL=http://localhost:8001` 등으로 오버라이드하고, 필요한 경우 `FakeRagClient`와 같은 목을 직접 주입할 수 있습니다.

## Related Modules

- `core/guide_agent/agent.py`: 그래프 초기화 및 결과 객체 변환
- `core/guide_agent/formatter.py`: Markdown 직렬화 로직
- `core/guide_agent/nodes.py`: LangGraph 노드 구현체와 RAG 결합 지점
- `api/chat_api.py::_handle_guide_agent_flow`: HTTP 엔드포인트와 가이드 에이전트 사이의 어댑터
- `tests/test_guide_agent.py`: 회귀 테스트

이 문서를 기반으로 UI나 스크립트에서 가이드 모드를 호출할 때 필요한 파라미터와 후속 흐름을 쉽게 정리할 수 있습니다.
