import json
import os
from typing import Dict, Any
from core.schemas import ChatState
from core.database import SessionLocal
from services.db_service import LangFlowService

# LangFlow 실행 도구 설명
langflow_execute_description = {
    "name": "execute_langflow",
    "description": "저장된 LangFlow JSON을 실행합니다. 플로우 이름을 지정하여 실행할 수 있습니다."
}

langflow_list_description = {
    "name": "list_langflows", 
    "description": "저장된 모든 LangFlow 목록을 조회합니다."
}

langflow_descriptions = [langflow_execute_description, langflow_list_description]

def execute_langflow_node(state: ChatState) -> Dict[str, Any]:
    """저장된 LangFlow JSON을 실행하는 노드"""
    try:
        # 사용자 메시지에서 플로우 이름 추출
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        
        # 간단한 파싱으로 플로우 이름 추출 (실제로는 더 정교한 파싱이 필요할 수 있음)
        flow_name = None
        if "실행" in last_message or "execute" in last_message.lower():
            # "플로우명 실행" 또는 "execute 플로우명" 패턴 찾기
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
                "input_value": state.get("original_input", ""),
                "message": last_message
            }
            
            # 비동기 실행을 동기 컨텍스트에서 처리
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            execution_result = loop.run_until_complete(
                langflow_service.execute_flow_by_name(flow_name, inputs)
            )
            
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

def list_langflows_node(state: ChatState) -> Dict[str, Any]:
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

def simulate_langflow_execution(flow_data: Dict[str, Any], user_input: str) -> str:
    """
    LangFlow 실행을 시뮬레이션합니다.
    실제 구현에서는 LangFlow 엔진을 사용해야 합니다.
    """
    try:
        nodes = flow_data.get("data", {}).get("nodes", [])
        edges = flow_data.get("data", {}).get("edges", [])
        
        # 간단한 시뮬레이션: 노드 타입별로 다른 처리
        results = []
        
        for node in nodes:
            node_type = node.get("type", "unknown")
            node_data = node.get("data", {})
            
            if "input" in node_type.lower():
                results.append(f"📥 입력: {user_input}")
            elif "llm" in node_type.lower() or "chat" in node_type.lower():
                results.append(f"🤖 LLM 처리: 사용자 입력을 분석하고 응답을 생성했습니다.")
            elif "output" in node_type.lower():
                results.append(f"📤 출력: 처리 결과를 반환합니다.")
            elif "prompt" in node_type.lower():
                template = node_data.get("template", "프롬프트 템플릿")
                results.append(f"📝 프롬프트: {template[:50]}...")
            else:
                results.append(f"⚙️ {node_type}: 노드 처리 완료")
        
        return "\n".join(results) if results else "플로우가 성공적으로 실행되었습니다."
        
    except Exception as e:
        return f"시뮬레이션 중 오류 발생: {str(e)}"