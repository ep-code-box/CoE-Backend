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

    # 1) Evaluate Python tools in context
    py_candidates: List[Tuple[int, str, Callable, str]] = []  # (score, name, fn, matched_kw)
    schemas, functions = get_available_tools_for_context(ctx)
    logger.info(f"[AUTO-ROUTE] Evaluating Python tools for context='{ctx}' (count={len(schemas)})")
    for sch in schemas:
        try:
            func = sch.get("function", {}) if isinstance(sch, dict) else {}
            name = func.get("name")
            desc = func.get("description") or sch.get("description")
            if not name:
                logger.info("[AUTO-ROUTE][PY] Skip: schema has no function name")
                continue
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
            if not _flow_allowed_in_context(db, f, ctx):
                logger.info(
                    f"[AUTO-ROUTE][FLOW] Skip '{f.name}': not allowed in context '{ctx}'"
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
            logger.info(f"[AUTO-ROUTE][FLOW] Candidate '{f.name}' matched_kw='{best_kw}' score={best_score}")
            flow_candidates.append((best_score, f, best_kw))
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
            result = await fn(None, state)
            content = (
                f"✅ 자동 라우팅: Tool '{name}' 실행됨 (키워드: '{matched_kw}', 점수: {score})\n\n"
                f"결과:\n{result}"
            )
        except Exception as e:
            content = (
                f"❌ 자동 라우팅 실패: Tool '{name}' 실행 중 오류\n\n"
                f"오류: {e}"
            )
        return {"role": "assistant", "content": content}

    # Flow
    flow: LangFlow = payload
    flow_data = LangFlowService.get_flow_data_as_dict(flow)
    inputs = {"input_value": user_text, "message": user_text}
    exec_result = await langflow_service.execute_flow(flow_data, inputs)

    if exec_result.success:
        outputs = exec_result.outputs or {}
        content = (
            f"✅ 자동 라우팅: LangFlow '{flow.name}' 실행됨 (키워드: '{matched_kw}', 점수: {score})\n\n"
            f"출력:\n{outputs}"
        )
    else:
        content = (
            f"❌ 자동 라우팅 실패: LangFlow '{flow.name}' 실행 중 오류\n\n"
            f"오류: {exec_result.error}"
        )
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

    # Collect Python tool candidates
    schemas, functions = get_available_tools_for_context(ctx)
    py_candidates: List[Dict[str, str]] = []
    for sch in schemas:
        try:
            func = sch.get("function", {}) if isinstance(sch, dict) else {}
            name = func.get("name")
            desc = func.get("description") or sch.get("description")
            if not name or not desc:
                continue
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
            if not _flow_allowed_in_context(db, f, ctx):
                continue
            desc = getattr(f, "description", None) or ""
            if len(desc) > AUTO_ROUTE_MAX_DESC_CHARS:
                desc = desc[:AUTO_ROUTE_MAX_DESC_CHARS] + "…"
            nm = getattr(f, "name", None)
            if not nm:
                continue
            flow_candidates.append({"type": "flow", "name": nm, "description": str(desc)})
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
                result = await fn(None, state)
                msg = (
                    f"✅ 자동 라우팅(의도분석): Tool '{pname}' 실행 완료\n\n결과:\n{result}"
                )
            except Exception as e:
                msg = (
                    f"❌ 자동 라우팅(의도분석) 실패: Tool '{pname}' 실행 오류\n\n오류: {e}"
                )
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
                msg = (
                    f"✅ 자동 라우팅(의도분석): LangFlow '{pname}' 실행 완료\n\n출력:\n{outputs}"
                )
            else:
                msg = (
                    f"❌ 자동 라우팅(의도분석) 실패: LangFlow '{pname}' 실행 오류\n\n오류: {exec_result.error}"
                )
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
    if strategy == "llm":
        picked = await maybe_execute_best_tool_by_llm(user_text, context, state)
        if picked is not None:
            return picked
        # Fallback to text if no LLM pick
        return await maybe_execute_best_tool_by_description(user_text, context, state)
    # text strategy
    return await maybe_execute_best_tool_by_description(user_text, context, state)
