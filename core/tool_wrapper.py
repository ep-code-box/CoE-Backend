"""
도구 실행을 감싸는 래퍼 모듈입니다.
모든 도구 실행 시 로깅을 추가하여 실행 추적을 가능하게 합니다.
"""

import logging
import time
import inspect # New import
from typing import Callable, Dict, Any
from functools import wraps
from core.schemas import ChatState

logger = logging.getLogger(__name__)


def tool_execution_wrapper(tool_name: str, tool_func: Callable) -> Callable:
    """
    도구 실행을 감싸는 래퍼 함수입니다.
    도구 실행 시작과 완료를 로깅하고 대화 이력에 저장합니다.
    
    Args:
        tool_name: 도구 이름
        tool_func: 실제 도구 함수
        
    Returns:
        래핑된 도구 함수
    """
    @wraps(tool_func)
    async def wrapper(state: ChatState) -> Dict[str, Any]: # Changed to async def
        start_time = time.time()
        
        # 도구 실행 시작 로그 (전용 로거 사용)
        tool_logger = logging.getLogger("tool_tracker")
        tool_logger.info(f"TOOL_EXECUTION_START: '{tool_name}'")
        logger.info(f"🚀 [TOOL_EXECUTION_START] Starting tool: '{tool_name}'")
        
        # 도구 컨텍스트 추출
        tool_context = state.get("_tool_context", {})
        session_id = tool_context.get("session_id")
        chat_service = tool_context.get("chat_service")
        turn_number = tool_context.get("turn_number", 1)
        
        try:
            # 실제 도구 실행
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(state) # Await if it's an async function
            else:
                result = tool_func(state)
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            execution_time_ms = int(execution_time * 1000)
            
            # 도구 실행 완료 로그 (전용 로거 사용)
            tool_logger.info(f"TOOL_EXECUTION_COMPLETE: '{tool_name}' | DURATION: {execution_time:.2f}s")
            logger.info(f"✅ [TOOL_EXECUTION_COMPLETE] Tool '{tool_name}' completed successfully in {execution_time:.2f}s")
            
            # 대화 이력에 도구 실행 정보 저장
            if chat_service and session_id:
                try:
                    # 도구 실행 결과를 시스템 메시지로 저장
                    tool_result_content = ""
                    if result and "messages" in result and result["messages"]:
                        last_message = result["messages"][-1]
                        if isinstance(last_message, dict) and "content" in last_message:
                            content = last_message["content"]
                            tool_result_content = str(content) if content is not None else ""
                        elif last_message is not None: # Handle cases where last_message is not a dict but not None
                            tool_result_content = str(last_message)
                    elif result is not None: # Handle cases where result is not a dict with messages but not None
                        tool_result_content = str(result)
                    
                    chat_service.save_chat_message(
                        session_id=session_id,
                        role="system",
                        content=f"[도구 실행] {tool_name}: {tool_result_content[:200]}{'...' if len(tool_result_content) > 200 else ''}",
                        turn_number=turn_number,
                        selected_tool=tool_name,
                        tool_execution_time_ms=execution_time_ms,
                        tool_success=True,
                        tool_metadata={
                            "execution_time_ms": execution_time_ms,
                            "result_preview": tool_result_content[:100] if tool_result_content else None
                        }
                    )
                except Exception as db_error:
                    logger.warning(f"도구 실행 정보 저장 실패: {db_error}")
            
            return result
            
        except Exception as e:
            # 실행 시간 계산
            execution_time = time.time() - start_time
            execution_time_ms = int(execution_time * 1000)
            error_message = str(e)
            
            # 도구 실행 실패 로그 (전용 로거 사용)
            tool_logger.error(f"TOOL_EXECUTION_ERROR: '{tool_name}' | DURATION: {execution_time:.2f}s | ERROR: {error_message}")
            logger.error(f"❌ [TOOL_EXECUTION_ERROR] Tool '{tool_name}' failed after {execution_time:.2f}s: {error_message}")
            
            # 대화 이력에 도구 실행 오류 정보 저장
            if chat_service and session_id:
                try:
                    chat_service.save_chat_message(
                        session_id=session_id,
                        role="system",
                        content=f"[도구 실행 오류] {tool_name}: {error_message}",
                        turn_number=turn_number,
                        selected_tool=tool_name,
                        tool_execution_time_ms=execution_time_ms,
                        tool_success=False,
                        tool_metadata={
                            "execution_time_ms": execution_time_ms,
                            "error_message": error_message
                        }
                    )
                except Exception as db_error:
                    logger.warning(f"도구 실행 오류 정보 저장 실패: {db_error}")
            
            # 에러 상태를 반환하여 그래프가 적절히 처리할 수 있도록 함
            return {
                "messages": [{"role": "system", "content": f"도구 '{tool_name}' 실행 중 오류가 발생했습니다: {error_message}"}],
                "next_node": "error"
            }
    
    return wrapper


def wrap_all_tools(tool_nodes: Dict[str, Callable]) -> Dict[str, Callable]:
    """
    모든 도구 노드에 실행 래퍼를 적용합니다.
    
    Args:
        tool_nodes: 원본 도구 노드 딕셔너리
        
    Returns:
        래핑된 도구 노드 딕셔너리
    """
    wrapped_tools = {}
    
    for tool_name, tool_func in tool_nodes.items():
        wrapped_tools[tool_name] = tool_execution_wrapper(tool_name, tool_func)
        logger.debug(f"🔧 [TOOL_WRAPPER] Wrapped tool: '{tool_name}'")
    
    logger.info(f"🔧 [TOOL_WRAPPER] Successfully wrapped {len(wrapped_tools)} tools with execution logging")
    
    return wrapped_tools