"""
새로운 Modal Context Protocol 아키텍처의 핵심 노드를 정의합니다.
"""
from typing import Dict, Any

from core.schemas import AgentState
from services import tool_dispatcher
import logging

logger = logging.getLogger(__name__)

async def tool_dispatcher_node(state: AgentState) -> Dict[str, Any]:
    """
    중앙 집중식 도구 디스패처를 호출하여 의도 분석 및 도구 실행을 위임합니다.
    이 노드는 이제 tool_dispatcher.py에 구현된 새로운 아키텍처의 간단한 진입점 역할을 합니다.
    """
    logger.info("Passing control to the centralized tool dispatcher.")
    # 새로운 디스패처가 의도 분석, 도구 실행, 상태 업데이트까지 모두 처리합니다.
    print("===tool_dispatcher_node===")
    return await tool_dispatcher.decide_and_dispatch(state)
