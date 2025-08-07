# 🤖 CoE-Backend: AI 에이전트 및 API 서버

**CoE for AI** 플랫폼의 핵심 백엔드 서버입니다. **LangGraph**와 **FastAPI**를 기반으로 구축된 확장 가능한 AI 에이전트 시스템으로, 다양한 AI 워크플로우를 지원합니다.

## 🎯 핵심 가치

- **🔧 확장성**: 도구 레지스트리 패턴으로 새로운 기능을 쉽게 추가
- **🔗 호환성**: OpenWebUI, LangFlow와 완벽 호환
- **🚀 성능**: 비동기 FastAPI 기반 고성능 API 서버
- **🛡️ 안정성**: 완전한 모듈화와 체계적인 에러 처리

## ✨ 주요 기능

- **🤖 AI 에이전트 시스템**: 동적 도구 라우팅, 자동 도구 등록, 멀티턴 대화
- **🔗 플랫폼 호환성**: OpenWebUI, LangFlow 연동 및 다중 LLM 지원
- **🔍 검색 및 임베딩**: ChromaDB 기반 벡터 검색 및 한국어 특화 모델 지원 (RAG)
- **👨‍💻 코딩 어시스턴트**: 10개 이상 주요 언어의 코드 분석, 생성, 리뷰 지원

## 🔧 아키텍처: 도구 레지스트리 패턴

이 프로젝트는 `main.py` 수정 없이 새로운 기능을 동적으로 추가할 수 있는 **도구 레지스트리(Tool Registry)** 패턴을 사용합니다. `tools/registry.py`가 `tools` 디렉터리 내의 도구들을 자동으로 스캔하고, `main.py`는 이를 조립하여 LangGraph를 구성합니다.

## 📂 프로젝트 구조

```
CoE-Backend/
├── main.py                 # FastAPI 앱 및 메인 LangGraph 조립기
├── Dockerfile              # Docker 이미지 빌드 파일
├── .env.sample             # 환경 변수 예시 파일
├── requirements.txt        # 프로젝트 의존성
├── README.md               # 프로젝트 문서
├── run.sh                  # 실행 스크립트
├── api/                    # API 엔드포인트 모듈
│   ├── chat_api.py
│   ├── embeddings_api.py
│   ├── flows_api.py
│   ├── health_api.py
│   ├── models_api.py
│   ├── coding_assistant/
│   │   └── code_api.py
│   ├── tools/
│   │   └── dynamic_tools_api.py
│   └── vector/
│       └── vector_api.py
├── config/                 # 설정 파일
│   └── models.json
├── core/                   # 핵심 비즈니스 로직
│   └── ...
├── docs/                   # 문서 폴더
├── flows/                  # LangFlow 워크플로우 저장소
├── routers/                # 라우터 모듈
├── services/               # 비즈니스 서비스 레이어
│   └── ...
├── tools/                  # 에이전트 도구 모듈
│   ├── README.md
│   ├── registry.py
│   └── ...
└── utils/                  # 유틸리티 함수
    └── ...
```

## 🚀 빠른 시작

### 📋 사전 요구사항
- Python 3.8+ 또는 Docker
- LLM API 키 (SKAX, OpenAI 등)

### 🔧 환경 변수 설정
1.  `.env.sample` 파일을 복사하여 `.env` 파일을 생성합니다.
    ```bash
    cp .env.sample .env
    ```
2.  `.env` 파일을 열어 `SKAX_API_KEY`, `OPENAI_API_KEY` 등 필요한 API 키를 설정합니다.
    - 로컬 개발 시에는 `.env.local` 파일을 사용하면 `run.sh` 스크립트가 자동으로 로드합니다.
    - Docker와 로컬 환경의 데이터베이스, ChromaDB 등의 접속 정보는 `.env.sample`에 자세히 안내되어 있습니다.

### 🐳 Docker로 실행 (권장)
```bash
# 1. Docker 이미지 빌드
docker build -t coe-backend .

# 2. 컨테이너 실행
docker run -d -p 8000:8000 --name coe-backend --env-file .env coe-backend

# 3. 서비스 확인
curl http://localhost:8000/health
```

### 🐍 로컬 개발 환경
`run.sh` 스크립트를 사용하면 가상 환경 설정, 의존성 설치, 서버 실행을 한 번에 처리할 수 있습니다.
```bash
# 스크립트 실행 권한 부여
chmod +x run.sh

# 서버 실행
./run.sh
```

## 🔌 플랫폼 연동

### 🌐 OpenWebUI 연동
1.  OpenWebUI **설정** → **연결** 메뉴로 이동
2.  **API Base URL**: `http://localhost:8000/v1` 입력 (Docker 환경에서는 `http://coe-backend:8000/v1`)
3.  **API Key**: 비워두고 저장
4.  모델 선택에서 **CoE Agent v1** 선택

### 🔄 LangFlow 연동
`/flows/save`, `/flows/list` 등의 API를 통해 LangFlow 워크플로우를 저장하고 관리할 수 있습니다.

## 💬 API 사용 예시

`curl`을 사용하여 다양한 엔드포인트를 테스트할 수 있습니다.

- **AI 에이전트 채팅**: `POST /v1/chat/completions`
- **코딩 어시스턴트**: `POST /api/coding-assistant/analyze`
- **벡터 검색**: `POST /vector/search`
- **시스템 상태**: `GET /health`

자세한 내용은 [API 레퍼런스](#-api-레퍼런스) 섹션을 참조하세요.

## 🛠️ 개발자 가이드: 새로운 도구 추가하기

`main.py`를 수정하지 않고 `tools` 디렉터리에 파일을 추가하는 것만으로 새로운 기능을 확장할 수 있습니다.

**1단계: 도구 파일 생성**
```python
# tools/my_custom_tool.py
from typing import Dict, Any
from core.schemas import ChatState

# 도구 설명 (변수명은 _description으로 끝나야 함)
my_custom_tool_description = {
    "name": "my_custom_tool",
    "description": "사용자 정의 도구입니다."
}

# 노드 함수 (함수명은 _node로 끝나야 함)
def my_custom_tool_node(state: ChatState) -> Dict[str, Any]:
    # 도구 로직 구현
    result = "도구 실행 결과"
    return {"messages": [{"role": "assistant", "content": result}]}
```

**2단계: 서버 재시작**
개발 서버는 변경사항을 감지하고 자동으로 재시작됩니다.

## 📚 API 레퍼런스

### 🤖 AI 에이전트 & 채팅
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/v1/chat/completions` | POST | OpenAI 호환 채팅 API (핵심) |
| `/v1/models` | GET | 사용 가능한 모델 목록 |

### 🔍 벡터 검색 & 임베딩
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/v1/embeddings` | POST | OpenAI 호환 임베딩 API |
| `/vector/search` | POST | 벡터 유사도 검색 |
| `/vector/add` | POST | 문서 추가 및 임베딩 |
| `/vector/info` | GET | 벡터 DB 상태 정보 |

### 👨‍💻 코딩 어시스턴트
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/coding-assistant/languages` | GET | 지원 언어 목록 |
| `/api/coding-assistant/analyze` | POST | 코드 분석 & 메트릭 |
| `/api/coding-assistant/generate` | POST | AI 코드 생성 |

### 🔄 워크플로우 관리
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/flows/save` | POST | LangFlow 워크플로우 저장 |
| `/flows/list` | GET | 저장된 워크플로우 목록 |

### 🏥 시스템 상태
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 상태 확인 |

## 🔧 문제 해결
- **API 키 오류**: `.env` 파일에 API 키가 올바르게 설정되었는지 확인하세요.
- **포트 충돌**: `lsof -i :8000` (macOS/Linux) 명령어로 8000번 포트를 사용하는 프로세스가 있는지 확인하세요.
