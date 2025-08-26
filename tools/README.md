# 도구 개발자 가이드 (v3)

이 문서는 CoE-Backend 시스템에 새로운 도구를 생성하고 통합하는 방법을 설명합니다. 새로운 아키텍처는 **의도 분석 기반의 중앙 집중형 디스패처**를 기반으로 하며, 모든 도구 관련 결정과 실행은 `services/tool_dispatcher.py`가 전담합니다.

## 핵심 개념: 의도 분석 기반 디스패처

- **중심 두뇌 (The Brain)**: `services/tool_dispatcher.py`가 에이전트의 핵심 두뇌 역할을 합니다. 이 디스패처는 단순한 실행기가 아니라, 사용자 문의의 **의도를 분석**하여 가장 적합한 도구를 **스스로 결정**하고 실행까지 책임집니다.
- **`context` 기반 도구 제공**: 특정 `context`(프론트엔드 환경)에서 사용 가능한 도구들의 목록을 LLM에게 제공하여, LLM이 이 중에서 최적의 도구를 선택하도록 합니다.
- **두 가지 도구 유형 및 실행 방식**:
  1.  **Python 도구**: 명확한 기능이 있는 정적(static) 도구입니다. LLM은 여러 Python 도구 중 가장 적합한 것의 **이름**을 선택하여 실행을 요청합니다.
  2.  **LangFlow 워크플로우**: 복잡한 작업을 처리하는 동적(dynamic) 워크플로우입니다. LLM은 특정 Flow의 이름을 선택하는 대신, **"LangFlow를 실행해야 한다"** 는 결정만 내립니다. 그러면 디스패처가 사용자의 질문과 가장 관련성이 높은 Flow를 **의미 기반 검색**으로 찾아 실행합니다.

---

## 새로운 Python 도구 만드는 방법

### 1단계: 도구 파일 생성 (`xxx_tool.py`)

`/tools` 디렉토리 또는 그 하위 디렉토리에 `_tool.py`로 끝나는 새 Python 파일을 만듭니다.

이 파일은 다음 두 가지 핵심 요소를 포함해야 합니다.

1.  **`run(tool_input, state)` 함수 (필수)**: 도구의 실제 로직을 포함하는 진입점 함수입니다. 디스패처는 이 `run` 함수를 찾아 실행합니다.
2.  **`available_tools` 변수 (필수)**: LLM이 이 도구를 이해하고 스스로 호출할 수 있도록, 도구의 명세(스키마)를 정의한 리스트입니다. (OpenAI Function Calling 형식)

**예시: `my_greeting_tool.py`**
```python
from typing import Dict, Any, List, Optional
from core.schemas import AgentState

# 1. 'run' 함수 (필수): 도구의 실제 로직
#    이 함수는 반드시 'run'이라는 이름으로 정의되어야 합니다.
async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> str:
    """도구의 진입점 함수입니다."""
    # tool_input은 LLM이 생성한 arguments를 포함할 수 있습니다.
    # 이 예제에서는 LLM이 'name' 인자를 생성했다고 가정합니다.
    user_name = tool_input.get('name', "Guest")
    return f"Hello, {user_name}! This is my new tool."

# 2. 'available_tools' 변수 (필수): 도구의 명세 (Schema)
#    LLM이 이 명세를 보고 도구의 이름, 설명, 필요한 인자 등을 파악합니다.
my_greeting_tool_schema = {
    "type": "function",
    "function": {
        "name": "greet_user_in_a_new_way", # LLM이 사용할 도구의 이름
        "description": "사용자에게 새로운 방식으로 인사합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "인사할 사람의 이름"}
            },
            "required": ["name"]
        }
    }
}

available_tools: List[Dict[str, Any]] = [my_greeting_tool_schema]
```

### 2단계: 매핑 파일 생성 (`xxx_map.py`)

`_tool.py` 파일과 같은 위치에 `_map.py` 파일을 생성합니다. 이 파일은 도구가 어떤 `context`에서 사용될 수 있는지를 정의합니다.

- **`tool_contexts` (필수)**: 도구가 활성화될 프론트엔드 환경 목록을 리스트로 정의합니다.

**예시: `my_new_map.py`**
```python
# 이 도구가 사용될 수 있는 컨텍스트를 정의합니다.
tool_contexts = [
    "aider",
    "openWebUi"
]
```

---

## 새로운 LangFlow 워크플로우 등록 방법

LangFlow는 더 이상 `tool_name`으로 직접 매핑되지 않습니다. 대신, `description`(설명)을 통해 의미적으로 검색됩니다.

### 1단계: LangFlow UI에서 Flow 생성

LangFlow UI를 사용하여 원하는 워크플로우를 생성합니다.

### 2단계: Flow 등록 (의미 검색을 위한 정보 제공)

`POST /v1/flows` API를 호출하여 생성된 Flow를 시스템에 등록합니다. 이때, **`description`과 `context` 필드가 매우 중요합니다.**

- **`description`**: 이 Flow가 어떤 작업을 수행하는지 LLM이 잘 이해할 수 있도록, 명확하고 상세하게 작성해야 합니다. 이 설명은 **의미 기반 검색의 핵심**이 됩니다.
- **`context`**: 이 Flow가 어떤 환경에서 사용될 수 있는지 지정합니다.

**요청 예시:**
```bash
cURL -X POST "http://localhost:8000/v1/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "generate-code-from-spec",
    "description": "사용자의 요구사항 명세서를 입력받아, 그에 맞는 Python 코드를 자동으로 생성하고 파일로 저장하는 복잡한 워크플로우입니다.",
    "flow_id": "flow-abc-123",
    "flow_body": { ... },
    "context": "aider"
  }'
```

요청이 성공하면, `langflows` 데이터베이스 테이블에 해당 정보가 저장되며, 이제부터 `tool_dispatcher`가 의도 분석을 통해 이 Flow를 동적으로 찾아 실행할 수 있게 됩니다.

---

## 도구 실행 예시 (cURL)

도구를 실행하는 방법은 크게 두 가지가 있습니다.

### 1. 에이전트를 통한 실행 (의도 분석)

중앙 에이전트(`/v1/chat/completions`)에 자연어 질문을 보내, 에이전트가 스스로 의도를 파악하고 최적의 도구를 선택하여 실행하게 하는 방식입니다. 이 방식이 기본적이고 권장되는 방법입니다.

**예시: `rag_guide_tool` 실행 요청**
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ax4",
    "messages": [
      {
        "role": "user",
        "content": "정리해줘. 1. 기간  : 8/25~8/28.  2. 대상 : 7~8월 갤럭시S25 or 폴더블7 구매 고객 중 '8월 특가폰 \> 번들 이벤트' 카테고리에서 워치 구매 고객 (오늘애특가에서 S25 or 폴더블7 구매한 고객은 행사 제외).  3. 혜택 : 갤럭시워치7/8 구매 혜택UP.  4. 워치 구매조건 [ LTE Watch 요금제 / 공통지원 할인 / 당월 개통 기준]"
      }
    ],
    "context": "aider"
  }'
```

위 요청을 받으면, `tool_dispatcher`는 `aider` 컨텍스트에서 사용 가능한 도구 목록과 사용자 질문을 LLM에 보내 의도를 분석합니다. LLM은 `rag_guide_tool`이 가장 적합하다고 판단하고, 해당 도구 실행을 요청하게 됩니다.

### 2. 개별 API를 통한 직접 실행

테스트나 특정 연동 시나리오를 위해, 에이전트의 판단을 거치지 않고 도구의 개별 엔드포인트를 직접 호출할 수 있습니다. 엔드포인트 경로는 각 도구의 `_map.py` 파일에 있는 `endpoints` 딕셔너리에 정의되어 있습니다.

**예시: `rag_guide_tool` 직접 호출**
```bash
curl -X POST "http://localhost:8000/tools/rag-guide" \
  -H "Content-Type: application/json" \
  -d '{
    "git_url": "https://github.com/my-org/my-repo"
  }'
```

이 방식은 `tool_dispatcher`를 거치지 않고, `python_tool_router_service`가 생성한 API를 통해 해당 도구의 `run` 함수를 즉시 실행합니다.
