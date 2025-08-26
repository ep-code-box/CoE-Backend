# 🤖 CoE Backend API

## CoE for AI - Backend API Server

이 API는 **LangGraph 기반 지능형 AI 에이전트**와 **다양한 개발 도구**를 제공하는 백엔드 서버입니다. OpenAI API와 호환되는 형식을 지원하여 기존 생태계와 쉽게 연동할 수 있습니다.

---

### 🚀 주요 기능 (Key Features)

- **지능형 AI 에이전트 채팅**: 모든 채팅 요청에 대해 사용자의 의도를 분석하고, 등록된 도구를 자율적으로 사용하는 지능형 에이전트 기능을 제공합니다. (`/v1/chat/completions`)
- **코딩 어시스턴트**: 코드 생성, 분석, 리팩토링, 리뷰 (`/api/coding-assistant/`)
- **LangFlow 연동**: 워크플로우 관리 (`/flows/`)
- **동적 도구**: `tools` 디렉토리에 정의된 Python 도구를 자동으로 등록하고 API로 노출합니다.

---

### 📚 사용 가이드 (How to Use)

모든 채팅 요청은 지능형 에이전트를 통해 처리됩니다. 에이전트는 사용자의 질문을 분석하여, 요청에 지정된 `context`에 맞는 최적의 도구를 스스로 찾아 사용합니다.

#### 1. 에이전트에게 작업 요청하기

API를 호출할 때, `model`과 `context`를 지정해야 합니다.

-   `model`: 에이전트가 **생각을 위해 사용할 LLM**을 지정합니다. (예: `gpt-4`, `claude-3`) 이 모델이 도구를 선택하고, 최종 답변을 생성하는 역할을 합니다.
-   `context`: 에이전트가 사용할 **도구 세트**를 지정합니다. (예: `"aider"`, `"openWebUi"`, `"coding"`)

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d \
'{ "model": "gpt-4-turbo", "messages": [ { "role": "user", "content": "https://github.com/my-org/my-repo 레포지토리를 분석해줘." } ], "context": "aider" }'
```

#### 2. 대화 이어가기

첫 응답에 포함된 `session_id`를 다음 요청부터 본문에 넣어 보내면, AI가 이전 대화 내용을 기억하고 맥락에 맞는 답변을 합니다.

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d \
'{ "model": "gpt-4-turbo", "messages": [{"role": "user", "content": "방금 분석한 레포지토리의 주요 기술 스택은 뭐야?"}], "context": "aider", "session_id": "여기에-이전-응답의-세션-ID를-입력하세요" }'
```

---

### 🔗 연동 서비스

-   **OpenWebUI**: `http://localhost:8000/v1` 설정으로 연동 가능
-   **CoE-RagPipeline**: `http://localhost:8001` (Git 소스코드 및 RDB 스키마 분석 서비스)