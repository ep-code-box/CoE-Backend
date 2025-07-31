## 💎 해야할 일
도커 배포 기반의 backend.
모델을 추가 등록 및 선택가능해야 한다. 모델은 크게 sllm과 embedding 모델이 있다.
langFlow 및 python Script 그리고 api 호출등 다양한 업무를 지원하며 langGraph를 기반으로 한다.
어떤 사람이든 기본 샘플을 보고 업무를 추가 할 수 있도록 한다.

## 📋 프로젝트 현황 (2025-07-31 업데이트)

### Todo
#### CoE Backend
- [ ] embedding 모델 연동 api 구현
- [ ] vector db 쿼링 및 결과 다듬기
- [ ] embedding 모델을 models.json에 추가 및 관리 시스템 구현
- [ ] RAG 기능을 위한 문서 임베딩 및 검색 API 구현

#### CoE RagPipeline
- [ ] Git 소스 분석 파이프라인 구현
- [ ] 정적 분석 결과 JSON 저장 기능
- [ ] 문서 자동 수집 및 분석 (doc 폴더, refUrl)
- [ ] 개발표준문서 자동 생성 기능
- [ ] RAG 시스템 구축 및 벡터 DB 연동
- [ ] 프로젝트 기본 구조 및 README 작성

### In Progress
#### CoE Backend
- [ ] 현재 진행 중인 작업 없음

### Done
#### CoE Backend
- [X] LangGraph Backend 샘플 구현 완료
- [X] Docker 배포 스크립트 작성 완료
- [X] 샘플 품질 고도화 완료 (상세한 README, 다양한 도구 예시)
- [X] langFlow 기본 적용 완료 (langflow_tool.py 구현)
- [X] 모듈형 도구 레지스트리 패턴 구현
- [X] FastAPI 기반 API 서버 구현
- [X] 인터랙티브 클라이언트 구현
- [X] 다양한 도구 통합 (API 호출, 클래스 기반, LangChain, Human-in-the-Loop)