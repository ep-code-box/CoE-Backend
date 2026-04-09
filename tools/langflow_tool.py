import json
import os
from typing import Dict, Any, Optional, List
from core.schemas import AgentState
from core.database import SessionLocal, LangflowToolMapping
from services.db_langflow_service import LangFlowService

# LangFlow 실행 도구 설명 (registry.py에서 수집되지 않도록 _description으로 끝나지 않게 명명)
langflow_execute_config = {
    "name": "execute_langflow",
    "description": "저장된 LangFlow JSON을 실행합니다. 플로우 이름을 지정하여 실행할 수 있습니다."
}

langflow_list_config = {
    "name": "list_langflows", 
    "description": "저장된 모든 LangFlow 목록을 조회합니다."
}

# registry.py에서 수집할 실제 설명 (중복 방지)
langflow_descriptions = [langflow_execute_config, langflow_list_config]

ENABLE_GROUP_FILTERING = os.getenv("ENABLE_GROUP_FILTERING", "true").lower() in {"1", "true", "yes", "on"}


def _flow_allowed_for_context(
    db: SessionLocal,
    flow_id: str,
    context: Optional[str],
    group_name: Optional[str],
) -> bool:
    if not context:
        return True

    mappings = (
        db.query(LangflowToolMapping)
        .filter(
            LangflowToolMapping.flow_id == flow_id,
            LangflowToolMapping.context == context,
        )
        .all()
    )

    if not mappings:
        return False

    if not ENABLE_GROUP_FILTERING:
        return True

    normalized_group = (group_name or "").strip().lower() or None
    if normalized_group is not None:
        for mapping in mappings:
            val = (mapping.group_name or "").strip().lower() or None
            if val is not None and val == normalized_group:
                return True
        for mapping in mappings:
            if mapping.group_name is None:
                return True
        return False

    for mapping in mappings:
        if mapping.group_name is None:
            return True
    return False

async def execute_langflow_run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """저장된 LangFlow JSON을 실행하는 노드"""
    try:
        flow_name = None
        flow_id = None
        if tool_input:
            flow_name = tool_input.get('flow_name')
            flow_id = tool_input.get('flow_id')
        last_message = ""
        if not flow_name and not flow_id:
            # 사용자 메시지에서 플로우 이름 추출
            try:
                last_message = state["history"][-1]["content"]
            except:
                pass
            # 간단한 파싱으로 플로우 이름 추출
            if "실행" in last_message or "execute" in last_message.lower():
                words = last_message.split()
                for i, word in enumerate(words):
                    if word in ["실행", "execute"] and i > 0:
                        flow_name = words[i-1]
                        break
                    elif word in ["실행", "execute"] and i < len(words) - 1:
                        flow_name = words[i+1]
                        break
        
        if not flow_name:
            return {
                "messages": [{
                    "role": "assistant", 
                    "content": "실행할 LangFlow의 이름을 지정해주세요. 예: '내플로우 실행' 또는 'execute myflow'"
                }]
            }
        
        # 데이터베이스에서 플로우 찾기 (context 허용 여부 확인)
        db = SessionLocal()
        try:
            db_flow = None
            if flow_id:
                # 1. 먼저 정수 ID로 시도 (id 컬럼)
                if isinstance(flow_id, (int, str)) and str(flow_id).isdigit():
                    db_flow = LangFlowService.get_flow_by_id(db, int(flow_id))
                
                # 2. 정수 ID로 못 찾았거나 flow_id가 문자열인 경우 flow_id 컬럼으로 시도
                if not db_flow:
                    db_flow = db.query(LangFlow).filter(LangFlow.flow_id == str(flow_id), LangFlow.is_active == True).first()
            else:
                db_flow = LangFlowService.get_flow_by_name(db, flow_name)
            
            if not db_flow:
                target = f"ID '{flow_id}'" if flow_id else f"이름 '{flow_name}'"
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": f"{target} 플로우를 찾을 수 없습니다. 저장된 플로우 목록을 확인해보세요."
                    }]
                }
            
            # 실제 사용된 이름 확보 (로깅용)
            actual_flow_name = db_flow.name
            
            # 현재 컨텍스트에서 사용 가능한지 확인
            current_ctx = state.get("context")
            group_name = state.get("group_name") if isinstance(state, dict) else None
            if current_ctx and not _flow_allowed_for_context(db, db_flow.flow_id, current_ctx, group_name):
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": f"현재 컨텍스트('{current_ctx}')에서는 '{flow_name}' 플로우를 사용할 수 없습니다."
                    }]
                }

            # 플로우 데이터 로드
            flow_data = LangFlowService.get_flow_data_as_dict(db_flow)
            
            # 실제 LangFlow 실행 로직
            from services.langflow.langflow_service import langflow_service
            import asyncio
            
            # 입력 데이터 구성
            inputs = {
                "input_value": state.get("input", ""), # state['input'] 사용
                "message": last_message # 마지막 메시지 사용
            }
            
            # 비동기 실행을 동기 컨텍스트에서 처리
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            execution_result = await langflow_service.execute_flow(flow_data, inputs)
            
            if execution_result.success:
                from services.tool_dispatcher import _format_flow_outputs_for_chat

                pretty_output = _format_flow_outputs_for_chat(execution_result.outputs or {})
                result_lines = [
                    f"실행 시간: {execution_result.execution_time:.2f}초",
                    f"세션 ID: {execution_result.session_id}",
                ]
                if pretty_output:
                    result_lines.append("출력 결과:")
                    result_lines.append(pretty_output)
                result = "\n".join(result_lines)
            else:
                result = f"실행 실패: {execution_result.error}"
            
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"✅ LangFlow '{actual_flow_name}' 실행 완료!\n\n실행 결과:\n{result}"
                }]
            }
        finally:
            db.close()
        
    except Exception as e:
        return {
            "messages": [{
                "role": "assistant",
                "content": f"❌ LangFlow 실행 중 오류가 발생했습니다: {str(e)}"
            }]
        }

async def list_langflows_run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """저장된 LangFlow 목록을 조회하는 노드"""
    try:
        # 데이터베이스에서 플로우 목록 조회 (컨텍스트 필터)
        db = SessionLocal()
        try:
            current_ctx = state.get("context")
            group_name = state.get("group_name") if isinstance(state, dict) else None
            all_flows = LangFlowService.get_all_flows(db)
            db_flows: List[Any] = []
            for flow in all_flows:
                if not getattr(flow, "is_active", True):
                    continue
                if current_ctx and not _flow_allowed_for_context(db, flow.flow_id, current_ctx, group_name):
                    continue
                db_flows.append(flow)
            
            if not db_flows:
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "📋 저장된 LangFlow가 없습니다.\n\n'/flows/save' API를 사용하여 플로우를 저장할 수 있습니다."
                    }]
                }
            
            # 플로우 목록 포맷팅
            flow_list = "📋 저장된 LangFlow 목록:\n\n"
            for i, db_flow in enumerate(db_flows, 1):
                # 플로우 데이터에서 노드/엣지 수 계산
                flow_data = LangFlowService.get_flow_data_as_dict(db_flow)
                nodes_count = len(flow_data.get("data", {}).get("nodes", []))
                edges_count = len(flow_data.get("data", {}).get("edges", []))
                
                flow_list += f"{i}. **{db_flow.name}**\n"
                flow_list += f"   - 설명: {db_flow.description or '설명 없음'}\n"
                flow_list += f"   - 노드 수: {nodes_count}, 엣지 수: {edges_count}\n"
                flow_list += f"   - 생성일: {db_flow.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            
            flow_list += "💡 플로우를 실행하려면 '플로우명 실행' 또는 'execute 플로우명'이라고 말해주세요."
            
            return {
                "messages": [{
                    "role": "assistant",
                    "content": flow_list
                }]
            }
        finally:
            db.close()
        
    except Exception as e:
        return {
            "messages": [{
                "role": "assistant",
                "content": f"❌ LangFlow 목록 조회 중 오류가 발생했습니다: {str(e)}"
            }]
        }

# --- Tool Schemas and Functions for LLM ---

available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "execute_langflow",
            "description": "저장된 LangFlow JSON을 실행합니다. 플로우 이름을 지정하여 실행할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flow_name": {
                        "type": "string",
                        "description": "실행할 LangFlow의 이름"
                    },
                    "flow_id": {
                        "type": "integer",
                        "description": "실행할 LangFlow의 ID (이름 대신 사용할 수 있음)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_langflows",
            "description": "저장된 모든 LangFlow 목록을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

tool_functions: Dict[str, callable] = {
    "execute_langflow": execute_langflow_run,
    "list_langflows": list_langflows_run,
}
