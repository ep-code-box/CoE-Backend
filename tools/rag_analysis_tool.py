import requests
from typing import Dict, Any, Optional
from core.schemas import ChatState
import os
import json
import logging

logger = logging.getLogger(__name__)

# RAG Pipeline의 기본 URL (환경 변수 또는 설정 파일에서 가져오는 것이 좋음)
RAG_PIPELINE_BASE_URL = os.getenv("RAG_PIPELINE_BASE_URL", "http://localhost:8001")

# 라우터 프롬프트에 사용될 도구 설명
rag_analysis_tool_description = {
    "name": "rag_analysis",
    "description": "Git 레포지토리를 분석하여 RAG 파이프라인에 데이터를 추가합니다. group_name을 지정하여 업무별로 데이터를 관리할 수 있습니다. (예: 'payment 팀의 github.com/example/repo 분석해줘')",
    "url_path": "/tools/rag-analysis",
    "parameters": { # 도구의 입력 파라미터 정의 (LLM이 이해하도록 돕기 위함)
        "type": "object",
        "properties": {
            "repositories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Git 레포지토리 URL"},
                        "branch": {"type": "string", "description": "분석할 브랜치 (기본값: main)", "default": "main"}
                    },
                    "required": ["url"]
                },
                "description": "분석할 Git 레포지토리 목록"
            },
            "group_name": {
                "type": "string",
                "description": "분석 결과를 묶을 그룹명 (예: PaymentTeam, FrontendTeam)",
                "nullable": True
            }
        },
        "required": ["repositories"]
    }
}

def rag_analysis_node(state: ChatState) -> Dict[str, Any]:
    """
    RAG 파이프라인의 /api/v1/analyze 엔드포인트를 호출하여 Git 레포지토리를 분석합니다.
    """
    input_data = state.get("input_data", {})
    repositories = input_data.get("repositories")
    group_name = input_data.get("group_name")

    if not repositories:
        return {"messages": [{"role": "system", "content": "RAG 분석 오류: 분석할 레포지토리 정보가 필요합니다."}]}

    # RAG Pipeline의 /analyze 엔드포인트 호출을 위한 데이터 구성
    payload = {
        "repositories": repositories,
        "include_ast": True,
        "include_tech_spec": True,
        "include_correlation": True,
        "group_name": group_name # group_name 포함
    }

    try:
        response = requests.post(f"{RAG_PIPELINE_BASE_URL}/api/v1/analyze", json=payload)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생

        result = response.json()
        analysis_id = result.get("analysis_id")
        message = result.get("message", "분석 요청이 성공적으로 전송되었습니다.")

        response_message = f"RAG 분석 요청이 성공적으로 전송되었습니다. 분석 ID: {analysis_id}. {message}"
        return {"messages": [{"role": "assistant", "content": response_message}], "rag_analysis_result": result}

    except requests.exceptions.RequestException as e:
        logger.error(f"RAG 분석 API 호출 실패: {e}")
        return {"messages": [{"role": "system", "content": f"RAG 분석 API 호출 실패: {e}"}]}
    except json.JSONDecodeError as e:
        logger.error(f"RAG 분석 API 응답 파싱 실패: {e}")
        return {"messages": [{"role": "system", "content": f"RAG 분석 API 응답 파싱 실패: {e}"}]}
    except Exception as e:
        logger.error(f"RAG 분석 도구 실행 중 예상치 못한 오류 발생: {e}")
        return {"messages": [{"role": "system", "content": f"RAG 분석 도구 실행 중 예상치 못한 오류 발생: {e}"}
    ]
}
