"""사용자 요청의 의도를 분석하여 가장 적합한 도구를 찾아 실행하는 서비스입니다.
이 모듈은 도구 실행의 두뇌 역할을 하며, Python 도구와 LangFlow 워크플로우를 모두 처리합니다."""
import os
import sys
import importlib.util
import json
from typing import Dict, Any, Optional, List
import logging
import httpx

from sqlalchemy.orm import Session
from core.database import LangFlow, SessionLocal, LangflowToolMapping
from core.schemas import AgentState
from core.llm_client import get_client_for_model

logger = logging.getLogger(__name__)

# --- Constants ---
TOOLS_BASE_DIR = "tools"
LANGFLOW_EXECUTION_URL = os.getenv("LANGFLOW_EXECUTION_URL", "http://localhost:8000")
RUN_BEST_LANGFLOW_TOOL_NAME = "run_best_langflow_workflow"

# --- Generic Tool Schema for LangFlow ---
LANGFLOW_GENERIC_SCHEMA = {
    "type": "function",
    "function": {
        "name": RUN_BEST_LANGFLOW_TOOL_NAME,
        "description": "사용자의 복잡한 요청이나 질문에 가장 적합한 자동화된 워크플로우(LangFlow)를 찾아 실행합니다. 일반적인 정보 조회나 간단한 작업이 아닌, 여러 단계가 필요해 보이는 요청에 사용됩니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_input": {
                    "type": "object",
                    "description": "워크플로우에 전달할 추가적인 구조화된 입력값입니다."
                }
            }
        }
    }
}

# --- Main Entrypoint ---

async def decide_and_dispatch(state: AgentState) -> Dict[str, Any]:
    """
    사용자 의도를 분석하여 적절한 도구를 결정하고 실행합니다.
    """
    context = state.get("context")
    model_id = state.get("model_id")
    history = state.get("history", [])

    # 1. Get all available tools for the current context
    tool_schemas = get_available_tools_for_context(context)

    if not tool_schemas:
        logger.warning(f"No tools available for context '{context}'. Returning no-op.")
        history.append({"role": "assistant", "content": "현재 컨텍스트에서는 사용할 수 있는 도구가 없습니다."})
        return {"history": history}

    logger.info(f"Calling LLM to decide action for context '{context}'.")
    llm_client = get_client_for_model(model_id)

    # Construct tool descriptions string for the prompt
    tool_descriptions_string = "\n".join(
        [f"- '{tool['function']['name']}': {tool['function']['description']}" for tool in tool_schemas]
    )

    system_prompt_content = f"""당신은 지능형 디스패처입니다. 사용자의 요청을 분석하여, 주어진 작업을 완수하기 위해 가장 적합한 도구를 선택해야 합니다.
제공된 도구 목록과 각 도구의 설명을 신중하게 검토하여 최적의 결정을 내리세요.

--- 사용 가능한 도구 ---
{tool_descriptions_string}

--- 응답 형식 ---
응답은 반드시 다음 JSON 형식이어야 합니다: {{'next_tool': '선택한 도구 이름'}}
만약 사용자의 요청을 처리할 적합한 도구가 없다면, "none"을 선택하세요.
"""
    system_prompt = {
        "role": "system",
        "content": system_prompt_content
    }
    messages_for_llm = history + [system_prompt]

    response = llm_client.chat.completions.create(
        model=model_id,
        messages=messages_for_llm,
        response_format={"type": "json_object"}, # Force JSON output
        temperature=0 # 도구 선택의 결정론적 판단을 위해 temperature를 0으로 설정
    )
    response_message = response.choices[0].message.model_dump()
    history.append(response_message) # Append the LLM's response to history

    # Parse the LLM's JSON response
    try:
        choice_json = json.loads(response_message["content"])
        chosen_tool_name = choice_json.get("next_tool")
        logger.info(f"DEBUG: Parsed chosen_tool_name: '{chosen_tool_name}' (type: {type(chosen_tool_name)})") # 이 줄 추가
    except (json.JSONDecodeError, KeyError) as e:
        error_msg = f"LLM 응답 파싱 실패: {e}. 응답 내용: {response_message.get('content', 'N/A')}"
        logger.error(f"🚨 [TOOL_SELECTION_ERROR] {error_msg}")
        history.append({"role": "system", "content": error_msg})
        return {"history": history}

    logger.info(f"LLM chose to execute tool: {chosen_tool_name}")

    # Check if a tool was chosen or if LLM indicated no tool
    if chosen_tool_name == "none":
        logger.info("LLM decided not to use any tool (explicitly 'none').")
        # 도구가 실행되지 않았지만, 자연어 응답을 위해 '소통가' LLM을 호출해야 합니다.
        pass # 아래 '소통가' LLM 호출 부분으로 흐름을 넘깁니다.

    # Validate chosen tool name against available tool schemas
    valid_tool_names = {tool['function']['name'] for tool in tool_schemas}
    if chosen_tool_name not in valid_tool_names:
        error_msg = f"LLM이 유효하지 않은 도구({chosen_tool_name})를 반환했습니다. 유효한 도구: {', '.join(valid_tool_names)}"
        logger.error(f"🚨 [TOOL_SELECTION_ERROR] {error_msg}")
        history.append({"role": "system", "content": error_msg})
        return {"history": history}

    # Find the actual tool schema for the chosen tool to get its parameters
    chosen_tool_schema = next((tool for tool in tool_schemas if tool['function']['name'] == chosen_tool_name), None)
    if not chosen_tool_schema:
        error_msg = f"선택된 도구({chosen_tool_name})의 스키마를 찾을 수 없습니다."
        logger.error(f"🚨 [TOOL_SELECTION_ERROR] {error_msg}")
        history.append({"role": "system", "content": error_msg})
        return {"history": history}

    # This is a simplified approach for passing arguments.
    # A more robust solution would involve the LLM extracting arguments from the user's query.
    last_user_message_content = ""
    for msg in reversed(history):
        if msg.get("role") == "user":
            last_user_message_content = msg.get("content", "")
            break

    tool_args = {"input": last_user_message_content}

    # 4. Dispatch to the chosen tool executor
    result = {}
    if chosen_tool_name == RUN_BEST_LANGFLOW_TOOL_NAME:
        result = await find_and_run_best_flow(state, tool_args)
    else:
        python_tool_path = find_python_tool_path(chosen_tool_name, context)
        if python_tool_path:
            result = await run_python_tool(python_tool_path, tool_args, state)
        else:
            result = {"error": f"Tool '{chosen_tool_name}' was selected by LLM but not found in dispatcher."}
    
    # --- 추가될 부분: visualize_conversation_as_langflow 도구일 경우 바로 JSON 반환 ---
    if chosen_tool_name == "visualize_conversation_as_langflow":
        # 도구의 결과(result)가 이미 LangFlow JSON 문자열이므로, 이를 바로 반환합니다.
        # OpenAI 호환 응답 형식에 맞춰 assistant 메시지로 래핑합니다.
        return {"history": [{"role": "assistant", "content": result}]}
    # --- 추가될 부분 끝 ---

    # 5. Append tool result to history (이 부분은 이제 visualize_conversation_as_langflow 도구일 경우 실행되지 않음)
    history.append({
        "role": "system",
        "content": f"Tool '{chosen_tool_name}' was executed and returned the following result:\n\n{json.dumps(result, ensure_ascii=False, indent=2)}",
    })

    # 6. Call LLM again to get a natural language response (이 부분도 visualize_conversation_as_langflow 도구일 경우 실행되지 않음)
    logger.info("Calling LLM again to synthesize final response from tool result.")
    second_response = llm_client.chat.completions.create(
        model=model_id,
        messages=history,
    )
    history.append(second_response.choices[0].message.model_dump())

    return {"history": history}


# --- Tool Discovery & Execution ---

def get_available_tools_for_context(context: str) -> List[Dict[str, Any]]:
    """
    주어진 컨텍스트에서 사용 가능한 모든 도구의 스키마를 반환합니다.
    """
    all_schemas: List[Dict[str, Any]] = []

    if not context:
        logger.warning("Context not provided, cannot determine available tools.")
        return all_schemas
        
    # 1. Scan for Python tools
    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_map.py"):
                map_filepath = os.path.join(root, filename)
                try:
                    spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                    map_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(map_module)
                    
                    if context in getattr(map_module, 'tool_contexts', []):
                        tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                        if os.path.exists(tool_filepath):
                            tool_spec = importlib.util.spec_from_file_location("tool_module", tool_filepath)
                            tool_module = importlib.util.module_from_spec(tool_spec)
                            tool_spec.loader.exec_module(tool_module)
                            if hasattr(tool_module, 'available_tools'):
                                all_schemas.extend(getattr(tool_module, 'available_tools'))
                except Exception as e:
                    logger.error(f"Error loading tools from map file {map_filepath}: {e}")

    # 2. Check for LangFlows and add generic executor tool
    db: Session = SessionLocal()
    try:
        if db.query(LangFlow).join(LangflowToolMapping).filter(LangflowToolMapping.tool_contexts == context, LangFlow.is_active == True).first():
            all_schemas.append(LANGFLOW_GENERIC_SCHEMA)
    except Exception as e:
        logger.error(f"Error checking for LangFlows in context '{context}': {e}")
    finally:
        db.close()

    return all_schemas

def find_python_tool_path(tool_name: str, context: Optional[str]) -> Optional[str]:
    """
    Finds the file path of a Python tool based on its name and context.
    """
    if not context:
        return None
    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_map.py"):
                map_filepath = os.path.join(root, filename)
                try:
                    spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                    map_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(map_module)
                    if context in getattr(map_module, 'tool_contexts', []):
                        tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                        if os.path.exists(tool_filepath):
                            tool_spec = importlib.util.spec_from_file_location("tool_module", tool_filepath)
                            tool_module = importlib.util.module_from_spec(tool_spec)
                            tool_spec.loader.exec_module(tool_module)
                            if tool_name in getattr(tool_module, 'tool_functions', {}):
                                return tool_filepath
                except Exception as e:
                    logger.error(f"Error processing map file {map_filepath}: {e}")
    return None

async def run_python_tool(tool_path: str, tool_input: Optional[Dict[str, Any]], state: AgentState) -> Any:
    """
    Dynamically loads and executes a Python tool from a given file path.
    """
    try:
        module_name = os.path.splitext(os.path.relpath(tool_path, "."))[0].replace(os.path.sep, '.')
        spec = importlib.util.spec_from_file_location(module_name, tool_path)
        tool_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool_module)
        
        # The entrypoint for all python tools is the 'run' function.
        if hasattr(tool_module, 'run') and callable(getattr(tool_module, 'run')):
            return await getattr(tool_module, 'run')(tool_input, state)
        else:
            raise AttributeError(f"Tool module at {tool_path} does not have a callable 'run' function.")
    except Exception as e:
        logger.error(f"Failed to execute Python tool at {tool_path}: {e}", exc_info=True)
        return {"error": f"An error occurred while running the tool: {str(e)}"}

async def find_and_run_best_flow(state: AgentState, tool_input: Optional[Dict[str, Any]]) -> Any:
    """
    Uses an LLM to find the best flow based on its description and executes it.
    """
    user_query = state.get("input")
    context = state.get("context")
    model_id = state.get("model_id")

    if not user_query or not context:
        return {"error": "User query or context missing for semantic flow search."}

    db: Session = SessionLocal()
    try:
        available_flows = db.query(LangFlow).filter(LangFlow.context == context, LangFlow.is_active == True).all()
        if not available_flows:
            return {"message": "해당 컨텍스트에 실행 가능한 워크플로우가 없습니다."}

        flow_descriptions = "\n".join([f"- {flow.name}: {flow.description}" for flow in available_flows])
        prompt = f"""Based on the user's query, which of the following workflows is the best to run?
User Query: "{user_query}"

Available Workflows:
{flow_descriptions}

Respond with the exact name of the best workflow and nothing else."""

        logger.info(f"Calling LLM to choose the best LangFlow from {len(available_flows)} options.")
        llm_client = get_client_for_model(model_id)
        response = llm_client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        chosen_flow_name = response.choices[0].message.content.strip()

        chosen_flow = next((flow for flow in available_flows if flow.name == chosen_flow_name), None)

        if not chosen_flow:
            logger.error(f"LLM chose a non-existent flow: '{chosen_flow_name}'")
            return {"error": f"LLM chose a non-existent workflow: {chosen_flow_name}"}

        logger.info(f"Executing best-matched LangFlow: {chosen_flow.name}")
        return await run_langflow_tool(chosen_flow, tool_input, state)

    except Exception as e:
        logger.error(f"Error during semantic search and execution of LangFlow: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {str(e)}"}
    finally:
        db.close()

async def run_langflow_tool(flow: LangFlow, tool_input: Optional[Dict[str, Any]], state: AgentState) -> Any:
    """
    Executes a given LangFlow workflow.
    """
    execution_url = f"{LANGFLOW_EXECUTION_URL}/flows/run/{flow.name}"
    # The user's direct input might be in the tool_input from the LLM or the original state input
    final_tool_input = tool_input or {"input": state.get("input")}
    request_body = {"user_input": final_tool_input}

    logger.info(f"Calling LangFlow execution endpoint: {execution_url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(execution_url, json=request_body, timeout=60.0)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"HTTP request to LangFlow failed: {e}", exc_info=True)
        return {"error": f"Failed to connect to LangFlow service: {str(e)}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"LangFlow service returned an error: {e.response.status_code} {e.response.text}", exc_info=True)
        return {"error": f"LangFlow service error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        logger.error(f"Failed to execute LangFlow tool '{flow.name}': {e}", exc_info=True)
        return {"error": f"An unexpected error occurred while running the LangFlow tool: {str(e)}"}