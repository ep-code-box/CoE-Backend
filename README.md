# 🤖 모듈형 LangGraph 에이전트 프레임워크

이 프로젝트는 **LangGraph**와 **FastAPI**를 기반으로 구축된, 확장성이 매우 뛰어난 모듈형 AI 에이전트 프레임워크입니다. **도구 레지스트리(Tool Registry)** 패턴을 도입하여, 새로운 기능을 추가할 때 메인 애플리케이션 코드를 전혀 수정할 필요가 없는 구조를 갖추고 있습니다.

## ✨ 주요 기능 (Features)

- **동적 도구 라우팅**: LLM을 사용하여 사용자의 요청에 가장 적합한 도구를 동적으로 선택합니다.
- **완벽한 모듈화 및 확장성**: 각 도구의 기능, 설명, 그래프 연결(흐름) 로직이 개별 파일로 분리되어 독립적으로 관리됩니다.
- **자동 도구 등록 (Tool Registry)**: `tools` 디렉터리에 새로운 도구 파일을 추가하는 것만으로 에이전트에 자동으로 통합됩니다.
- **다양한 도구 통합 예시**:
    - 간단한 Python 함수 (텍스트 변환)
    - 외부 REST API 호출
    - 클래스 기반 로직 실행
    - LangChain Expression Language(LCEL) 체인 통합 (텍스트 요약 및 감성 분석)
    - 하위 그래프(Sub-graph) 호출
    - 2단계 사용자 승인/거절 (Human-in-the-Loop)
- **복합 작업 흐름 (Conditional Edges)**: 두 개 이상의 도구를 조건에 따라 순차적으로 실행하여 복잡한 작업을 처리합니다. (예: API 호출 -> 데이터 분석)
- **FastAPI 기반 API 서버**: 에이전트와 상호작용할 수 있는 비동기 API 엔드포인트를 제공합니다.
- **인터랙티브 클라이언트**: 터미널에서 에이전트와 실시간으로 대화할 수 있는 클라이언트를 제공합니다.

## 🔧 아키텍처: 도구 레지스트리 패턴

이 프로젝트의 핵심은 **도구 레지스트리(Tool Registry)** 패턴을 사용하여 `main.py`의 수정 없이 새로운 기능을 쉽게 추가할 수 있다는 점입니다.

1.  **동적 로딩**: `tools/registry.py`의 `load_all_tools()` 함수는 `tools` 디렉터리 내의 모든 파이썬 파일을 스캔합니다.
2.  **규칙 기반 등록**: 각 파일에서 다음 규칙에 맞는 변수와 함수를 찾아 동적으로 로드합니다.
    - **노드 함수**: 이름이 `_node`로 끝나는 함수 (예: `api_call_node`)
    - **도구 설명**: 이름이 `_description` 또는 `_descriptions`로 끝나는 변수
    - **그래프 엣지**: 이름이 `_edges`로 끝나는 변수 (특별한 흐름이 필요할 경우)
3.  **그래프 자동 구성**: `main.py`는 레지스트리가 수집한 노드, 설명, 엣지 정보를 사용하여 LangGraph를 동적으로 구성합니다.

이 구조 덕분에 `main.py`는 어떤 도구가 존재하는지 알 필요가 없으며, 오직 "조립기"의 역할만 수행합니다.

## 📂 프로젝트 구조

```
CoE/
├── main.py             # FastAPI 앱 및 메인 LangGraph 조립기
├── client.py           # 서버와 통신하는 터미널 클라이언트
├── llm_client.py       # LLM 클라이언트 초기화
├── schemas.py          # Pydantic 스키마 (데이터 모델)
├── .env                # 환경 변수 파일 (API 키 등)
├── requirements.txt    # 프로젝트 의존성
├── tools/              # 에이전트가 사용하는 도구 모듈
│   ├── __init__.py
│   ├── registry.py     # 도구를 동적으로 로드하는 레지스트리
│   ├── utils.py        # 도구 모듈에서 사용하는 유틸리티 함수
│   ├── api_tool.py
│   ├── basic_tools.py
│   ├── class_tool.py
│   ├── human_tool.py
│   ├── langchain_tool.py
│   └── subgraph_tool.py
└── README.md
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# 1. 저장소 복제
git clone <repository-url>
cd CoE

# 2. 가상 환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. .env 파일 생성 및 API 키 설정
echo "OPENAI_API_KEY='your-openai-api-key'" > .env
```

### 2. 서버 및 클라이언트 실행

두 개의 터미널을 열고 각각 다음 명령어를 실행합니다.

**터미널 1: FastAPI 서버 실행**
```bash
python main.py
```

**터미널 2: 인터랙티브 클라이언트 실행**
```bash
python client.py
```

## 💬 사용 예시

- **기본 도구 (대문자 변환)**
  > **You:** hello world를 대문자로 바꿔줘
  > **Agent:** HELLO WORLD

- **API 호출**
  > **You:** 1번 사용자 정보 알려줘
  > **Agent:** API 결과: sunt aut facere repellat provident occaecati excepturi optio reprehenderit

- **복합 작업 (API 호출 + 분석)**
  > **You:** 1번 사용자 데이터 분석해줘
  > **Agent:** 텍스트 분석 결과: 길이=294, 단어 수=52

- **LangChain 체인 (요약 + 감성 분석)**
  > **You:** 이 영화 정말 최고였어! 스토리도 감동적이고 영상미도 뛰어났어.
  > **Agent:** 텍스트 분석 결과입니다:
  > - 요약: 이 영화는 스토리와 영상미가 뛰어나 매우 훌륭했다는 평가입니다.
  > - 감성: Positive

- **Human-in-the-Loop (사용자 승인)**
  > **You:** 중요한 작업 승인해줘
  > **Agent:** '중요한 작업 승인해줘' 작업에 대한 관리자 승인이 필요합니다. 계속 진행하려면 'approve', 취소하려면 'reject'를 입력해주세요.
  > **You:** approve
  > **Agent:** 승인되었습니다. 요청된 작업을 계속 진행합니다.

## 🛠️ 새로운 도구 추가하기

이 아키텍처의 가장 큰 장점은 새로운 도구를 매우 쉽게 추가할 수 있다는 것입니다.

1.  `tools` 디렉터리에 `my_new_tool.py`와 같은 새 파이썬 파일을 만듭니다.
2.  파일 안에 아래와 같이 **도구 설명**과 **노드 함수**를 규칙에 맞게 정의합니다.

**예시: `tools/my_new_tool.py`**
```python
from typing import Dict, Any
from schemas import ChatState

# 1. 라우터가 사용할 도구 설명 (변수명은 _description 또는 _descriptions로 끝나야 함)
my_new_tool_description = {
    "name": "my_tool",
    "description": "이것은 새로 추가된 멋진 도구입니다."
}

# 2. 실제 작업을 수행할 노드 함수 (함수명은 _node로 끝나야 함)
def my_tool_node(state: ChatState) -> Dict[str, Any]:
    # ... 실제 도구 로직 구현 ...
    return {"messages": [{"role": "assistant", "content": "새로운 도구 실행 완료!"}]}
```

3.  **끝입니다!** `main.py`를 수정할 필요 없이 서버를 재시작하면 에이전트가 `my_tool`을 자동으로 인식하고 라우팅에 사용합니다.

### 복잡한 흐름 추가하기

만약 도구가 실행된 후 특정 다른 노드로 연결되어야 한다면, `_edges` 변수를 정의하여 그래프 흐름을 지정할 수 있습니다. 자세한 내용은 `tools/api_tool.py`나 `tools/human_tool.py`를 참고하세요.

## 📝 API 엔드포인트

- **`POST /chat`**: 채팅 메시지를 받아 에이전트를 실행하고 응답을 반환합니다.
- **`GET /v1/models`**: LangChain 호환성을 위한 모델 목록을 반환합니다.



## 💎 해야할 일

### Todo

- [ ] CoE Backend
  - [ ] Embedding 모델 통한 쿼리 벡터
  - [ ] 벡터db 활용
  - [ ] Docker 배포 스크립트
- [ ] RAG 생성 파이프 라인
  - [ ] 정적 분석도구 리서치
  - [ ] 프로세스 파이프라인 정리
- [ ] vsCode Extention
  - [ ] copilot open source 분석
- [ ] CoE Portal
  - [ ] webIDE 리서치

### ing
- [ ] CoE Backend
  - [X] 샘플 품질 고도화

### Done

- [X] LangGraph Backend 샘플