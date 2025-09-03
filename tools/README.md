# 도구 개발자 가이드 (v3.1)

이 문서는 CoE-Backend 시스템에 새로운 도구를 생성하고 통합하는 방법을 설명합니다. 이 시스템의 아키텍처는 **중앙 집중형 도구 디스패처**를 기반으로 하며, 모든 도구 관련 결정과 실행은 `services/tool_dispatcher.py`가 전담합니다.

## 핵심 개념

- **중앙 디스패처 (Central Dispatcher)**: `services/tool_dispatcher.py`가 에이전트의 핵심 두뇌 역할을 합니다. 이 디스패처는 사용자 문의의 의도를 분석하여 가장 적합한 도구를 결정하고 실행까지 책임집니다.
- **`context` 기반 도구 제공**: 특정 `context`(프론트엔드 환경)에서 사용 가능한 도구들의 목록을 LLM에게 제공하여, LLM이 이 중에서 최적의 도구를 선택하도록 합니다.
- **도구 유형 및 실행 방식**:
  1.  **Python 도구**: 명확한 기능이 있는 정적(static) 도구입니다. LLM은 여러 Python 도구 중 가장 적합한 것의 **이름**을 선택하여 실행을 요청합니다.
  2.  **LangFlow 워크플로우**: 복잡한 작업을 처리하는 동적(dynamic) 워크플로우입니다. `execute_langflow` 도구를 사용하여 이름으로 특정 워크플로우를 실행합니다.

---

## 사용 가능한 도구 목록

다음은 현재 시스템에서 사용 가능한 도구 목록입니다.

### 1. RAG 기반 개발 가이드 추출 (`rag_guide_tool`)

- **설명**: Git 레포지토리를 분석하여 개발 가이드를 추출하거나, 새로운 RAG 분석을 시작합니다. `CoE-RagPipeline` 서비스와 연동하여 작동합니다.
- **파라미터**:
    - `git_url` (string, 선택): 분석할 Git 레포지토리 URL. 제공되면 새로운 분석을 시작합니다.
    - `analysis_id` (string, 선택): 기존 분석 ID. 제공되면 해당 분석 결과를 사용하여 가이드를 추출합니다.
    - `group_name` (string, 선택): 분석 결과를 묶을 그룹명.
- **사용 예시**:
    - 새로운 분석 시작: "https://github.com/my-org/my-repo 레포지토리 분석해줘"
    - 기존 분석으로 가이드 추출: "analysis_id abc-123-def로 개발 가이드 추출해줘"

### 2. LangFlow 관리 (`langflow_tool`)

- **설명**: 저장된 LangFlow 워크플로우를 실행하거나 목록을 조회합니다.
- **도구**:
    - `execute_langflow`: 이름으로 특정 LangFlow를 실행합니다.
        - **파라미터**: `flow_name` (string, 필수) - 실행할 LangFlow의 이름.
        - **사용 예시**: "my-flow 실행해줘"
    - `list_langflows`: 저장된 모든 LangFlow의 목록을 보여줍니다.
        - **파라미터**: 없음
        - **사용 예시**: "저장된 플로우 목록 보여줘"

### 3. 텍스트 분석 (`class_tool`)

- **설명**: 간단한 텍스트 분석을 수행합니다.
- **도구**:
    - `class_call`: 텍스트의 길이와 단어 수를 분석합니다.
        - **파라미터**: `text` (string, 선택) - 분석할 텍스트.
        - **사용 예시**: "이 문장 분석해줘: 안녕하세요"
    - `combined_tool`: API 호출과 분석을 조합하는 작업을 위한 플레이스홀더입니다. (현재는 입력 텍스트를 그대로 반환)

### 4. LangChain 기반 분석 (`langchain_tool`)

- **설명**: LangChain Expression Language(LCEL)를 사용하여 텍스트를 요약하고 감성을 분석합니다.
- **도구**:
    - `langchain_chain`: 텍스트를 요약하고 감성(긍정/부정/중립)을 분석합니다.
        - **파라미터**: `text` (string, 필수) - 분석할 텍스트.
        - **사용 예시**: "이 긴 글을 요약하고 감성을 알려줘"

### 5. SQL 에이전트 (`sql_agent_tool`)

- **설명**: 자연어 질문을 SQL로 변환하고 데이터베이스에 쿼리하여 답변을 생성합니다. `CoE-RagPipeline`의 SQL Agent와 연동됩니다.
- **파라미터**: `query` (string, 필수) - 데이터베이스에 질문할 자연어 쿼리.
- **사용 예시**: "지난 달 가장 많이 팔린 제품이 뭐야?"

### 6. 서브그래프 호출 (`subgraph_tool`)

- **설명**: 미리 정의된 간단한 LangGraph 서브그래프를 호출하여 인사말을 반환하는 예제 도구입니다.
- **파라미터**: 없음
- **사용 예시**: "안녕"

### 7. 대화 및 워크플로우 시각화 (`visualize_flow_tool`)

- **설명**: 대화 기록을 시각화하거나 사용자의 요청에 맞는 새로운 LangFlow 워크플로우를 생성합니다.
- **도구**:
    - `visualize_conversation_as_langflow`: 현재까지의 대화 기록을 LangFlow 그래프 형식의 JSON으로 변환하여 시각화합니다.
        - **파라미터**: 없음
        - **사용 예시**: "지금까지 대화 내용 그려줘"
    - `generate_langflow_workflow`: 사용자의 요청을 분석하여 해당 기능을 수행하는 LangFlow 워크플로우 JSON을 생성합니다.
        - **파라미터**: `input` (string, 필수) - 생성할 워크플로우에 대한 상세한 설명.
        - **사용 예시**: "사용자 입력을 받아서 텍스트를 번역하고, 결과를 이메일로 보내는 워크플로우 만들어줘"

---

## 신규 도구 개발 가이드

새로운 Python 도구를 만들어 시스템에 통합하는 방법은 간단합니다. 다음 두 단계만 따르면 됩니다.

### 1단계: 도구 파일 생성 (`*_tool.py`)

`/tools` 디렉토리 또는 그 하위 디렉토리에 `_tool.py`로 끝나는 새 Python 파일을 만듭니다. 이 파일은 도구의 핵심 로직과 명세를 담고 있습니다.

**파일 필수 구성 요소:**

1.  **`run(tool_input, state)` 함수**:
    *   도구의 실제 로직을 포함하는 **필수** 진입점 함수입니다.
    *   `tool_input` (dict): LLM이 생성한 인자들을 담고 있습니다.
    *   `state` (AgentState): 전체 대화 기록, 사용자 입력 등 에이전트의 현재 상태 정보가 담겨 있습니다.
    *   반환값은 도구 실행 결과를 담은 딕셔너리여야 합니다. (예: `{"messages": [{"role": "assistant", "content": "결과"}]}`)

2.  **`available_tools` 변수**:
    *   LLM이 도구를 이해하고 사용할 수 있도록 OpenAI Function Calling 형식의 스키마를 정의한 **필수** 리스트입니다.
    *   `name`: LLM이 사용할 도구의 이름입니다.
    *   `description`: LLM이 도구의 용도를 파악할 수 있는 상세한 설명입니다.
    *   `parameters`: 도구가 필요로 하는 인자들의 명세입니다.

**예시: `my_greeting_tool.py`**
```python
from typing import Dict, Any, List, Optional
from core.schemas import AgentState

# 1. 'run' 함수 (필수)
async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """도구의 진입점 함수입니다."""
    user_name = "Guest"
    if tool_input and 'name' in tool_input:
        user_name = tool_input['name']
    else:
        # tool_input이 없는 경우, 상태(state)에서 정보 추출 시도
        last_message = state.get("input", "")
        # (실제로는 여기서 더 정교한 파싱 로직이 필요할 수 있습니다)
        if "이름은" in last_message:
            user_name = last_message.split("이름은")[1].strip().split(" ")[0]

    greeting = f"Hello, {user_name}! Welcome to the new tool system."
    
    # 항상 딕셔너리 형태로 결과를 반환해야 합니다.
    return {"messages": [{"role": "assistant", "content": greeting}]}

# 2. 'available_tools' 변수 (필수)
my_greeting_tool_schema = {
    "type": "function",
    "function": {
        "name": "greet_user_in_a_new_way",
        "description": "사용자에게 개인화된 새로운 방식으로 인사합니다. 사용자의 이름이 필요할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string", 
                    "description": "인사할 사람의 이름"
                }
            }
            # 'name'이 필수 인자가 아니라면 'required' 필드를 생략하거나 비워둡니다.
        }
    }
}

available_tools: List[Dict[str, Any]] = [my_greeting_tool_schema]

# 3. 'tool_functions' 변수 (필수)
# 'available_tools'에 정의된 name과 실제 실행 함수를 매핑합니다.
tool_functions: Dict[str, callable] = {
    "greet_user_in_a_new_way": run
}
```

### 2단계: 매핑 파일 생성 (`*_map.py`)

`_tool.py` 파일과 같은 위치에 `_map.py` 파일을 생성합니다. 이 파일은 도구의 메타데이터를 정의합니다.

**파일 필수 구성 요소:**

1.  **`tool_contexts` 변수**:
    *   도구가 활성화될 프론트엔드 환경 목록을 리스트로 정의합니다. (예: `["aider", "openWebUi"]`)
    *   LLM은 현재 `context`에 맞는 도구들만 제공받게 됩니다.

2.  **`endpoints` 변수** (선택 사항):
    *   도구를 외부 API로 직접 노출하고 싶을 때 사용합니다.
    *   `{ "도구_이름": "/api/경로" }` 형식의 딕셔너리로 정의합니다.

**예시: `my_greeting_map.py`**
```python
# 이 도구가 사용될 수 있는 컨텍스트를 정의합니다.
tool_contexts = [
    "aider",
    "openWebUi"
]

# 도구를 직접 호출할 수 있는 API 엔드포인트를 정의합니다.
endpoints = {
    "greet_user_in_a_new_way": "/tools/greet-user"
}
```

이 두 파일만 생성하면, 시스템이 자동으로 도구를 인식하고 `tool_dispatcher`와 LLM 라우터가 상황에 맞게 도구를 사용하게 됩니다.

---

## 튜토리얼: '만 나이 계산기' 만들어보기

이론만으로는 지루할 수 있으니, 간단한 '만 나이 계산기' 도구를 함께 만들어보며 전체 과정을 익혀보겠습니다.

### 목표

사용자가 "1995년 3월 15일생은 몇 살이야?"라고 물으면, 만 나이를 계산해서 "생년월일 1995-03-15 기준, 만 나이는 X세입니다."라고 대답하는 도구를 만듭니다.

### 1단계: 로직 파일 `age_calculator_tool.py` 생성

먼저 `/tools` 폴더에 `age_calculator_tool.py` 파일을 생성하고 아래 내용을 채웁니다.

```python
from typing import Dict, Any, List, Optional
from core.schemas import AgentState
from datetime import datetime

# 1. 'run' 함수 (필수)
async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """생년월일을 기준으로 만 나이를 계산합니다."""
    if not tool_input or 'birth_date' not in tool_input:
        return {"messages": [{"role": "assistant", "content": "생년월일을 'YYYY-MM-DD' 형식으로 알려주세요."}]}

    try:
        birth_date_str = tool_input['birth_date']
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.today()
        
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        result_message = f"생년월일 {birth_date_str} 기준, 만 나이는 {age}세입니다."
        return {"messages": [{"role": "assistant", "content": result_message}]}

    except ValueError:
        return {"messages": [{"role": "assistant", "content": "생년월일 형식이 잘못되었습니다. 'YYYY-MM-DD' 형식으로 입력해주세요."}]}

# 2. 'available_tools' 변수 (필수)
age_calculator_tool_schema = {
    "type": "function",
    "function": {
        "name": "calculate_international_age",
        "description": "주어진 생년월일(YYYY-MM-DD)을 기준으로 만 나이를 계산합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "birth_date": {
                    "type": "string",
                    "description": "계산할 생년월일. YYYY-MM-DD 형식입니다."
                }
            },
            "required": ["birth_date"]
        }
    }
}

available_tools: List[Dict[str, Any]] = [age_calculator_tool_schema]

# 3. 'tool_functions' 변수 (필수)
tool_functions: Dict[str, callable] = {
    "calculate_international_age": run
}
```
- **핵심 로직**: `run` 함수는 `datetime` 라이브러리를 사용해 오늘 날짜와 생년월일을 비교하여 만 나이를 계산합니다.
- **AI와의 소통**: `available_tools` 스키마는 AI에게 이 도구의 이름(`calculate_international_age`), 기능 설명, 그리고 필요한 파라미터(`birth_date`)가 무엇인지 명확히 알려줍니다.

### 2단계: 매핑 파일 `age_calculator_map.py` 생성

같은 위치에 `age_calculator_map.py` 파일을 생성하고, 이 도구가 어떤 환경에서 사용될지 정의합니다.

```python
# 이 도구가 사용될 수 있는 컨텍스트를 정의합니다.
tool_contexts = [
    "aider",
    "openWebUi"
]

# 도구를 직접 호출할 수 있는 API 엔드포인트를 정의합니다. (선택 사항)
endpoints = {
    "calculate_international_age": "/tools/calculate-age"
}
```
- **`tool_contexts`**: 이 도구가 `aider`와 `openWebUi` 컨텍스트에서 활성화되도록 설정했습니다.

### 3단계: 테스트

이제 모든 준비가 끝났습니다! 에이전트에게 다음과 같이 질문해 보세요.

> "1995년 3월 15일생 만 나이 알려줘"

에이전트는 우리 의도대로 `calculate_international_age` 도구를 찾아 실행하고, 계산된 나이를 답변해 줄 것입니다. 이처럼 새로운 기능을 도구로 만들어 쉽게 확장할 수 있습니다.

---

## 도구 실행 예시 (cURL)

### 1. 에이전트를 통한 실행 (권장)

중앙 에이전트(`/v1/chat/completions`)에 자연어 질문을 보내면, 에이전트가 스스로 의도를 파악하고 최적의 도구를 선택하여 실행합니다.

**예시: `rag_guide_tool` 실행 요청**
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d 
    "model": "ax4",
    "messages": [
      {
        "role": "user",
        "content": "https://github.com/my-org/my-repo 레포지토리 분석해서 개발 가이드 만들어줘"
      }
    ],
    "context": "aider"
  }
```

### 2. 개별 API를 통한 직접 실행

테스트나 특정 연동 시나리오를 위해, 도구의 개별 엔드포인트를 직접 호출할 수 있습니다. (`_map.py`의 `endpoints`에 정의된 경우)

**예시: `rag_guide_tool` 직접 호출**
```bash
curl -X POST "http://localhost:8000/tools/rag-guide" \
  -H "Content-Type: application/json" \
  -d 
    "git_url": "https://github.com/my-org/my-repo",
    "group_name": "my-group"
  }
```
이 방식은 `python_tool_router_service`가 생성한 API를 통해 해당 도구의 `run` 함수를 즉시 실행합니다.
