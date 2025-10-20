# CoE Backend - AI Agent Server

문서 맵
- 배포/기동: `../docs/DEPLOY.md`
- 마이그레이션 운영: `../docs/OPERATIONS.md`
- Swagger/UI 경로/사용: `../docs/SWAGGER_GUIDE.md`
- cURL 예시 모음: `../docs/curl-checks.md`

## 1. 프로젝트 개요

이 프로젝트는 **중앙 AI 에이전트 백엔드 서버**입니다. FastAPI를 기반으로 구축되었으며, 시스템의 두뇌 역할을 수행합니다.

사용자의 요청을 받아 자연어의 의도를 파악하고, 가장 적합한 **도구(Tool)**를 선택하여 실행합니다. 또한, `CoE_RagPipeline`과 같은 다른 백엔드 서비스와의 통신을 조율하여 최종 응답을 생성하는 중앙 관제탑(Orchestrator)입니다.

## 2. 주요 기능

- **중앙 에이전트 로직**: LangGraph를 활용하여 사용자의 복잡한 요청을 처리하는 핵심 에이전트 로직을 포함합니다.
- **확장 가능한 도구 시스템**: 새로운 기능을 모듈화된 '도구'로 쉽게 추가하고 확장할 수 있는 아키텍처를 제공합니다. 상세한 가이드는 [tools/README.md](./tools/README.md)를 참고하세요.
- **OpenAI 호환 API**: `/v1/chat/completions`, `/v1/embeddings` 등 표준 OpenAI 형식의 API를 제공하여 다양한 클라이언트와의 호환성을 보장합니다.
- **서비스 오케스트레이션**: RAG 파이프라인, 데이터베이스 등 외부 서비스와의 통신을 관리하고 조율합니다.
- **RAG 문서 처리**: Git 레포지토리 분석뿐 아니라 개별 문서·코드 조각을 백엔드 üzerinden 임베딩/검색할 수 있습니다.
- **가이드 에이전트 모드**: `context="guide"` 또는 `tool_input` 플래그로 진입하면 LangGraph 기반 가이드가 요약·계획·추천을 Markdown으로 반환하고, 필요한 경우 실행할 도구를 제안합니다.

## 3. 시작하기

운영/배포/기동 절차는 최상위 문서에서 관리합니다. 아래 문서를 참고하세요.
- 전체 배포: `../docs/DEPLOY.md`
- 로컬/개발/완전 격리 스택: `../docs/DEPLOY.md#완전-격리-배포edge--prod-full--dev-full`

### 3.1. 오프라인 의존성 준비
내부망에서 `pip`/`uv` 설치가 불가능할 경우, 외부망 머신에서 아래 스크립트로 Linux+Python3.11용 휠을 모아 두세요.
```bash
./scripts/download_wheels.sh backend
```
스크립트는 Docker( python:3.11-bullseye )를 사용해 `CoE-Backend/vendor/wheels/` 에 필요한 패키지와 `uv` 휠을 내려받습니다. 이후 휠 디렉터리를 내부망 서버로 복사하고 `./run.sh`를 실행하면 `uv pip install --no-index --find-links=vendor/wheels ...` 경로로 설치가 진행됩니다.

## 4. API 사용 예시

Swagger 경로와 주요 예시는 다음 문서에서 확인하세요.
- Swagger/UI: `../docs/SWAGGER_GUIDE.md`
- cURL 예시 모음: `../docs/curl-checks.md`

### 4.1 RAG 프록시 빠르게 사용하기

| 기능 | 엔드포인트 | 설명 |
| --- | --- | --- |
| Git 분석 시작/조회 | `POST /v1/rag/analyze`, `GET /v1/rag/results/{analysis_id}` | `CoE-RagPipeline`의 Git 분석 엔드포인트를 백엔드가 대리 호출합니다. |
| 분석 결과 목록 | `GET /v1/rag/results` | 저장된 분석들의 ID·상태를 조회할 수 있습니다. |
| 분석 문서 검색 | `POST /v1/rag/search` | Vector DB에 저장된 분석 결과에서 의미 검색을 수행합니다. |
| RDB 스키마 임베딩 | `POST /v1/rag/ingest/rdb-schema` | 파이프라인의 DB 스키마 동기화를 트리거합니다. |
| 임의 문서 임베딩 | `POST /v1/rag/embed-content` | 파일·URL·원본 텍스트를 벡터 DB에 저장합니다. |

> ℹ️  이 엔드포인트들은 모두 내부 RAG 서비스로 요청을 전달합니다. 외부 네트워크에서 파이프라인을 직접 열지 않고도 동일한 기능을 사용할 수 있습니다.

### 4.2 Chat API 멀티모달 요청 포맷

`/v1/chat/completions` 엔드포인트는 OpenAI 호환 메시지 구조를 사용합니다. 각 메시지의 `content`는 문자열 또는 멀티파트 배열을 허용하며, 텍스트·이미지·일반 파일(Base64) 조각을 혼합할 수 있습니다.

```jsonc
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "이 파일을 요약해줘"},
        {
          "type": "file_base64",          // 또는 "input_file"
          "file_base64": "<base64-encoded payload>",
          "mime_type": "application/pdf", // 선택
          "filename": "spec.pdf"          // 선택
        }
      ]
    }
  ]
}
```

- 이미지의 경우 `type`을 `image_base64`(또는 `input_image`)로 지정하고 `mime_type`을 함께 전달하면 됩니다.
- 프론트엔드가 확장자나 MIME 타입을 모를 때는 `type: "file_base64"` 만 설정해도 수신 및 처리가 가능합니다.
- 로그/PII 필터는 텍스트 조각만 사용하며, 첨부 파일은 `[attachment xN]` 형태로 요약됩니다.

## 5. 프로젝트 구조

```
CoE-Backend/
├── api/              # API 라우터 (채팅, 임베딩, 도구 등)
├── core/             # FastAPI 앱 팩토리, 서버 로직, 에이전트 노드 등 핵심 로직
├── services/         # 도구 디스패처, DB 서비스 등 비즈니스 로직
├── tools/            # 개별 도구 정의 (`_tool.py`, `_map.py`)
├── main.py           # 애플리케이션 진입점
└── Dockerfile        # Docker 설정
```

## 6. API 문서

서버 실행 후 다음 URL에서 상세한 API 문서를 확인할 수 있습니다:

- **Swagger UI**: [http://localhost/docs](http://localhost/docs)
- **ReDoc**: [http://localhost/redoc](http://localhost/redoc)

## 7. 운영 시 DB 마이그레이션

정책과 실행 방법은 `../docs/OPERATIONS.md`를 참고하세요.

## 8. Guide Agent 사용법

가이드 에이전트는 복잡한 개발 작업 가이드를 제공하기 위해 LangGraph 그래프와 RAG 검색을 조합합니다. 요청 문맥과 사용자 환경을 정리한 뒤 Markdown으로 요약/계획/추천/인사이트를 전달합니다.

### 8.1 실행 조건

- `context="guide"` 로 `/v1/chat/completions` 요청을 보내면 자동으로 가이드 모드가 활성화됩니다.
- 일반 컨텍스트에서도 `tool_input.guide_mode`, `tool_input.guide_agent`, `tool_input.run_guide` 중 하나를 truthy 값(`true`, `"yes"`, `1` 등)으로 설정하면 가이드를 실행합니다.

### 8.2 요청 필드

- `tool_input.paths`: 문자열 리스트 또는 콤마 구분 문자열로 다루고 싶은 파일/디렉터리 경로를 최대 10개까지 전달할 수 있습니다.
- `tool_input.profile`: 명시하지 않으면 그룹명(`group_name`)을, 둘 다 없으면 `default` 프로필을 사용합니다.
- `tool_input.language` 또는 `tool_input.locale`: 응답 언어 힌트로 활용됩니다(기본값 `ko`).
- 서버는 메타데이터에 현재 컨텍스트, 그룹, 요청 헤더를 포함해 LangGraph에 전달합니다.

### 8.3 응답과 도구 실행 흐름

- 본문에는 `요약`, `계획 체크리스트`, `추천 사항`, `참고 인사이트` 섹션이 Markdown 형태로 포함됩니다.
- 추가로 자동 도구 추천이 가능하면 메시지 하단에 `권장 도구 실행 안내`가 붙습니다.
  - 실행하려면 동일 세션에서 `tool_input.guide_confirm=true` 와 함께 다시 요청하세요.
  - 도구 인자가 필요할 경우 `tool_input.guide_tool_args={...}` 로 JSON 인자를 추가하면 세션에 보관된 추천이 덮어씁니다.
  - 실행하지 않으려면 `tool_input.guide_cancel=true` 로 세션의 대기 중인 추천을 해제할 수 있습니다.

### 8.4 연관 문서 및 환경 변수

- 상세 동작, 상태 모델, 테스트 전략은 `guide_agent_docs/README.md` 에 정리되어 있습니다.
- `GUIDE_AGENT_RAG_URL` 환경 변수를 설정하면 외부 RAG 파이프라인 엔드포인트를 커스터마이징할 수 있으며, 기본값은 `http://coe-ragpipeline-dev:8001` 입니다.
