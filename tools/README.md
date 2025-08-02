# 🔧 CoE-Backend 도구 개발자 가이드

이 문서는 CoE-Backend의 AI 에이전트가 사용하는 **도구(Tool)**를 개발하는 방법을 안내합니다.

## 🎯 핵심 개념: 도구 레지스트리 패턴

CoE-Backend는 **도구 레지스트리(Tool Registry)** 패턴을 사용하여 `main.py`나 에이전트 코드를 직접 수정하지 않고도 새로운 기능을 쉽게 추가할 수 있습니다.

`tools/registry.py`의 `load_all_tools()` 함수는 서버 시작 시 `tools` 디렉터리 내의 모든 파이썬 파일을 스캔하여, 특정 명명 규칙을 따르는 함수와 변수를 찾아 에이전트의 도구로 자동 등록합니다.

## 📜 도구 파일의 3가지 핵심 요소

새로운 도구를 추가하려면 `tools/` 디렉터리에 `.py` 파일을 생성하고 다음 세 가지 규칙에 따라 구성요소를 정의하면 됩니다.

### 1. 도구 설명 (`*_description` 또는 `*_descriptions`)

LLM 라우터가 어떤 상황에 이 도구를 사용해야 할지 판단하는 데 사용하는 메타데이터입니다.

-   **변수명:** `_description` 또는 `_descriptions`로 끝나야 합니다.
-   **형식:** `Dict` 또는 `List[Dict]`.
-   **필수 키:**
    -   `name` (str): 도구의 고유 이름. 노드 함수의 이름과 일치해야 합니다 (`<name>_node`).
    -   `description` (str): 도구의 기능을 명확하고 상세하게 설명하는 문장. LLM이 이 설명을 보고 도구를 선택하므로 매우 중요합니다.
-   **선택적 키:**
    -   `url_path` (str): 이 값을 지정하면 `/tools/<url_path>` 경로로 `GET`(정보 조회) 및 `POST`(도구 실행) API 엔드포인트가 자동으로 생성됩니다. (`api/tools/dynamic_tools_api.py` 참조)

**예시 (`basic_tools.py`):**
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

### 2. 노드 함수 (`*_node`)

도구의 실제 로직을 수행하는 함수입니다. LangGraph의 노드(Node)로 등록됩니다.

-   **함수명:** `<name>_node` 형식이어야 합니다. `name`은 도구 설명의 `name`과 일치해야 합니다.
-   **시그니처:** `(state: ChatState) -> Dict[str, Any]`
    -   `state` (`ChatState`): 에이전트의 현재 상태를 담고 있는 딕셔너리. 대화 기록(`messages`), 사용자 입력(`original_input`) 등이 포함됩니다.
-   **반환값:** `Dict[str, Any]`. 에이전트의 상태를 업데이트할 딕셔너리를 반환해야 합니다. 일반적으로 도구 실행 결과를 담은 메시지를 반환합니다.

**예시 (`basic_tools.py`):**
```python
from core.schemas import ChatState
from .utils import find_last_user_message

def tool1_node(state: ChatState) -> Dict[str, Any]:
    """Converts the last user message to uppercase."""
    user_content = find_last_user_message(state["messages"])
    if user_content:
        # 성공 시, assistant 역할의 메시지를 반환하여 상태를 업데이트
        return {"messages": [{"role": "assistant", "content": user_content.upper()}]}
    # 실패 시, system 역할의 에러 메시지를 반환
    return {"messages": [{"role": "system", "content": "Tool1 Error: User message not found."}]}
```

### 3. 특수 엣지 (`*_edges`) (고급)

기본적으로 모든 도구는 실행 후 라우터로 돌아갑니다. 하지만 특정 조건에 따라 다음 단계를 직접 지정하고 싶을 때 사용하는 변수입니다.

-   **변수명:** `_edges`로 끝나야 합니다.
-   **형식:** `Dict` 또는 `List[Dict]`.
-   **내용:** `{"source_node_name": "target_node_name"}` 형식의 딕셔너리.

**예시:**
```python
# 이 도구가 실행된 후에는 'human_feedback_node'로 이동하도록 지정
my_tool_edges = {
    "my_tool": "human_feedback"
}
```

## 🚀 단계별 새 도구 추가 가이드

`날씨를 알려주는 도구`를 추가하는 과정을 예시로 설명합니다.

### 1단계: 도구 파일 생성

`tools/weather_tool.py` 파일을 새로 만듭니다.

### 2단계: 도구 설명 정의

LLM이 "오늘 날씨 어때?"와 같은 질문에 이 도구를 선택할 수 있도록 상세한 설명을 작성합니다. API 엔드포인트도 추가해 보겠습니다.

```python
# tools/weather_tool.py

# 1. 도구 설명 정의
weather_tool_description = {
    "name": "get_weather",
    "description": "특정 지역의 현재 날씨 정보를 조회합니다. '서울 날씨 알려줘'와 같이 지역 이름이 포함되어야 합니다.",
    "url_path": "/tools/weather" # API 엔드포인트 자동 생성
}
```

### 3단계: 노드 함수 구현

사용자 메시지에서 지역을 추출하고, 외부 날씨 API를 호출하는 로직을 구현합니다.

```python
# tools/weather_tool.py
import re
import httpx # 외부 API 호출을 위한 라이브러리
from typing import Dict, Any
from core.schemas import ChatState
from .utils import find_last_user_message

# (설명 변수는 위에 정의됨)

# 2. 노드 함수 구현
async def get_weather_node(state: ChatState) -> Dict[str, Any]:
    user_message = find_last_user_message(state["messages"])
    if not user_message:
        return {"messages": [{"role": "system", "content": "오류: 사용자 메시지를 찾을 수 없습니다."}]}

    # 간단한 정규식으로 지역 이름 추출
    match = re.search(r"(.+?) 날씨", user_message)
    if not match:
        return {"messages": [{"role": "assistant", "content": "어느 지역의 날씨를 알려드릴까요?"}]}
    
    location = match.group(1).strip()
    
    try:
        # 외부 날씨 API 호출 (예시)
        api_url = f"https://api.weather.com/v1/current?location={location}"
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status() # 오류 발생 시 예외 발생
            weather_data = response.json()
            
            # 결과 포맷팅
            result_content = f"{location}의 현재 날씨: {weather_data['summary']}, 기온: {weather_data['temp']}°C"
            
            return {"messages": [{"role": "assistant", "content": result_content}]}

    except httpx.HTTPStatusError as e:
        return {"messages": [{"role": "system", "content": f"오류: 날씨 정보를 가져오는 데 실패했습니다. (HTTP {e.response.status_code})"}}
    except Exception as e:
        return {"messages": [{"role": "system", "content": f"오류: 날씨 정보 조회 중 예기치 않은 오류가 발생했습니다: {e}"}]}

```

### 4단계: 서버 재시작 및 테스트

개발 모드(`APP_ENV=development`)에서는 서버가 자동으로 재시작되며 새로운 `get_weather` 도구가 로드됩니다.

-   **AI 에이전트 테스트:** OpenWebUI나 `/v1/chat/completions` API를 통해 "서울 날씨 알려줘"라고 질문하여 테스트합니다.
-   **API 엔드포인트 테스트:**
    -   `GET http://localhost:8000/tools/weather` 로 도구 정보를 확인합니다.
    -   `POST http://localhost:8000/tools/weather` 로 도구를 직접 실행할 수 있습니다.

## ✨ 모범 사례

-   **단일 책임 원칙:** 각 도구는 하나의 명확한 기능만 수행하도록 설계하세요.
-   **명확한 설명:** LLM이 도구의 기능과 필요한 인수를 쉽게 이해할 수 있도록 `description`을 상세하게 작성하세요.
-   **견고한 에러 처리:** 외부 API 호출 실패, 잘못된 입력 등 예상 가능한 모든 오류 상황을 `try-except` 블록으로 처리하고, 사용자에게 친절한 메시지를 반환하세요.
-   **유틸리티 함수 활용:** 여러 도구에서 공통으로 사용되는 로직(예: 마지막 사용자 메시지 찾기)은 `tools/utils.py`에 작성하여 재사용하세요.
-   **로깅:** 디버깅을 위해 `logging` 모듈을 사용하여 주요 실행 단계나 오류 정보를 기록하세요.