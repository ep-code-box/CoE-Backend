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

## 3. 시작하기

운영/배포/기동 절차는 최상위 문서에서 관리합니다. 아래 문서를 참고하세요.
- 전체 배포: `../docs/DEPLOY.md`
- 로컬/개발/완전 격리 스택: `../docs/DEPLOY.md#완전-격리-배포edge--prod-full--dev-full`

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
