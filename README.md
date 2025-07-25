# LangGraph 멀티-에이전트 협업 예제 (LangGraph Multi-Agent Collaboration Example)

이 프로젝트는 LangGraph와 FastAPI를 사용하여 여러 도구(Tool)를 사용하는 지능형 에이전트를 구축하는 방법을 보여주는 예제입니다. 에이전트는 사용자의 요청을 이해하고, 가장 적절한 도구를 선택하여 작업을 수행합니다.

## ✨ 주요 기능 (Features)

- **LLM 기반 라우팅**: 사용자의 입력에 따라 다음에 실행할 도구를 동적으로 결정합니다.
- **다양한 도구 통합**:
    - 간단한 Python 함수 (텍스트 변환)
    - 외부 API 호출
    - 클래스 기반 로직 실행
    - LangChain LCEL Chain 통합
    - 하위 그래프(Sub-graph) 호출
    - Human-in-the-loop (사용자 승인)
- **조합 작업**: 두 개 이상의 도구를 순차적으로 실행하여 복잡한 작업을 처리합니다. (예: API 호출 -> 데이터 분석)
- **FastAPI 기반 API 서버**: 에이전트와 상호작용할 수 있는 비동기 API 엔드포인트를 제공합니다.
- **인터랙티브 클라이언트**: 터미널에서 에이전트와 대화할 수 있는 클라이언트를 제공합니다.

## 📂 프로젝트 구조 (Project Structure)

```
.
├── main.py             # FastAPI 서버 및 LangGraph 그래프 정의
├── client.py           # 서버와 통신하는 터미널 클라이언트
├── llm_client.py       # LLM 클라이언트 초기화
├── schemas.py          # Pydantic 스키마 (데이터 모델)
├── requirements.txt    # 프로젝트 의존성
├── tools/              # 에이전트가 사용하는 도구 모듈
│   ├── basic_tools.py
│   ├── api_tool.py
│   ├── class_tool.py
│   ├── human_tool.py
│   ├── langchain_tool.py
│   ├── subgraph_tool.py
│   └── utils.py
└── README.md
```

## 🚀 시작하기 (Getting Started)

### 1. 사전 준비 (Prerequisites)

- Python 3.9 이상
- OpenAI API 키

### 2. 설치 (Installation)

1.  **프로젝트 클론**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **가상 환경 생성 및 활성화**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate   # Windows
    ```

3.  **의존성 설치**
    ```bash
    pip install -r requirements.txt
    ```

4.  **환경 변수 설정**
    프로젝트 루트 디렉터리에 `.env` 파일을 생성하고 OpenAI API 키를 추가합니다. `llm_client.py`는 이 파일을 사용하여 환경 변수를 로드합니다.

    ```.env
    OPENAI_API_KEY="sk-..."
    OPENAI_MODEL_NAME="gpt-4o"
    ```

### 3. 실행 (Usage)

1.  **API 서버 실행**
    터미널에서 다음 명령어를 실행하여 FastAPI 서버를 시작합니다.

    ```bash
    python main.py
    ```
    서버는 `http://127.0.0.1:8000`에서 실행됩니다.

2.  **클라이언트 실행**
    다른 터미널을 열고 다음 명령어를 실행하여 인터랙티브 챗 클라이언트를 시작합니다.

    ```bash
    python client.py
    ```

### 4. 예제 대화 (Example Conversation)

클라이언트를 실행하고 다음과 같이 질문하여 각 도구의 동작을 테스트할 수 있습니다.

- **Tool 1 (대문자 변환)**
  > **You:** hello world를 대문자로 바꿔줘
  > **Agent:** HELLO WORLD

- **API Call (외부 API 호출)**
  > **You:** 1번 사용자 정보 알려줘
  > **Agent:** 1번 사용자의 정보입니다: {'id': 1, 'name': 'Leanne Graham', 'username': 'Bret', 'email': 'Sincere@april.biz'}

- **Class Call (클래스 기반 분석)**
  > **You:** 이 문장 분석해줘: "LangGraph is a powerful tool."
  > **Agent:** 분석 결과: 원본 텍스트 'LangGraph is a powerful tool.'의 단어 수는 5개, 글자 수는 29개입니다.

- **Combined Tool (API 호출 + 분석)**
  > **You:** 1번 사용자 데이터 분석해줘
  > **Agent:** 분석 결과: 원본 텍스트 '{\'id\': 1, \'name\': \'Leanne Graham\', \'username\': \'Bret\', \'email\': \'Sincere@april.biz\'}'의 단어 수는 13개, 글자 수는 102개입니다.

- **Human Approval (사용자 승인)**
  > **You:** 중요한 작업 승인해줘
  > (서버 로그에 승인 대기 메시지 출력 후 멈춤)

## 📝 API 엔드포인트

### `POST /chat`

에이전트와 대화를 주고받는 메인 엔드포인트입니다.

- **Request Body**
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": "Your message here"
      }
    ]
  }
  ```

- **Response Body**
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": "Your message here"
      },
      {
        "role": "assistant",
        "content": "Agent's response here"
      }
    ]
  }
  ```