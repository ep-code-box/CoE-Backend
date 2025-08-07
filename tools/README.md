# 도구 개발자 가이드

이 가이드는 CoE-Backend 시스템에 새로운 도구를 생성하고 통합하는 방법을 설명합니다. 도구는 특정 작업을 수행하고 메인 애플리케이션 그래프에 동적으로 로드되는 독립적인 Python 모듈입니다.

## 핵심 개념

- **동적 로딩:** `tools/registry.py`가 도구를 자동으로 발견하고 등록합니다. 새 도구를 수동으로 등록할 필요가 없습니다.
- **네이밍 컨벤션:** 동적 로딩 메커니즘은 도구 모듈 내의 함수 및 변수에 대한 엄격한 이름 지정 규칙에 의존합니다.
- **상태 관리:** 각 도구 노드는 대화 기록 및 기타 관련 데이터를 그래프를 통해 전달하는 `ChatState` 객체에서 작동합니다.
- **API 노출:** `api/tools/dynamic_tools_api.py`는 도구 설명에 `url_path`가 포함된 모든 도구를 자동으로 FastAPI 엔드포인트로 생성합니다. 이를 통해 각 도구를 직접 API로 호출할 수 있습니다.

## 새 도구를 만드는 방법

새 도구를 만들려면 다음 단계를 따르세요.

### 1. 도구 파일 생성

`/tools` 디렉토리 또는 그 하위 디렉토리에 새 Python 파일을 만듭니다 (예: `my_new_tool.py`).

### 2. 노드 함수 정의

이 함수는 도구의 핵심 로직을 포함합니다. 에이전트가 도구를 사용하기로 결정하면 실행됩니다.

- **이름:** 함수 이름은 반드시 `_node`로 끝나야 합니다. 예: `my_new_tool_node`.
- **매개변수:** `ChatState` 객체인 `state`라는 단일 인수를 받아야 합니다.
- **반환 값:** 상태를 업데이트하는 사전을 반환해야 합니다. 일반적으로 여기에는 대화 기록에 추가될 새 메시지 목록이 있는 `messages` 키가 포함됩니다.

**예시:**
```python
from typing import Dict, Any
from core.schemas import ChatState

def my_new_tool_node(state: ChatState) -> Dict[str, Any]:
    user_input = state.get("original_input", "")
    result_content = f"내 도구가 처리함: {user_input}"
    return {"messages": [{"role": "assistant", "content": result_content}]}
```

### 3. 도구 설명 추가

에이전트의 라우터는 이 설명을 사용하여 도구가 무엇을 하는지, 언제 사용해야 하는지 이해합니다.

- **이름:** 변수 이름은 단일 도구의 경우 `_description`으로, 파일 하나에 여러 도구가 있는 경우 `_descriptions`로 끝나야 합니다.
- **형식:** 다음 키를 가진 사전(또는 사전 목록)이어야 합니다.
    - `name`: 도구의 고유 식별자입니다. `_node` 접미사가 없는 노드 함수 이름과 일치해야 합니다 (예: `my_new_tool`).
    - `description`: 도구가 수행하는 작업에 대한 명확하고 간결한 설명입니다. 에이전트가 올바른 라우팅 결정을 내리는 데 매우 중요합니다.
    - `url_path`: (선택 사항) 도구를 외부 API 엔드포인트로 노출할 경우 사용하는 경로입니다. `dynamic_tools_api.py`가 이 경로를 사용합니다.

**예시 1: 단일 도구 (`_description`)**
```python
my_new_tool_description = {
    "name": "my_new_tool",
    "description": "새로운 단일 도구의 기능을 설명합니다.",
    "url_path": "/tools/my-new-tool"
}
```

**예시 2: 여러 도구 (`_descriptions`)**
```python
basic_tool_descriptions = [
    {
        "name": "tool1",
        "description": "텍스트를 대문자로 변환합니다.",
        "url_path": "/tools/tool1"
    },
    {
        "name": "tool2",
        "description": "텍스트를 역순으로 변환합니다.",
        "url_path": "/tools/tool2"
    }
]
```

### 4. (고급) 특수 엣지 정의

도구에 복잡한 제어 흐름(예: 실행 후 조건부 분기)이 필요한 경우 그래프에 대한 특수 엣지를 정의할 수 있습니다.

- **이름:** 변수 이름은 반드시 `_edges`로 끝나야 합니다.
- **형식:** 각 사전이 노드 간의 조건부 또는 표준 엣지를 정의하는 사전 목록입니다.

**예시 (`api_tool.py`에서):
```python
from langgraph.graph import END

def after_api_call(state: ChatState) -> str:
    return "class_analysis" if state.get("next_node") == "combined_tool" else END

api_tool_edges = [
    {
        "type": "conditional",
        "source": "api_call",
        "condition": after_api_call,
        "path_map": {"class_analysis": "class_analysis", END: END}
    }
]
```

## 자동 등록

네이밍 컨벤션(`_node`, `_description(s)`, `_edges`)을 따르는 한, `tools/registry.py`는 시작 시 자동으로 도구를 찾아 로드합니다. 추가 등록 단계는 필요하지 않습니다.
