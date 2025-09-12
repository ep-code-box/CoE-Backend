"""
Front-end에서 요청된 도구를 찾아 실행하고, 그 결과를 반환하는 서비스입니다.
"""
import os
import sys
import importlib.util
from typing import Dict, Any, Optional, List, Tuple, Callable
import re
import logging
import httpx

from sqlalchemy.orm import Session
from core.database import LangFlow, LangflowToolMapping, SessionLocal
from services.db_langflow_service import LangFlowService
from services.langflow.langflow_service import langflow_service

logger = logging.getLogger(__name__)

# 도구가 위치한 기본 디렉토리
TOOLS_BASE_DIR = "tools"
# LangFlow 실행을 위한 기본 URL
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:8000")

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
    langflow = find_langflow_tool(tool_name, ctx)
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

def get_available_tools_for_context(context: str) -> Tuple[List[Dict[str, Any]], Dict[str, Callable]]:
    """
    주어진 컨텍스트(_map.py 기준)에 맞는, LLM이 사용할 수 있는 도구의 스키마와 함수를 반환합니다.
    """
    all_schemas = []
    all_functions = {}
    logger.info(f"Loading tools for context: '{context}'")

    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_map.py"):
                map_filepath = os.path.join(root, filename)
                try:
                    map_spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                    map_module = importlib.util.module_from_spec(map_spec)
                    map_spec.loader.exec_module(map_module)

                    tool_contexts = getattr(map_module, 'tool_contexts', [])

                    if context in tool_contexts:
                        tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                        if os.path.exists(tool_filepath):
                            logger.info(f"Map file {map_filepath} matches context '{context}'. Loading tools from {tool_filepath}")
                            
                            tool_spec = importlib.util.spec_from_file_location("tool_module", tool_filepath)
                            tool_module = importlib.util.module_from_spec(tool_spec)
                            tool_spec.loader.exec_module(tool_module)

                            if hasattr(tool_module, 'available_tools') and hasattr(tool_module, 'tool_functions'):
                                all_schemas.extend(getattr(tool_module, 'available_tools'))
                                all_functions.update(getattr(tool_module, 'tool_functions'))
                        else:
                            logger.warning(f"Map file {map_filepath} matched context, but tool file {tool_filepath} not found.")

                except Exception as e:
                    logger.error(f"Error processing map file {map_filepath}: {e}")

    # LangFlow 도구는 별도의 매핑 테이블로 컨텍스트 제한을 적용합니다 (실행 시 검사).
    logger.info(f"Found {len(all_schemas)} tools available for context '{context}'.")
    return all_schemas, all_functions

def find_langflow_tool(tool_name: str, context: Optional[str]) -> Optional[LangFlow]:
    """
    LangFlow를 이름(엔드포인트)으로 조회하고, context가 주어지면 매핑 테이블로 사용 가능 여부를 확인합니다.
    """
    db: Session = SessionLocal()
    try:
        lf = db.query(LangFlow).filter(LangFlow.name == tool_name, LangFlow.is_active == True).first()
        if not lf:
            return None
        if context:
            allowed = db.query(LangflowToolMapping).filter(
                LangflowToolMapping.flow_id == lf.flow_id,
                LangflowToolMapping.context == context
            ).first()
            if not allowed:
                logger.info(
                    "LangFlow '%s' not allowed for context '%s' (flow_id=%s)",
                    tool_name,
                    context,
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
            response.raise_for_status() # 4xx, 5xx 에러 발생 시 예외 처리
            return response.json()

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


def _flow_allowed_in_context(db: Session, flow: LangFlow, context: Optional[str]) -> bool:
    if not context:
        return True
    allowed = db.query(LangflowToolMapping).filter(
        LangflowToolMapping.flow_id == flow.flow_id,
        LangflowToolMapping.context == context,
    ).first()
    return allowed is not None


async def maybe_execute_flow_by_description(user_text: str, context: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    If any active flow's description contains quoted keywords that appear in user_text,
    execute the best-matching flow and return an assistant message dict. Else None.
    """
    if not user_text:
        return None

    db: Session = SessionLocal()
    try:
        flows = LangFlowService.get_all_flows(db)
        candidates: List[Tuple[int, LangFlow, str]] = []
        utext = user_text or ""
        for f in flows:
            if not getattr(f, "is_active", True):
                continue
            if not _flow_allowed_in_context(db, f, context):
                continue
            best_kw = None
            best_score = 0
            for kw in _extract_keywords_from_description(f.description):
                if not kw:
                    continue
                if kw in utext:
                    # weight by length to favor specific phrases
                    score = max(1, len(kw))
                    if score > best_score:
                        best_kw = kw
                        best_score = score
            if best_kw:
                candidates.append((best_score, f, best_kw))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, sel, matched_kw = candidates[0]

        flow_data = LangFlowService.get_flow_data_as_dict(sel)
        inputs = {"input_value": user_text, "message": user_text}
        exec_result = await langflow_service.execute_flow(flow_data, inputs)

        if exec_result.success:
            outputs = exec_result.outputs or {}
            content = (
                f"✅ 자동 라우팅: LangFlow '{sel.name}' 실행됨 (키워드: '{matched_kw}')\n\n"
                f"출력:\n{outputs}"
            )
        else:
            content = (
                f"❌ 자동 라우팅 실패: LangFlow '{sel.name}' 실행 중 오류\n\n"
                f"오류: {exec_result.error}"
            )

        return {"role": "assistant", "content": content}
    finally:
        db.close()


async def maybe_execute_python_tool_by_description(
    user_text: str, context: Optional[str], state: "AgentState"
) -> Optional[Dict[str, Any]]:
    """Description-based auto selection among Python tools available in the context.

    Uses the same keyword extraction and scoring rule as flows. If matched, executes
    the tool function and returns an assistant message dict. Otherwise returns None.
    """
    if not user_text:
        return None

    ctx = context or ""
    schemas, functions = get_available_tools_for_context(ctx)
    if not schemas:
        return None

    candidates: List[Tuple[int, Dict[str, Any], str]] = []  # (score, schema, keyword)
    for sch in schemas:
        try:
            func = sch.get("function", {}) if isinstance(sch, dict) else {}
            name = func.get("name")
            desc = func.get("description") or sch.get("description")
            if not name or not desc:
                continue
            best_kw = None
            best_score = 0
            for kw in _extract_keywords_from_description(desc):
                if kw and kw in user_text:
                    score = max(1, len(kw))
                    if score > best_score:
                        best_kw = kw
                        best_score = score
            if best_kw:
                candidates.append((best_score, sch, best_kw))
        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, sel_schema, matched_kw = candidates[0]
    sel_name = sel_schema["function"]["name"]
    tool_fn = functions.get(sel_name)
    if not tool_fn:
        return None

    try:
        result = await tool_fn(None, state)  # let tool parse from state if needed
        content = (
            f"✅ 자동 라우팅: Tool '{sel_name}' 실행됨 (키워드: '{matched_kw}')\n\n"
            f"결과:\n{result}"
        )
    except Exception as e:
        content = (
            f"❌ 자동 라우팅 실패: Tool '{sel_name}' 실행 중 오류\n\n"
            f"오류: {e}"
        )

    return {"role": "assistant", "content": content}
