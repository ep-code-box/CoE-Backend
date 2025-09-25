"""
Front-end에서 요청된 도구를 찾아 실행하고, 그 결과를 반환하는 서비스입니다.
"""
import os
import sys
import importlib.util
from typing import Dict, Any, Optional, List, Tuple, Callable, Set
import re
import logging
import httpx

from sqlalchemy.orm import Session
from core.database import LangFlow, LangflowToolMapping, SessionLocal
from services.db_langflow_service import LangFlowService
from services.langflow.langflow_service import langflow_service
from core.llm_client import get_client_for_model, client as default_llm_client

logger = logging.getLogger(__name__)

# 도구가 위치한 기본 디렉토리
TOOLS_BASE_DIR = "tools"
# LangFlow 실행을 위한 기본 URL
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:8000")
AUTO_ROUTE_STRATEGY = os.getenv("AUTO_ROUTE_STRATEGY", "llm").lower()  # llm|text
AUTO_ROUTE_MODEL = os.getenv("AUTO_ROUTE_MODEL", "gpt-4o-mini")
AUTO_ROUTE_MAX_CANDIDATES = int(os.getenv("AUTO_ROUTE_MAX_CANDIDATES", "16"))
AUTO_ROUTE_MAX_DESC_CHARS = int(os.getenv("AUTO_ROUTE_MAX_DESC_CHARS", "512"))
AUTO_ROUTE_LLM_FALLBACK = os.getenv("AUTO_ROUTE_LLM_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}
ENABLE_GROUP_FILTERING = os.getenv("ENABLE_GROUP_FILTERING", "true").lower() in {"1", "true", "yes", "on"}

def _extract_text_from_raw_string(s: str) -> Optional[str]:
    """Heuristically extract a natural-language message from a raw LangFlow repr string.

    Targets patterns like:
    - ChatOutputResponse(message='...')
    - artifacts={'message': '...'}
    - data={'text': '...'}
    - outputs={'message': {'message': '...'}}
    Returns the first plausible match.
    """
    try:
        import re as _re
        # Prefer explicit chat output message
        m = _re.search(r"ChatOutputResponse\(message='([^']+)'", s)
        if m:
            return m.group(1).strip()
        # Artifacts message
        m = _re.search(r"artifacts=\{[^}]*'message'\s*:\s*'([^']+)'", s)
        if m:
            return m.group(1).strip()
        # Outputs.message.message
        m = _re.search(r"outputs=\{[^}]*'message'\s*:\s*\{[^}]*'message'\s*:\s*'([^']+)'", s)
        if m:
            return m.group(1).strip()
        # Generic 'text': '...'
        m = _re.search(r"'text'\s*:\s*'([^']+)'", s)
        if m:
            return m.group(1).strip()
        # Double-quoted text/message content
        m = _re.search(r'"text"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', s)
        if m:
            return m.group(1).strip()
        m = _re.search(r"'text'\s*:\s*\"([^\"\\]*(?:\\.[^\"\\]*)*)\"", s)
        if m:
            return m.group(1).strip()
        m = _re.search(r'"message"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', s)
        if m:
            return m.group(1).strip()
        # `Message(text_key='text', data={'text': "..."})` pattern
        m = _re.search(r"data=\{[^}]*['\"]text['\"]\s*:\s*\"([^\"\\]*(?:\\.[^\"\\]*)*)\"", s, _re.S)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None

def _extract_primary_text(obj: Any) -> Optional[str]:
    """Best-effort extraction of a human-friendly text from LangFlow-like outputs.

    Tries common keys and nested shapes (e.g., outputs.message.message, artifacts.message, text, content).
    Avoids returning large 'raw' blobs.
    """
    # Fast path: direct string
    if isinstance(obj, str):
        s = obj.strip()
        return s if s else None

    # Dict path: prefer specific keys
    if isinstance(obj, dict):
        # flow outputs often come wrapped like {'message': {'message': '...'} }
        if set(obj.keys()) == {"message"} and isinstance(obj.get("message"), dict):
            inner_candidate = obj.get("message")
            normalized = _extract_primary_text(inner_candidate)
            if normalized:
                return normalized

        if all(k in obj for k in ("message", "type")) and isinstance(obj.get("message"), str):
            maybe_msg = obj.get("message", "").strip()
            if maybe_msg:
                return maybe_msg

        # Handle 'raw' string payloads by attempting to parse for a likely message
        raw = obj.get("raw")
        if isinstance(raw, str):
            parsed = _extract_text_from_raw_string(raw)
            if parsed:
                return parsed
        # Avoid raw
        for k in ("message", "text", "output", "result", "content"):
            if k in obj and k != "raw":
                v = obj.get(k)
                # message may itself be a dict: {"message": "...", "type": "text"}
                if isinstance(v, dict):
                    inner = _extract_primary_text(v)
                    if inner:
                        return inner
                elif isinstance(v, str):
                    s = v.strip()
                    if s:
                        return s

        data_block = obj.get("data")
        if isinstance(data_block, dict):
            data_text = data_block.get("text")
            if isinstance(data_text, str) and data_text.strip():
                return data_text.strip()
            inner = _extract_primary_text(data_block)
            if inner:
                return inner

        # artifacts often carries a flat message
        artifacts = obj.get("artifacts")
        if isinstance(artifacts, dict):
            msg = artifacts.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
            inner = _extract_primary_text(artifacts)
            if inner:
                return inner

        # outputs nesting
        outputs = obj.get("outputs")
        if outputs is not None:
            inner = _extract_primary_text(outputs)
            if inner:
                return inner

        results = obj.get("results")
        if results is not None:
            inner = _extract_primary_text(results)
            if inner:
                return inner

        value_field = obj.get("value")
        if isinstance(value_field, str) and value_field.strip():
            return value_field.strip()

        # fallback: scan remaining values for recognizable text fields
        try:
            for key, value in obj.items():
                if isinstance(value, str):
                    lowered = str(key).lower()
                    if lowered in {"text", "message", "content", "output", "result", "value"}:
                        candidate = value.strip()
                        if candidate:
                            return candidate
                inner = _extract_primary_text(value)
                if inner:
                    return inner
        except Exception:
            pass

        # messages list with dicts
        messages = obj.get("messages")
        if isinstance(messages, list):
            inner = _extract_primary_text(messages)
            if inner:
                return inner

    # Objects exposing LangFlow-style attributes
    if hasattr(obj, "results"):
        try:
            inner = _extract_primary_text(getattr(obj, "results"))
            if inner:
                return inner
        except Exception:
            pass

    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            inner = _extract_primary_text(obj.dict())  # type: ignore[arg-type]
            if inner:
                return inner
        except Exception:
            pass

    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            inner = _extract_primary_text(obj.to_dict())  # type: ignore[arg-type]
            if inner:
                return inner
        except Exception:
            pass

    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            inner = _extract_primary_text(obj.model_dump())  # type: ignore[arg-type]
            if inner:
                return inner
        except Exception:
            pass

    if hasattr(obj, "data") and not isinstance(obj, (str, bytes)):
        try:
            data_attr = getattr(obj, "data")
            if isinstance(data_attr, (dict, list)):
                inner = _extract_primary_text(data_attr)
                if inner:
                    return inner
        except Exception:
            pass

    # Dataclass or custom objects: inspect common attributes / __dict__
    try:
        if hasattr(obj, "text") and isinstance(getattr(obj, "text"), str):
            text_attr = getattr(obj, "text").strip()
            if text_attr:
                return text_attr
        if hasattr(obj, "message") and isinstance(getattr(obj, "message"), str):
            message_attr = getattr(obj, "message").strip()
            if message_attr:
                return message_attr
        if hasattr(obj, "data") and isinstance(getattr(obj, "data"), dict):
            inner = _extract_primary_text(getattr(obj, "data"))
            if inner:
                return inner
        if hasattr(obj, "__dict__"):
            dict_view = vars(obj)
            if dict_view:
                inner = _extract_primary_text(dict_view)
                if inner:
                    return inner
    except Exception:
        pass

    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, dict)):
        try:
            for item in obj:
                inner = _extract_primary_text(item)
                if inner:
                    return inner
        except Exception:
            pass

    # List path: scan items
    if isinstance(obj, list):
        for it in obj:
            inner = _extract_primary_text(it)
            if inner:
                return inner

    return None

def _format_flow_outputs_for_chat(outputs: Any) -> str:
    """Format LangFlow execution outputs as a clean chat message.

    Prefers the primary user-facing text. Falls back to compact JSON.
    """
    try:
        primary = _extract_primary_text(outputs)
        if primary:
            return primary
        # fallback to compact JSON (not repr)
        import json as _json
        return _json.dumps(outputs, ensure_ascii=False, default=str)
    except Exception:
        return str(outputs)

def _format_tool_result_for_chat(result: Any) -> str:
    """Format Python tool execution result into a user-friendly message.

    Common tool return shape is {"messages": [{"role": "assistant", "content": "..."}, ...]}.
    If present, return the first assistant content. Otherwise, stringify compactly.
    """
    try:
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            msgs = result.get("messages")
            if isinstance(msgs, list) and msgs:
                first = msgs[0]
                if isinstance(first, dict):
                    content = first.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
        import json as _json
        return _json.dumps(result, ensure_ascii=False, default=str)
    except Exception:
        return str(result)

async def _llm_generate_tool_arguments(tool_schema: Dict[str, Any], user_text: str) -> Optional[Dict[str, Any]]:
    """Ask the LLM to produce a strict JSON object of arguments for the selected tool.

    Relies on the tool's JSON schema (function.parameters). Returns dict or None.
    """
    try:
        if not isinstance(tool_schema, dict):
            return None
        fn = tool_schema.get("function") or {}
        params = fn.get("parameters")
        if not params:
            return None

        import json as _json
        system = (
            "You generate ONLY JSON arguments for a function call.\n"
            "Rules:\n"
            "- Output a single JSON object matching the provided JSON Schema.\n"
            "- Do not include explanations, code fences, or extra text.\n"
            "- If a field is not inferable, omit it."
        )
        user = (
            "Function schema (JSON Schema for arguments):\n"
            f"{_json.dumps(params, ensure_ascii=False)}\n\n"
            f"User input:\n{user_text}"
        )
        completion = await default_llm_client.chat.completions.create(
            model=AUTO_ROUTE_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=256,
        )
        content = completion.choices[0].message.content or ""
        # Extract JSON object
        try:
            return _json.loads(content)
        except Exception:
            import re as _re
            m = _re.search(r"\{.*\}", content, _re.S)
            if not m:
                return None
            return _json.loads(m.group(0))
    except Exception:
        return None

### Note: No regex-based argument inference here.
### Tool arguments should be supplied by the LLM via tool calls.

async def dispatch_and_execute(tool_name: str, tool_input: Optional[Dict[str, Any]], state: "AgentState") -> Optional[Any]:
    """
    주어진 tool_name에 따라 적절한 도구를 찾아 실행합니다.

    Args:
        tool_name: 실행할 도구의 이름 (Python 도구 키 또는 LangFlow 엔드포인트 이름).
        tool_input: 도구에 전달될 입력 값.
        state: 현재 에이전트의 상태.

    Returns:
        도구 실행 결과. 도구를 찾지 못하면 None을 반환합니다.
    """
    logger.info(f"Attempting to dispatch tool: {tool_name}")

    # 1. Python 도구인지 확인하고 실행
    python_tool_path = find_python_tool_path(tool_name)
    if python_tool_path:
        logger.info(f"Found Python tool for '{tool_name}' at '{python_tool_path}'. Executing...")
        return await run_python_tool(python_tool_path, tool_input, state)

    # 2. LangFlow가 있는지 확인하고 실행 (엔드포인트/이름 + context 매핑 기준)
    ctx = state.get("context") if isinstance(state, dict) else None
    group_name = state.get("group_name") if isinstance(state, dict) else None
    langflow = find_langflow_tool(tool_name, ctx, group_name)
    if langflow:
        logger.info(f"Found LangFlow '{tool_name}' (context='{ctx}'). Executing...")
        return await run_langflow_tool(langflow, tool_input, state)

    # 3. 해당하는 도구가 없으면 None 반환
    logger.warning(f"No tool found for '{tool_name}'.")
    return None

def find_python_tool_path(tool_name: str) -> Optional[str]:
    """
    _map.py 파일을 기반으로 Python 도구 파일의 경로를 찾습니다.

    Args:
        tool_name: 찾고자 하는 도구의 이름 (Python 도구 키).

    Returns:
        도구 파일의 절대 경로. 없으면 None.
    """
    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    logger.debug(f"Searching for Python tool '{tool_name}' in: {tools_dir}")

    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_map.py"):
                map_filepath = os.path.join(root, filename)
                try:
                    spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                    map_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(map_module)
                    
                    # endpoints 딕셔너리의 key 값들을 도구 이름으로 간주
                    endpoints = getattr(map_module, 'endpoints', {})
                    
                    if tool_name in endpoints.keys():
                        tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                        if os.path.exists(tool_filepath):
                            logger.info(f"Found matching tool '{tool_name}' in '{map_filepath}' -> '{tool_filepath}'")
                            return tool_filepath
                        else:
                            logger.warning(f"Found map file for '{tool_name}' but corresponding _tool.py file not found at '{tool_filepath}'")
                except Exception as e:
                    logger.error(f"Error reading map file {map_filepath}: {e}")
    
    return None

def get_available_tools_for_context(
    context: str,
    group_name: Optional[str] = None,
    enable_group_filtering: Optional[bool] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Callable]]:
    """주어진 컨텍스트에 맞는 Python 도구 스키마와 실행 함수를 반환합니다."""

    apply_filters = enable_group_filtering if enable_group_filtering is not None else ENABLE_GROUP_FILTERING
    normalized_group = (group_name or "").strip().lower() or None

    all_schemas: List[Dict[str, Any]] = []
    all_functions: Dict[str, Callable] = {}
    logger.info(
        f"Loading tools for context='{context}' group='{normalized_group}' filter={apply_filters}"
    )

    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if not filename.endswith("_map.py"):
                continue

            map_filepath = os.path.join(root, filename)
            try:
                map_spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                map_module = importlib.util.module_from_spec(map_spec)
                map_spec.loader.exec_module(map_module)

                tool_contexts = getattr(map_module, "tool_contexts", [])
                if context not in tool_contexts:
                    continue

                module_allowed_groups = {
                    g.strip().lower()
                    for g in getattr(map_module, "allowed_groups", [])
                    if isinstance(g, str) and g.strip()
                }
                raw_tool_group_map = getattr(map_module, "allowed_groups_by_tool", {}) or {}
                tool_allowed_groups: Dict[str, Set[str]] = {}
                for tool_name, groups in raw_tool_group_map.items():
                    if not isinstance(groups, (list, tuple, set)):
                        continue
                    lowered = {
                        str(item).strip().lower()
                        for item in groups
                        if isinstance(item, str) and str(item).strip()
                    }
                    if lowered:
                        tool_allowed_groups[tool_name] = lowered

                if apply_filters:
                    if normalized_group is None and module_allowed_groups:
                        logger.debug(
                            f"Skip map {map_filepath}: module-level groups defined but no group provided."
                        )
                        continue
                    if (
                        normalized_group is not None
                        and module_allowed_groups
                        and normalized_group not in module_allowed_groups
                    ):
                        logger.debug(
                            f"Skip map {map_filepath}: group '{normalized_group}' not allowed at module level."
                        )
                        continue

                tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                if not os.path.exists(tool_filepath):
                    logger.warning(
                        f"Map file {map_filepath} matched context, but tool file {tool_filepath} not found."
                    )
                    continue

                logger.info(
                    f"Map file {map_filepath} matches context '{context}'. Loading tools from {tool_filepath}"
                )

                tool_spec = importlib.util.spec_from_file_location("tool_module", tool_filepath)
                tool_module = importlib.util.module_from_spec(tool_spec)
                tool_spec.loader.exec_module(tool_module)

                if not (
                    hasattr(tool_module, "available_tools")
                    and hasattr(tool_module, "tool_functions")
                ):
                    continue

                available = getattr(tool_module, "available_tools")
                functions = getattr(tool_module, "tool_functions")

                for schema in available:
                    try:
                        fn = schema.get("function", {}) if isinstance(schema, dict) else {}
                        name = fn.get("name")
                        if not name:
                            continue

                        def _is_tool_allowed() -> bool:
                            if not apply_filters:
                                return True
                            allowed_for_tool = tool_allowed_groups.get(name)
                            if normalized_group is None:
                                if allowed_for_tool:
                                    return False
                                if module_allowed_groups:
                                    return False
                                return True
                            # group provided
                            if allowed_for_tool is not None:
                                return normalized_group in allowed_for_tool
                            if module_allowed_groups:
                                return normalized_group in module_allowed_groups
                            return True

                        if not _is_tool_allowed():
                            continue

                        all_schemas.append(schema)
                        if name in functions:
                            all_functions[name] = functions[name]
                    except Exception as e:
                        logger.debug(f"Skip tool due to error while filtering: {e}")

            except Exception as e:
                logger.error(f"Error processing map file {map_filepath}: {e}")

    logger.info(
        f"Found {len(all_schemas)} tools available for context='{context}' group='{normalized_group}'."
    )
    return all_schemas, all_functions

def find_langflow_tool(
    tool_name: str,
    context: Optional[str],
    group_name: Optional[str] = None,
    enable_group_filtering: Optional[bool] = None,
) -> Optional[LangFlow]:
    """
    LangFlow를 이름(엔드포인트)으로 조회하고, context가 주어지면 매핑 테이블로 사용 가능 여부를 확인합니다.
    """
    db: Session = SessionLocal()
    try:
        lf = db.query(LangFlow).filter(LangFlow.name == tool_name, LangFlow.is_active == True).first()
        if not lf:
            return None
        allowed, matched_group = _flow_allowed_in_context(
            db,
            lf,
            context,
            group_name,
            enable_group_filtering,
        )
        if not allowed:
            logger.info(
                "LangFlow '%s' not allowed for context='%s' group='%s' (flow_id=%s)",
                tool_name,
                context,
                group_name,
                lf.flow_id,
            )
            return None
        return lf
    except Exception as e:
        logger.error(f"Error finding LangFlow '{tool_name}' in database: {e}", exc_info=True)
        return None
    finally:
        db.close()

async def run_python_tool(tool_path: str, tool_input: Optional[Dict[str, Any]], state: "AgentState") -> Any:
    """
    주어진 경로의 Python 도구를 동적으로 로드하고 실행합니다.
    도구 파일에는 'run(tool_input, state)' 함수가 정의되어 있어야 합니다.
    """
    try:
        # 모듈 이름을 경로로부터 생성 (e.g., tools.coding_assistant.my_tool)
        module_name = os.path.splitext(os.path.relpath(tool_path, "."))[0].replace(os.path.sep, '.')
        
        spec = importlib.util.spec_from_file_location(module_name, tool_path)
        if spec is None:
            raise ImportError(f"Could not create module spec for {tool_path}")
            
        tool_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = tool_module
        spec.loader.exec_module(tool_module)

        # 도구 모듈에 'run' 함수가 있는지 확인
        if hasattr(tool_module, 'run') and callable(getattr(tool_module, 'run')):
            logger.info(f"Executing run() function in {tool_path}")
            # 'run' 함수 실행. tool_input이 없으면 None을 전달하며, 이 경우 run 함수 내부에서
            # state 정보를 바탕으로 필요한 입력을 파싱해야 합니다.
            return await getattr(tool_module, 'run')(tool_input, state)
        else:
            raise AttributeError(f"Tool module at {tool_path} does not have a callable 'run' function.")

    except Exception as e:
        logger.error(f"Failed to execute Python tool at {tool_path}: {e}", exc_info=True)
        # 에러 발생 시, 사용자에게 보여줄 수 있는 형태로 에러 메시지 반환
        return {"error": f"An error occurred while running the tool: {str(e)}"}

async def run_langflow_tool(langflow: LangFlow, tool_input: Optional[Dict[str, Any]], state: "AgentState") -> Any:
    """
    찾아낸 LangFlow 도구를 실행합니다.
    """
    try:
        # LangFlow의 엔드포인트(name)를 사용하여 실행 URL 구성
        endpoint_name = langflow.name
        execution_url = f"{LANGFLOW_BASE_URL}/flows/run/{endpoint_name}"

        # TODO: tool_input이 없으면 state['history']에서 정보를 추출하는 로직 구현
        # 현재는 tool_input이 있는 경우만 가정합니다.
        if tool_input is None:
            # 이 부분은 추후 자연어 처리 등을 통해 입력값을 동적으로 생성해야 합니다.
            logger.warning("tool_input is missing for LangFlow tool. This needs to be implemented.")
            # 임시로 빈 입력을 전달하거나, 에러를 반환할 수 있습니다.
            request_body = {"user_input": ""} # 또는 다른 기본값
        else:
            request_body = {"user_input": tool_input}

        logger.info(f"Calling LangFlow execution endpoint: {execution_url}")
        async with httpx.AsyncClient() as client:
            response = await client.post(execution_url, json=request_body, timeout=300.0)
            response.raise_for_status()  # 4xx, 5xx 에러 발생 시 예외 처리
            payload = response.json()

        # LangFlow의 응답은 종종 outputs/outputs[0]/artifacts 등의 중첩 구조를 가집니다.
        # 사용자가 보기 쉬운 1차 메시지로 정제한 뒤 assistant 메시지 형태로 감쌉니다.
        outputs: Any = payload
        if isinstance(payload, dict):
            if "outputs" in payload:
                outputs = payload["outputs"]
            elif "result" in payload:
                outputs = payload["result"]

        content = _format_flow_outputs_for_chat(outputs)
        logger.debug(
            "LangFlow '%s' responded with payload=%s | formatted=%s",
            endpoint_name,
            payload,
            content,
        )
        return {"messages": [{"role": "assistant", "content": content}]}

    except httpx.RequestError as e:
        logger.error(f"HTTP request to LangFlow failed: {e}", exc_info=True)
        return {"error": f"Failed to connect to LangFlow service: {str(e)}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"LangFlow service returned an error: {e.response.status_code} {e.response.text}", exc_info=True)
        return {"error": f"LangFlow service error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        logger.error(f"Failed to execute LangFlow '{langflow.name}': {e}", exc_info=True)
        return {"error": f"An unexpected error occurred while running the LangFlow tool: {str(e)}"}


# --- Description-driven auto routing for LangFlow ---

def _normalize_text(s: str) -> str:
    return s.strip()


_KO_STOPWORDS = {
    "그리고", "그러면", "그러나", "만", "만에", "만은", "경우", "단어", "단어가",
    "포함", "포함된", "수행", "하면", "하는", "만", "답변", "합니다", "하세요",
    "경우에", "만", "그", "이", "저", "것", "등", "또는", "또", "때문에"
}

_EN_STOPWORDS = {
    "the", "and", "or", "if", "when", "then", "only", "case", "word", "include",
    "includes", "included", "perform", "do", "answer"
}


def _extract_keywords_from_description(desc: Optional[str]) -> List[str]:
    """Extract meaningful tokens or phrases from description.

    Strategy:
    1) Prefer quoted phrases ("...").
    2) If none, fall back to content words (Korean/English) of reasonable length, minus stopwords.
    """
    if not desc:
        return []

    # 1) quoted phrases first
    patterns = [r'"([^"]+)"', r"'([^']+)'", r'“([^”]+)”', r'‘([^’]+)’']
    quoted: List[str] = []
    for pat in patterns:
        quoted.extend(re.findall(pat, desc))
    quoted = [_normalize_text(q) for q in quoted if _normalize_text(q)]
    if quoted:
        # dedupe preserve order
        seen = set()
        out: List[str] = []
        for q in quoted:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return out

    # 2) fallback: tokenize description to keywords
    # Split by non-word but keep Korean chars
    tokens_raw = re.split(r"[^0-9A-Za-z가-힣_]+", desc)
    tokens: List[str] = []
    for t in tokens_raw:
        t = t.strip()
        if not t:
            continue
        low = t.lower()
        # filter short/common tokens
        is_korean = bool(re.search(r"[가-힣]", t))
        if is_korean:
            if len(t) < 2 or t in _KO_STOPWORDS:
                continue
        else:
            if len(low) < 3 or low in _EN_STOPWORDS:
                continue
        tokens.append(t)

    # dedupe while preserving order
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _flow_allowed_in_context(
    db: Session,
    flow: LangFlow,
    context: Optional[str],
    group_name: Optional[str],
    enable_group_filtering: Optional[bool] = None,
) -> Tuple[bool, bool]:
    """Return (allowed, matched_group_specific)."""

    if not context:
        return True, False

    apply_filters = enable_group_filtering if enable_group_filtering is not None else ENABLE_GROUP_FILTERING
    normalized_group = (group_name or "").strip().lower() or None

    mappings = db.query(LangflowToolMapping).filter(
        LangflowToolMapping.flow_id == flow.flow_id,
        LangflowToolMapping.context == context,
    ).all()

    if not mappings:
        return False, False

    if not apply_filters:
        return True, False

    if normalized_group is not None:
        for mapping in mappings:
            group_val = (mapping.group_name or "").strip().lower() or None
            if group_val is not None and group_val == normalized_group:
                return True, True
        for mapping in mappings:
            if mapping.group_name is None:
                return True, False
        return False, False

    # No group provided: only allow public mappings (group_name IS NULL)
    for mapping in mappings:
        if mapping.group_name is None:
            return True, False
    return False, False


async def maybe_execute_best_tool_by_description(
    user_text: str, context: Optional[str], state: "AgentState"
) -> Optional[Dict[str, Any]]:
    """Evaluate both Python tools and LangFlow flows using the same description-matching rule,
    pick the highest scoring candidate, and execute it. Logs info-level reasons for skips.
    """
    if not user_text:
        logger.info("[AUTO-ROUTE] Skip: empty user_text")
        return None

    ctx = context or ""
    utext = user_text or ""
    group_name = None
    if isinstance(state, dict):
        group_name = state.get("group_name")

    apply_filters = ENABLE_GROUP_FILTERING

    # 1) Evaluate Python tools in context
    py_candidates: List[Tuple[int, str, Callable, str]] = []  # (score, name, fn, matched_kw)
    schemas, functions = get_available_tools_for_context(ctx, group_name, apply_filters)
    py_schema_index: Dict[str, Dict[str, Any]] = {}
    logger.info(f"[AUTO-ROUTE] Evaluating Python tools for context='{ctx}' (count={len(schemas)})")
    for sch in schemas:
        try:
            func = sch.get("function", {}) if isinstance(sch, dict) else {}
            name = func.get("name")
            desc = func.get("description") or sch.get("description")
            if not name:
                logger.info("[AUTO-ROUTE][PY] Skip: schema has no function name")
                continue
            if isinstance(sch, dict):
                py_schema_index[name] = sch
            if not desc:
                logger.info(f"[AUTO-ROUTE][PY] Skip '{name}': no description")
                continue
            kws = _extract_keywords_from_description(desc)
            if not kws:
                logger.info(f"[AUTO-ROUTE][PY] Skip '{name}': no keywords extracted from description")
                continue
            best_kw = None
            best_score = 0
            for kw in kws:
                if kw in utext:
                    score = max(1, len(kw))
                    if score > best_score:
                        best_kw = kw
                        best_score = score
            if not best_kw:
                logger.info(f"[AUTO-ROUTE][PY] Skip '{name}': no keyword matched in user_text; kws={kws}")
                continue
            tool_fn = functions.get(name)
            if not tool_fn:
                logger.info(f"[AUTO-ROUTE][PY] Skip '{name}': function not found in registry")
                continue
            logger.info(f"[AUTO-ROUTE][PY] Candidate '{name}' matched_kw='{best_kw}' score={best_score}")
            py_candidates.append((best_score, name, tool_fn, best_kw))
        except Exception as e:
            logger.info(f"[AUTO-ROUTE][PY] Skip schema due to error: {e}")

    # 2) Evaluate LangFlow flows
    flow_candidates: List[Tuple[int, LangFlow, str]] = []  # (score, flow, matched_kw)
    db: Session = SessionLocal()
    try:
        flows = LangFlowService.get_all_flows(db)
        logger.info(f"[AUTO-ROUTE] Evaluating Flows (count={len(flows)}) for context='{ctx}'")
        for f in flows:
            if not getattr(f, "is_active", True):
                logger.info(f"[AUTO-ROUTE][FLOW] Skip '{getattr(f,'name',None)}': inactive")
                continue
            allowed, matched_group = _flow_allowed_in_context(
                db,
                f,
                ctx,
                group_name,
                apply_filters,
            )
            if not allowed:
                logger.info(
                    f"[AUTO-ROUTE][FLOW] Skip '{f.name}': not allowed for context='{ctx}' group='{group_name}'"
                )
                continue
            kws = _extract_keywords_from_description(f.description)
            if not kws:
                logger.info(f"[AUTO-ROUTE][FLOW] Skip '{f.name}': no keywords extracted from description")
                continue
            best_kw = None
            best_score = 0
            for kw in kws:
                if kw in utext:
                    score = max(1, len(kw))
                    if score > best_score:
                        best_kw = kw
                        best_score = score
            if not best_kw:
                logger.info(f"[AUTO-ROUTE][FLOW] Skip '{f.name}': no keyword matched in user_text; kws={kws}")
                continue
            bonus = 1000 if matched_group else 0
            score_with_priority = best_score + bonus
            logger.info(
                f"[AUTO-ROUTE][FLOW] Candidate '{f.name}' matched_kw='{best_kw}' score={best_score} bonus={bonus}"
            )
            flow_candidates.append((score_with_priority, f, best_kw))
    finally:
        db.close()

    # 3) Pick the best among all candidates
    best: Optional[Tuple[str, int, str, Any]] = None  # (source, score, matched_kw, payload)

    for score, name, fn, kw in py_candidates:
        if best is None or score > best[1]:
            best = ("python", score, kw, (name, fn))

    for score, flow, kw in flow_candidates:
        if best is None or score > best[1]:
            best = ("flow", score, kw, flow)

    if best is None:
        logger.info("[AUTO-ROUTE] No candidates matched. Falling back to LLM.")
        return None

    source, score, matched_kw, payload = best
    logger.info(f"[AUTO-ROUTE] Selected '{source}' candidate with score={score}, kw='{matched_kw}'")

    # 4) Execute selected candidate
    if source == "python":
        name, fn = payload
        try:
            # Let the LLM infer arguments for the selected tool using its schema
            args = await _llm_generate_tool_arguments(py_schema_index.get(name) or {}, utext)
            result = await fn(args, state)
            content = _format_tool_result_for_chat(result)
        except Exception as e:
            content = f"도구 실행 중 오류가 발생했습니다: {e}"
        return {"role": "assistant", "content": content}

    # Flow
    flow: LangFlow = payload
    flow_data = LangFlowService.get_flow_data_as_dict(flow)
    # Provide a broad set of common input aliases used across flows
    inputs = {
        "input_value": user_text,
        "message": user_text,
        "input": user_text,
        "text": user_text,
        "chat_input": user_text,
        "user_question": user_text,
        "prompt": user_text,
    }
    exec_result = await langflow_service.execute_flow(flow_data, inputs)

    if exec_result.success:
        outputs = exec_result.outputs or {}
        content = _format_flow_outputs_for_chat(outputs)
    else:
        content = f"LangFlow 실행 중 오류가 발생했습니다: {exec_result.error}"
    return {"role": "assistant", "content": content}


async def maybe_execute_best_tool_by_llm(
    user_text: str, context: Optional[str], state: "AgentState"
) -> Optional[Dict[str, Any]]:
    """Use LLM intent analysis to pick the best tool/flow.

    Prompts the LLM with user_text and candidate list to choose one.
    Returns assistant message with execution result, or None if no suitable tool.
    """
    if not user_text:
        logger.info("[AUTO-ROUTE][LLM] Skip: empty user_text")
        return None

    ctx = context or ""
    group_name = None
    if isinstance(state, dict):
        group_name = state.get("group_name")

    apply_filters = ENABLE_GROUP_FILTERING

    # Collect Python tool candidates
    schemas, functions = get_available_tools_for_context(ctx, group_name, apply_filters)
    py_candidates: List[Dict[str, str]] = []
    py_schema_index: Dict[str, Dict[str, Any]] = {}
    for sch in schemas:
        try:
            func = sch.get("function", {}) if isinstance(sch, dict) else {}
            name = func.get("name")
            desc = func.get("description") or sch.get("description")
            if not name or not desc:
                continue
            if isinstance(sch, dict):
                py_schema_index[name] = sch
            d = str(desc)
            if len(d) > AUTO_ROUTE_MAX_DESC_CHARS:
                d = d[:AUTO_ROUTE_MAX_DESC_CHARS] + "…"
            py_candidates.append({"type": "python", "name": name, "description": d})
        except Exception:
            continue

    # Collect Flow candidates allowed in context
    db: Session = SessionLocal()
    flow_candidates: List[Dict[str, str]] = []
    flow_index: Dict[str, LangFlow] = {}
    try:
        for f in LangFlowService.get_all_flows(db):
            if not getattr(f, "is_active", True):
                continue
            allowed, matched_group = _flow_allowed_in_context(
                db,
                f,
                ctx,
                group_name,
                apply_filters,
            )
            if not allowed:
                continue
            desc = getattr(f, "description", None) or ""
            if len(desc) > AUTO_ROUTE_MAX_DESC_CHARS:
                desc = desc[:AUTO_ROUTE_MAX_DESC_CHARS] + "…"
            nm = getattr(f, "name", None)
            if not nm:
                continue
            visibility = "group" if matched_group else "public"
            flow_candidates.append(
                {"type": "flow", "name": nm, "description": str(desc), "visibility": visibility}
            )
            flow_index[nm] = f
    finally:
        db.close()

    candidates = py_candidates + flow_candidates
    if not candidates:
        logger.info("[AUTO-ROUTE][LLM] No candidates available in context; fallback to LLM")
        return None

    # Cap candidate list to reduce token usage
    if len(candidates) > AUTO_ROUTE_MAX_CANDIDATES:
        logger.info(
            f"[AUTO-ROUTE][LLM] Capping candidates {len(candidates)} -> {AUTO_ROUTE_MAX_CANDIDATES}"
        )
        candidates = candidates[:AUTO_ROUTE_MAX_CANDIDATES]

    # Build prompt for selection
    system = (
        "You are a strict tool router. Your task is to choose exactly one best candidate (a Python tool or a Flow) that can solve the user's request, or return null when none fits."
        "\nRules:" 
        "\n- Obey the provided context restrictions implicitly (candidates are already filtered)."
        "\n- Prefer semantic fit and specificity over generic matches."
        "\n- If multiple seem plausible, pick the one whose description most directly addresses the user's intent."
        "\n- If no candidate clearly applies, return null."
        "\nOutput strictly JSON only with this schema: {\"pick\": {\"type\": \"python|flow\", \"name\": string} | null}."
    )
    user = (
        "Decide now. Return ONLY the JSON object (no extra text).\n"
        f"User input: {user_text}\n"
        f"Context: {ctx or '-'}\n"
        f"Candidates: {candidates}"
    )

    llm = default_llm_client  # AsyncOpenAI
    try:
        completion = await llm.chat.completions.create(
            model=AUTO_ROUTE_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=256,
        )
        content = completion.choices[0].message.content or ""
        import json as _json
        data = None
        try:
            data = _json.loads(content)
        except Exception:
            # try to extract JSON blob
            import re as _re
            m = _re.search(r"\{.*\}", content, _re.S)
            if m:
                data = _json.loads(m.group(0))
        if not data or data.get("pick") in (None, "none"):
            logger.info(f"[AUTO-ROUTE][LLM] Model declined to pick. content={content!r}")
            return None
        pick = data.get("pick", {})
        ptype = pick.get("type")
        pname = pick.get("name")
        logger.info(f"[AUTO-ROUTE][LLM] Picked type='{ptype}' name='{pname}'")

        if ptype == "python":
            fn = functions.get(pname)
            if not fn:
                logger.info(f"[AUTO-ROUTE][LLM] Picked python tool not found: {pname}")
                return None
            try:
                # Ask LLM to produce arguments according to the tool schema
                args = await _llm_generate_tool_arguments(py_schema_index.get(pname) or {}, user_text)
                result = await fn(args, state)
                msg = _format_tool_result_for_chat(result)
            except Exception as e:
                msg = f"도구 실행 중 오류가 발생했습니다: {e}"
            return {"role": "assistant", "content": msg}

        if ptype == "flow":
            fl = flow_index.get(pname)
            if not fl:
                logger.info(f"[AUTO-ROUTE][LLM] Picked flow not found: {pname}")
                return None
            flow_data = LangFlowService.get_flow_data_as_dict(fl)
            inputs = {"input_value": user_text, "message": user_text}
            exec_result = await langflow_service.execute_flow(flow_data, inputs)
            if exec_result.success:
                outputs = exec_result.outputs or {}
                msg = _format_flow_outputs_for_chat(outputs)
            else:
                msg = f"LangFlow 실행 중 오류가 발생했습니다: {exec_result.error}"
            return {"role": "assistant", "content": msg}

        logger.info(f"[AUTO-ROUTE][LLM] Unknown pick type: {ptype}")
        return None
    except Exception as e:
        logger.info(f"[AUTO-ROUTE][LLM] Selection error: {e}")
        return None


async def maybe_execute_best_tool(
    user_text: str, context: Optional[str], state: "AgentState"
) -> Optional[Dict[str, Any]]:
    """Strategy switch for auto-routing.

    AUTO_ROUTE_STRATEGY=llm|text (default llm). Falls back to text if LLM returns None.
    """
    strategy = AUTO_ROUTE_STRATEGY
    if strategy == "off":
        return None
    if strategy == "llm":
        picked = await maybe_execute_best_tool_by_llm(user_text, context, state)
        if picked is not None:
            return picked
        # Optionally fall back to description-based routing
        if AUTO_ROUTE_LLM_FALLBACK:
            return await maybe_execute_best_tool_by_description(user_text, context, state)
        logger.info("[AUTO-ROUTE] LLM-only mode; skipping text fallback.")
        return None
    # text strategy
    return await maybe_execute_best_tool_by_description(user_text, context, state)
