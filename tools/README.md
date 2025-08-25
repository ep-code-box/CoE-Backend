# 도구 개발자 가이드 (v2)

이 문서는 CoE-Backend 시스템에 새로운 도구를 생성하고 통합하는 방법을 설명합니다. 새로운 아키텍처는 **통합된 동적 디스패처**를 기반으로 하며, 모든 도구는 `services/tool_dispatcher.py`를 통해 관리됩니다.

## 핵심 개념

- **통합 디스패처**: `services/tool_dispatcher.py`가 모든 도구(Python, LangFlow)의 검색, 실행, 목록 관리를 전담합니다. 기존의 `tools/registry.py`는 더 이상 사용되지 않습니다.
- **두 가지 도구 유형**:
  1.  **Python 도구**: `tools` 디렉토리 내에 `.py` 파일로 직접 구현된 도구입니다.
  2.  **LangFlow 도구**: LangFlow UI로 생성된 워크플로우를 API를 통해 도구로 등록한 것입니다.
- **매핑(Mapping) 기반 검색**:
  - Python 도구는 `_map.py` 파일을 통해 `tool_contexts`와 연결됩니다.
  - LangFlow 도구는 데이터베이스의 `langflow_tool_mappings` 테이블을 통해 `tool_name`과 `context`로 연결됩니다.
- **`tool_name`**: 도구의 고유한 이름입니다. (예: `my_new_tool`, `sub_graph`)
- **`context`**: 도구가 속하는 환경 또는 그룹을 나타내는 문자열입니다. (예: `aider`, `continue.dev`, `openWebUi`)

## 새로운 Python 도구 만드는 방법

### 1단계: 도구 파일 생성 (`xxx_tool.py`)

`/tools` 디렉토리 또는 그 하위 디렉토리에 `_tool.py`로 끝나는 새 Python 파일을 만듭니다. (예: `my_new_tool.py`)

이 파일은 다음 세 가지 요소를 포함해야 합니다.

1.  **`run(tool_input, state)` 함수 (필수)**: 도구의 핵심 로직을 포함하는 진입점 함수입니다.
    - `tool_input`: 클라이언트가 제공한 구조화된 입력값 (dict). 없을 경우 None이 전달됩니다.
    - `state`: `AgentState` 객체. `tool_input`이 없을 경우, 이 `state`의 대화 기록(`history`) 등에서 필요한 정보를 파싱해야 합니다.

2.  **`available_tools` 변수 (선택적, LLM 자동 호출용)**: LLM이 이 도구를 이해하고 스스로 호출할 수 있도록, 도구의 스키마를 정의한 리스트입니다. (OpenAI Function Calling 형식)

3.  **`tool_functions` 변수 (선택적, LLM 자동 호출용)**: 도구의 이름과 실제 함수를 매핑하는 딕셔너리입니다.

**예시: `my_new_tool.py`**
```python
from typing import Dict, Any, List, Optional
from core.schemas import AgentState

# 1. 핵심 로직
async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> str:
    if tool_input and 'name' in tool_input:
        user_name = tool_input['name']
    else:
        # tool_input이 없을 경우, 대화 기록에서 이름 찾기 (예시)
        user_name = "Guest"
        for message in reversed(state['history']):
            if message['role'] == 'user':
                # 실제로는 더 정교한 파싱 로직 필요
                user_name = message['content'].split()[-1]
                break
    return f"Hello, {user_name}! This is my new tool."

# 2. LLM을 위한 도구 스키마
my_new_tool_schema = {
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "사용자에게 새로운 방식으로 인사합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "사용자의 이름"}
            }
        }
    }
}

available_tools: List[Dict[str, Any]] = [my_new_tool_schema]

# 3. LLM을 위한 함수 매핑
tool_functions: Dict[str, callable] = {
    "my_new_tool": run
}
```

### 2단계: 매핑 파일 생성 (`xxx_map.py`)

`_tool.py` 파일과 같은 위치에 `_map.py` 파일을 생성합니다. 이 파일은 도구가 속하는 `context`와 API `endpoints`를 지정하는 역할을 합니다.

- 파일 안에는 `tool_contexts`라는 이름의 리스트를 정의해야 합니다.
- `endpoints` 딕셔너리는 선택 사항이며, 도구 함수 이름과 API 경로를 매핑합니다.

**예시: `my_new_map.py`**
```python
# 이 도구가 속하는 컨텍스트를 정의합니다.
tool_contexts = [
    "aider",
    "continue.dev"
]

# (선택 사항) 이 도구의 함수들을 외부 API로 노출할 경로를 정의합니다.
endpoints = {
    "my_new_tool": "/tools/my-new-tool-api"
}
```

## 새로운 LangFlow 도구 만드는 방법

### 1단계: LangFlow UI에서 Flow 생성

먼저 LangFlow UI를 사용하여 원하는 워크플로우를 생성합니다.

### 2단계: Flow를 도구로 등록

`POST /flows/` API를 호출하여 생성된 Flow를 시스템에 등록합니다. 이 때, `tool_name`과 `context` 필드를 반드시 포함해야 합니다.

**요청 예시:**
```bash
cURL -X POST "http://localhost:8000/flows/" \
  -H "Content-Type: application/json" \
  -d {
    "endpoint": "my-langflow-endpoint",
    "description": "A simple LangFlow tool.",
    "flow_id": "flow-abc-123",
    "flow_body": { ... },
    "tool_name": "my_first_langflow_tool",  # <-- 도구 이름
    "context": "my_team_context"            # <-- 도구 컨텍스트
  }
```

요청이 성공하면, `langflow_tool_mappings` 데이터베이스 테이블에 해당 정보가 자동으로 저장되어 도구로 사용할 수 있게 됩니다.

## 도구 실행 방식

1.  **직접 실행**: 클라이언트가 `tool_name`과 `context`를 지정하여 `coe-agent`에 요청하면, 디스패처가 해당 이름의 도구를 즉시 찾아 실행합니다.
2.  **LLM 자동 실행**: 클라이언트가 `tool_name`과 `context` 없이 일반적인 대화를 요청하면, `coe-agent`는 현재 `context`에 맞는 도구들의 스키마(`available_tools`)를 LLM에 제공합니다. LLM은 대화의 맥락에 가장 적합한 도구가 있다고 판단하면, 해당 도구를 사용하라는 응답을 보내고, 디스패처는 그에 따라 도구를 실행합니다.