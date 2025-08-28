import json
from typing import Dict, Any, Optional, List
from core.schemas import AgentState
from core.database import SessionLocal
from services.db_service import LangFlowService

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

async def execute_langflow_run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """저장된 LangFlow JSON을 실행하는 노드"""
    try:
        flow_name = None
        if tool_input and 'flow_name' in tool_input:
            flow_name = tool_input['flow_name']
        else:
            # 사용자 메시지에서 플로우 이름 추출
            last_message = state["history"][-1]["content"] if state["history"] else ""
            # 간단한 파싱으로 플로우 이름 추출 (실제로는 더 정교한 파싱이 필요할 수 있음)
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
        
        # 데이터베이스에서 플로우 찾기
        db = SessionLocal()
        try:
            db_flow = LangFlowService.get_flow_by_name(db, flow_name)
            
            if not db_flow:
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": f"'{flow_name}' 플로우를 찾을 수 없습니다. 저장된 플로우 목록을 확인해보세요."
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
                result = f"실행 시간: {execution_result.execution_time:.2f}초\n"
                result += f"세션 ID: {execution_result.session_id}\n"
                if execution_result.outputs:
                    result += f"출력 결과:\n{json.dumps(execution_result.outputs, indent=2, ensure_ascii=False)}"
                else:
                    result = "플로우가 성공적으로 실행되었습니다."
            else:
                result = f"실행 실패: {execution_result.error}"
            
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"✅ LangFlow '{flow_name}' 실행 완료!\n\n실행 결과:\n{result}"
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
        # 데이터베이스에서 플로우 목록 조회
        db = SessionLocal()
        try:
            db_flows = LangFlowService.get_all_flows(db)
            
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
                    }
                },
                "required": ["flow_name"]
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
