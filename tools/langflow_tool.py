import json
import os
from typing import Dict, Any
from schemas import ChatState

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
        
        # flows 디렉토리에서 해당 플로우 찾기
        flows_dir = "flows"
        flow_path = None
        
        if os.path.exists(flows_dir):
            # 직접 파일명으로 찾기
            direct_path = os.path.join(flows_dir, f"{flow_name}.json")
            if os.path.exists(direct_path):
                flow_path = direct_path
            else:
                # 저장된 이름으로 찾기
                for filename in os.listdir(flows_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(flows_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                flow_data = json.load(f)
                            if flow_data.get("saved_name") == flow_name:
                                flow_path = filepath
                                break
                        except Exception:
                            continue
        
        if not flow_path:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"'{flow_name}' 플로우를 찾을 수 없습니다. 저장된 플로우 목록을 확인해보세요."
                }]
            }
        
        # 플로우 JSON 로드
        with open(flow_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
        
        # 실제 LangFlow 실행 로직 (현재는 시뮬레이션)
        # 실제 구현에서는 LangFlow 엔진을 사용하여 플로우를 실행해야 합니다
        result = simulate_langflow_execution(flow_data, state.get("original_input", ""))
        
        return {
            "messages": [{
                "role": "assistant",
                "content": f"✅ LangFlow '{flow_name}' 실행 완료!\n\n실행 결과:\n{result}"
            }]
        }
        
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
        flows_dir = "flows"
        flows = []
        
        if os.path.exists(flows_dir):
            for filename in os.listdir(flows_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(flows_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            flow_data = json.load(f)
                        
                        flow_info = {
                            "name": flow_data.get("saved_name", filename[:-5]),
                            "description": flow_data.get("description", "설명 없음"),
                            "nodes": len(flow_data.get("data", {}).get("nodes", [])),
                            "edges": len(flow_data.get("data", {}).get("edges", []))
                        }
                        flows.append(flow_info)
                    except Exception as e:
                        print(f"Error reading flow file {filename}: {e}")
                        continue
        
        if not flows:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "📋 저장된 LangFlow가 없습니다.\n\n'/flows/save' API를 사용하여 플로우를 저장할 수 있습니다."
                }]
            }
        
        # 플로우 목록 포맷팅
        flow_list = "📋 저장된 LangFlow 목록:\n\n"
        for i, flow in enumerate(flows, 1):
            flow_list += f"{i}. **{flow['name']}**\n"
            flow_list += f"   - 설명: {flow['description']}\n"
            flow_list += f"   - 노드 수: {flow['nodes']}, 엣지 수: {flow['edges']}\n\n"
        
        flow_list += "💡 플로우를 실행하려면 '플로우명 실행' 또는 'execute 플로우명'이라고 말해주세요."
        
        return {
            "messages": [{
                "role": "assistant",
                "content": flow_list
            }]
        }
        
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