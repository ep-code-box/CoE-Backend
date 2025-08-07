# 🤖 CoE-Backend: AI 에이전트 및 API 서버

**CoE for AI** 플랫폼의 핵심 백엔드 서버입니다. **LangGraph**와 **FastAPI**를 기반으로 구축된 확장 가능한 AI 에이전트 시스템으로, 다양한 AI 워크플로우를 지원합니다.

## ✨ 주요 기능

- **🔧 확장성**: 도구 레지스트리 패턴으로 새로운 기능을 쉽게 추가할 수 있습니다.
- **🔗 호환성**: OpenWebUI, LangFlow와 완벽하게 호환됩니다.
- **🚀 성능**: 비동기 FastAPI 기반의 고성능 API 서버입니다.
- **🛡️ 안정성**: 완전한 모듈화와 체계적인 에러 핸들링을 갖추고 있습니다.

## 🚀 시작하기

### 📋 사전 요구사항
- Python, Docker
- LLM API 키 (예: SKAX, OpenAI)

### 🔧 환경 설정
1.  `.env.sample` 파일을 복사하여 `.env` 파일을 생성합니다.
    ```bash
    cp .env.sample .env
    ```
2.  `.env` 파일을 열어 `SKAX_API_KEY`, `OPENAI_API_KEY` 등 필요한 API 키를 설정합니다.

### 🏃‍♂️ 서버 실행
`run.sh` 스크립트를 사용하면 가상 환경 설정, 의존성 설치, 서버 실행을 한 번에 처리할 수 있습니다.
```bash
# 실행 권한 부여
chmod +x run.sh

# 서버 실행
./run.sh
```

## 🔌 플랫폼 연동

### 🌐 OpenWebUI 연동
1.  OpenWebUI **설정** → **연결** 메뉴로 이동합니다.
2.  **API Base URL**: `http://localhost:8000/v1` (Docker 환경에서는 `http://coe-backend:8000/v1`)을 입력합니다.
3.  **API Key**: 비워두고 저장합니다.
4.  모델 목록에서 **CoE Agent v1**을 선택합니다.

### 🔄 LangFlow 연동
`/flows/save`, `/flows/list` API를 통해 LangFlow 워크플로우를 저장하고 관리할 수 있습니다.

## 📂 프로젝트 구조

```
CoE-Backend/
├── main.py                 # FastAPI 앱 및 메인 LangGraph 조립기
├── run.sh                  # 실행 스크립트
├── Dockerfile              # Docker 이미지 빌드 파일
├── .env.sample             # 환경 변수 예시 파일
├── requirements.txt        # 프로젝트 의존성
├── README.md               # 프로젝트 문서
├── api/                    # API 엔드포인트 모듈
├── config/                 # 설정 파일
├── core/                   # 핵심 비즈니스 로직
├── services/               # 비즈니스 서비스 레이어
└── tools/                  # 에이전트 도구 모듈
```
