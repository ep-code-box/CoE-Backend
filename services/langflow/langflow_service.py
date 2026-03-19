"""
LangFlow 실행 서비스
내부 LangFlow 라이브러리를 사용하여 플로우를 직접 실행합니다.
"""

import time
import inspect
import json as _json
import re
from typing import Dict, Any, Optional, List
from core.schemas import ExecuteFlowResponse

# ──────────────────────────────────────────────────────────────────────
# langflow ↔ lfx Message 클래스 호환 패치
# ──────────────────────────────────────────────────────────────────────
# 플로우 JSON 에 포함된 SKAX 에이전트 컴포넌트가 lfx.schema.message.Message 를
# 사용하고, langflow.memory.aadd_messages 는 langflow.schema.message.Message 의
# isinstance 체크를 수행합니다. 두 클래스는 기능적으로 동일하지만 서로 다른 모듈에서
# 로드되어 isinstance 검사에 실패하기 때문에, 좀 더 유연한 체크로 교체합니다.
# ──────────────────────────────────────────────────────────────────────
def _apply_langflow_message_compat_patch():
    """Monkey-patch langflow.memory.aadd_messages to accept lfx Message objects."""
    try:
        import langflow.memory as _lf_memory
        from langflow.schema.message import Message as LfMessage

        _original_aadd = _lf_memory.aadd_messages

        async def _patched_aadd_messages(messages, flow_id=None):
            if not isinstance(messages, list):
                messages = [messages]

            # 유연한 타입 체크: 클래스 이름이 'Message'이고 필요 속성을 갖추면 통과
            def _is_message_like(obj):
                if isinstance(obj, LfMessage):
                    return True
                # lfx.schema.message.Message 등 호환 타입 허용
                return (
                    type(obj).__name__ == "Message"
                    and hasattr(obj, "text")
                    and hasattr(obj, "sender")
                )

            if not all(_is_message_like(m) for m in messages):
                types = ", ".join([str(type(m)) for m in messages])
                msg = f"The messages must be instances of Message. Found: {types}"
                raise ValueError(msg)

            # 원래 함수의 isinstance 체크를 이미 통과시켰으므로,
            # 기존 로직의 나머지 부분을 직접 실행
            from langflow.services.database.models.message import MessageTable
            from langflow.services.deps import session_scope
            from langflow.memory import aadd_messagetables
            from langflow.logging.logger import logger

            try:
                from uuid import UUID

                def _normalize_message(m):
                    """lfx Message → langflow Message 호환 변환"""
                    # session_id가 UUID 객체이면 str로 변환
                    if hasattr(m, 'session_id') and isinstance(m.session_id, UUID):
                        try:
                            m.session_id = str(m.session_id)
                        except Exception:
                            pass
                    # flow_id도 마찬가지
                    if hasattr(m, 'flow_id') and isinstance(m.flow_id, UUID):
                        try:
                            m.flow_id = str(m.flow_id)
                        except Exception:
                            pass
                    # id 필드도
                    if hasattr(m, 'id') and isinstance(getattr(m, 'id', None), UUID):
                        try:
                            m.id = str(m.id)
                        except Exception:
                            pass
                    # lfx Message가 아닌 langflow Message로 변환 시도
                    if not isinstance(m, LfMessage):
                        try:
                            dump = m.model_dump() if hasattr(m, 'model_dump') else m.dict()
                            # UUID 값 일괄 문자열 변환
                            for k, v in dump.items():
                                if isinstance(v, UUID):
                                    dump[k] = str(v)
                            return LfMessage(**dump)
                        except Exception:
                            pass
                    return m

                normalized = [_normalize_message(m) for m in messages]
                messages_models = [MessageTable.from_message(m, flow_id=flow_id) for m in normalized]
                async with session_scope() as session:
                    messages_models = await aadd_messagetables(messages_models, session)
                return [await LfMessage.create(**mm.model_dump()) for mm in messages_models]
            except Exception as e:
                await logger.aexception(e)
                raise

        _lf_memory.aadd_messages = _patched_aadd_messages
    except ImportError:
        pass  # langflow 라이브러리 미설치 시 무시

_apply_langflow_message_compat_patch()

# LangFlow 실행 함수 호환 계층
# 다양한 LangFlow 버전에서 이름/경로가 바뀌어 import 에러가 날 수 있으므로
# 지연 임포트 + 다중 후보를 시도하고, 전부 실패하면 우아하게 에러를 반환합니다.
def _resolve_langflow_runner():
    try:
        # 구버전/일부 배포에서 제공
        from langflow.processing.process import process_graph_cached  # type: ignore

        def _runner(flow_data, inputs):
            # Introspect signature for maximum compatibility
            try:
                sig = inspect.signature(process_graph_cached)  # type: ignore
                params = list(sig.parameters.keys())
                kwargs = {}
                # flow graph parameter
                if 'data_graph' in params:
                    kwargs['data_graph'] = flow_data
                elif 'graph' in params:
                    kwargs['graph'] = flow_data
                elif params:
                    # fallback to first parameter by name
                    kwargs[params[0]] = flow_data
                # inputs parameter
                if 'inputs' in params:
                    kwargs['inputs'] = inputs or {}
                elif 'input' in params:
                    kwargs['input'] = inputs or {}
                elif 'input_dict' in params:
                    kwargs['input_dict'] = inputs or {}
                elif 'data' in params:
                    kwargs['data'] = inputs or {}
                return process_graph_cached(**kwargs)  # type: ignore
            except Exception:
                # last resort: positional
                return process_graph_cached(flow_data, inputs or {})  # type: ignore

        return _runner
    except Exception:
        pass

    try:
        # 비교적 최신 API에서 자주 보이는 진입점
        from langflow.load import run_flow_from_json  # type: ignore

        def _runner(flow_data, inputs):
            try:
                sig = inspect.signature(run_flow_from_json)  # type: ignore
                params = list(sig.parameters.keys())
                kwargs = {}
                # flow graph parameter
                if 'flow' in params:
                    kwargs['flow'] = flow_data
                elif 'data' in params:
                    kwargs['data'] = flow_data
                elif 'graph' in params:
                    kwargs['graph'] = flow_data
                elif params:
                    kwargs[params[0]] = flow_data
                # inputs parameter (try multiple names)
                if 'inputs' in params:
                    kwargs['inputs'] = inputs or {}
                elif 'input' in params:
                    kwargs['input'] = inputs or {}
                elif 'input_dict' in params:
                    kwargs['input_dict'] = inputs or {}
                elif 'input_value' in params:
                    # Some versions require a positional/keyword 'input_value'
                    # Provide a simple string if dict given
                    ival = inputs if isinstance(inputs, (str, bytes)) else (inputs or {}).get('input_value') or (inputs or {}).get('message') or (inputs or {}).get('user_input') or (inputs or {})
                    print(f"DEBUG: LangFlow inputs: {inputs}, extracted ival: {ival}")
                    kwargs['input_value'] = ival
                elif 'data' in params and 'flow' in kwargs:
                    # if data exists and not used for graph, use for inputs
                    kwargs['data'] = inputs or {}
                # tweaks if available
                if 'tweaks' in params and 'tweaks' not in kwargs:
                    kwargs['tweaks'] = None
                return run_flow_from_json(**kwargs)  # type: ignore
            except Exception:
                # fallback attempts with common patterns
                try:
                    return run_flow_from_json(flow=flow_data, input=inputs or {})  # type: ignore
                except Exception:
                    try:
                        # try input_value positional if function expects it
                        return run_flow_from_json(flow_data, (inputs or {}).get('input_value') or (inputs or {}).get('message') or (inputs or {}).get('user_input') or inputs or {})  # type: ignore
                    except Exception:
                        # last resort: flow only
                        return run_flow_from_json(flow=flow_data, input_value="")  # type: ignore

        return _runner
    except Exception:
        pass

    try:
        # 또 다른 위치 시도 (일부 분기)
        from langflow.processing.process import run_flow_from_json  # type: ignore

        def _runner(flow_data, inputs):
            try:
                sig = inspect.signature(run_flow_from_json)  # type: ignore
                params = list(sig.parameters.keys())
                kwargs = {}
                if 'flow' in params:
                    kwargs['flow'] = flow_data
                elif 'data' in params:
                    kwargs['data'] = flow_data
                elif 'graph' in params:
                    kwargs['graph'] = flow_data
                elif params:
                    kwargs[params[0]] = flow_data
                if 'inputs' in params:
                    kwargs['inputs'] = inputs or {}
                elif 'input' in params:
                    kwargs['input'] = inputs or {}
                elif 'input_dict' in params:
                    kwargs['input_dict'] = inputs or {}
                elif 'input_value' in params:
                    ival = inputs if isinstance(inputs, (str, bytes)) else (inputs or {}).get('input_value') or (inputs or {}).get('message') or (inputs or {}).get('user_input') or (inputs or {})
                    kwargs['input_value'] = ival
                if 'tweaks' in params and 'tweaks' not in kwargs:
                    kwargs['tweaks'] = None
                return run_flow_from_json(**kwargs)  # type: ignore
            except Exception:
                try:
                    return run_flow_from_json(flow=flow_data, input=inputs or {})  # type: ignore
                except Exception:
                    try:
                        return run_flow_from_json(flow_data, (inputs or {}).get('input_value') or (inputs or {}).get('message') or (inputs or {}).get('user_input') or inputs or {})  # type: ignore
                    except Exception:
                        return run_flow_from_json(flow=flow_data)  # type: ignore

        return _runner
    except Exception:
        pass

    # 전부 실패하면 None
    return None

class LangFlowExecutionService:
    """LangFlow 실행을 담당하는 서비스 클래스 (라이브러리 기반)"""

    def __init__(self):
        """
        LangFlow 서비스 초기화 (내부 실행)
        """
        # 라이브러리 기반 실행에서는 URL이나 API 키가 필요 없습니다.
        pass

    async def execute_flow(
        self,
        flow_data: Dict[str, Any],
        inputs: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        주어진 flow_data(JSON)를 LangFlow 라이브러리를 통해 직접 실행합니다.

        Args:
            flow_data: 실행할 플로우의 JSON 데이터
            inputs: 플로우 입력 데이터

        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        
        if not inputs:
            inputs = {}

        try:
            # Normalize common schema differences between LangFlow versions
            def _normalize_flow_payload(payload: Dict[str, Any]) -> None:
                try:
                    dg = payload.get("data") or {}
                    edges: List[Dict[str, Any]] = dg.get("edges") or []
                    normalized: List[Dict[str, Any]] = []
                    for e in edges:
                        if not isinstance(e, dict):
                            normalized.append(e)
                            continue
                        ne = dict(e)
                        data_block = ne.get("data") if isinstance(ne.get("data"), dict) else {}
                        # Move flat handles into nested data.sourceHandle/targetHandle with .id
                        src_h = ne.pop("sourceHandle", None)
                        tgt_h = ne.pop("targetHandle", None)
                        if src_h is not None and not isinstance(data_block.get("sourceHandle"), dict):
                            data_block["sourceHandle"] = {"id": src_h if isinstance(src_h, str) else src_h.get("id") if isinstance(src_h, dict) else src_h}
                        if tgt_h is not None and not isinstance(data_block.get("targetHandle"), dict):
                            data_block["targetHandle"] = {"id": tgt_h if isinstance(tgt_h, str) else tgt_h.get("id") if isinstance(tgt_h, dict) else tgt_h}

                        # Some exports embed JSON into the id string like '{…"dataType":"X"…}' possibly with custom quotes
                        def _inflate_handle(h: Any) -> Dict[str, Any]:
                            if isinstance(h, dict):
                                # If id contains an embedded JSON, try to parse and merge
                                _id = h.get("id")
                                if isinstance(_id, str) and ("dataType" in _id or _id.strip().startswith("{")):
                                    try:
                                        patched = _id.replace("œ", '"')
                                        parsed = _json.loads(patched)
                                        if isinstance(parsed, dict):
                                            # Merge parsed fields; keep original id if present
                                            merged = {**h, **parsed}
                                            # Ensure id is a simple string
                                            if not isinstance(merged.get("id"), (str, bytes)):
                                                merged["id"] = str(merged.get("id", ""))
                                            return merged
                                    except Exception:
                                        pass
                                # Ensure required fields exist
                                if "dataType" not in h:
                                    h["dataType"] = "Any"
                                return h
                            # If simple string, wrap
                            return {"id": str(h), "dataType": "Any"}

                        if isinstance(data_block.get("sourceHandle"), (dict, str)):
                            data_block["sourceHandle"] = _inflate_handle(data_block.get("sourceHandle"))
                        if isinstance(data_block.get("targetHandle"), (dict, str)):
                            data_block["targetHandle"] = _inflate_handle(data_block.get("targetHandle"))

                        ne["data"] = data_block
                        normalized.append(ne)
                    if edges and normalized:
                        dg["edges"] = normalized
                        payload["data"] = dg
                except Exception:
                    # best-effort normalization only
                    pass

            _normalize_flow_payload(flow_data)

            # SKAX 에이전트 노드의 BACKEND_BASE_URL을 localhost로 패치
            # coe-backend 컨테이너가 직접 플로우를 실행할 때,
            # 플로우 JSON에 하드코딩된 외부/크로스-컴포즈 URL
            # (예: http://coe-backend-coe-1:8000/v1) 은 자기 자신의 네트워크에서
            # 해석할 수 없으므로 localhost로 치환합니다.
            # (예: http://coe-backend-coe-1:8000/v1) 은 자기 자신의 네트워크에서
            # 해석할 수 없으므로 localhost로 치환합니다.
            # /v1/internal 경로를 사용하여 Agent 파이프라인(도구 로딩, Auto-Route 등)을
            # 건너뛰고 LLM API만 직접 호출하도록 합니다. (성능 최적화)
            import os
            _SELF_BACKEND_URL = os.getenv(
                "LANGFLOW_SELF_BACKEND_URL", "http://localhost:8000/v1/internal"
            )

            def _patch_skax_backend_url(payload: Any) -> Any:
                import json
                try:
                    # 입력값이 문자열이면 dict로 변환 시도
                    is_string_payload = isinstance(payload, str)
                    data_to_process = json.loads(payload) if is_string_payload else payload
                    
                    dumped = json.dumps(data_to_process, ensure_ascii=False)
                    print(f"=============================")
                    print(f"[LANGFLOW] DEBUG full payload type: {type(payload)}")
                    
                    import re
                    extracted_urls = set(re.findall(r"https?://[^\s\"'{}]+", dumped))
                    print(f"[LANGFLOW] DEBUG all URLs found in payload: {extracted_urls}")
                    print(f"=============================")
                    
                    targets = ["sk-axstudio.com", "coe-backend", "20.214.9.217", "greatcoe.cafe24.com"]
                    patched_count = 0
                    
                    for target in targets:
                        if target in dumped:
                            # 다양한 경로 패턴에 대응하는 무식하지만 명확한 문자열 치환
                            old_url_v1 = f'http://{target}/v1'
                            old_url_v1_s = f'https://{target}/v1'
                            if old_url_v1 in dumped:
                                dumped = dumped.replace(old_url_v1, _SELF_BACKEND_URL)
                                patched_count += 1
                            if old_url_v1_s in dumped:
                                dumped = dumped.replace(old_url_v1_s, _SELF_BACKEND_URL)
                                patched_count += 1
                                
                            # 포트가 명시된 경우
                            old_url_port = f'http://{target}:8000/v1'
                            if old_url_port in dumped:
                                dumped = dumped.replace(old_url_port, _SELF_BACKEND_URL)
                                patched_count += 1

                    if patched_count > 0:
                        print(f"[LANGFLOW] Successfully patched {patched_count} URL(s) to {_SELF_BACKEND_URL}")
                        new_payload = json.loads(dumped)
                        # 원본이 문자열이었으면 패치된 문자열로, 객체면 업데이트된 객체로 반환
                        if is_string_payload:
                            return json.dumps(new_payload, ensure_ascii=False)
                        else:
                            if isinstance(payload, dict):
                                payload.clear()
                                payload.update(new_payload)
                            return payload
                    else:
                        print("[LANGFLOW] No backend patterns found to patch in payload.")
                        return payload

                except Exception as e:
                    print(f"[LANGFLOW] Patch conversion error: {str(e)}")
                    return payload

            flow_data = _patch_skax_backend_url(flow_data)

            # 호환 가능한 LangFlow 러너 확인
            runner = _resolve_langflow_runner()
            if runner is None:
                raise ImportError(
                    "Compatible LangFlow entrypoint not found. "
                    "Tried: processing.process.process_graph_cached, load.run_flow_from_json. "
                    "Please pin a compatible 'langflow' version or update the integration."
                )

            text_field_pattern = re.compile(
                r"'text'\s*:\s*\"([^\"\\]*(?:\\.[^\"\\]*)*)\"",
                re.S,
            )

            def _decode_text_from_repr(raw: str) -> Optional[str]:
                """Attempt to extract a "text" value from repr strings."""
                try:
                    match = text_field_pattern.search(raw)
                    if match:
                        return match.group(1).strip()
                except Exception:
                    return None
                return None

            def _coerce_langflow_value(value: Any) -> Any:
                if isinstance(value, (str, bytes, dict, list)) or value is None:
                    return value

                for attr in ("model_dump", "dict", "to_dict"):
                    method = getattr(value, attr, None)
                    if callable(method):
                        try:
                            coerced = method()  # type: ignore[misc]
                            if coerced is not None:
                                return coerced
                        except TypeError:
                            try:
                                coerced = method(exclude_none=True)  # type: ignore[misc]
                                if coerced is not None:
                                    return coerced
                            except Exception:
                                pass
                        except Exception:
                            pass

                if hasattr(value, "__dict__"):
                    try:
                        return vars(value)
                    except TypeError:
                        pass

                if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    try:
                        return list(value)
                    except TypeError:
                        pass

                return value

            def _extract_text(obj: Any) -> Optional[str]:
                if obj is None:
                    return None

                coerced = _coerce_langflow_value(obj)

                if isinstance(coerced, bytes):
                    try:
                        coerced = coerced.decode("utf-8", "ignore")
                    except Exception:
                        coerced = coerced.decode(errors="ignore")

                if isinstance(coerced, str):
                    stripped = coerced.strip()
                    if not stripped:
                        return None
                    if "'text'" in stripped and "ResultData" in stripped:
                        decoded = _decode_text_from_repr(stripped)
                        if decoded:
                            return decoded
                    return stripped

                if isinstance(coerced, dict):
                    category = coerced.get("category")
                    entry_type = coerced.get("type")

                    if category == "message" or entry_type == "message":
                        for key in ("text", "message", "content", "value"):
                            val = coerced.get(key)
                            text_val = _extract_text(val)
                            if text_val:
                                return text_val
                        data_node = coerced.get("data")
                        text_val = _extract_text(data_node)
                        if text_val:
                            return text_val

                    if "data" in coerced:
                        data_node = coerced.get("data")
                        text_val = _extract_text(data_node)
                        if text_val:
                            return text_val

                    if entry_type == "dataframe" or (isinstance(coerced, dict) and "dataframe" in coerced):
                        dataframe = coerced.get("dataframe")
                        if dataframe is None and isinstance(coerced.get("data"), list):
                            dataframe = coerced.get("data")
                        if isinstance(dataframe, list):
                            for row in dataframe:
                                text_val = _extract_text(row)
                                if text_val:
                                    return text_val

                    for key in (
                        "text",
                        "message",
                        "content",
                        "output",
                        "result",
                        "value",
                        "artifacts",
                        "results",
                        "messages",
                        "outputs",
                        "data",
                        "logs",
                    ):
                        if key in coerced:
                            text_val = _extract_text(coerced[key])
                            if text_val:
                                return text_val

                    return None

                if isinstance(coerced, list):
                    for item in coerced:
                        text_val = _extract_text(item)
                        if text_val:
                            return text_val

                for attr in ("results", "messages", "outputs", "artifacts", "data"):
                    if hasattr(coerced, attr):
                        try:
                            text_val = _extract_text(getattr(coerced, attr))
                            if text_val:
                                return text_val
                        except Exception:
                            continue

                if hasattr(coerced, "text") and isinstance(getattr(coerced, "text"), str):
                    text_prop = getattr(coerced, "text").strip()
                    if text_prop:
                        return text_prop

                if hasattr(coerced, "message") and isinstance(getattr(coerced, "message"), str):
                    msg_prop = getattr(coerced, "message").strip()
                    if msg_prop:
                        return msg_prop

                return None

            # langflow 러너 실행
            result_data = runner(flow_data, inputs)
            
            # 실행 결과에서 실제 output 추출
            # LangFlow의 결과 구조에 따라 파싱 방식이 달라질 수 있습니다.
            outputs = {}
            # Common shapes
            if isinstance(result_data, dict):
                if "outputs" in result_data:
                    try:
                        outv = result_data.get("outputs")
                        if isinstance(outv, list) and outv:
                            candidate = outv[0]
                            if isinstance(candidate, dict):
                                outputs = candidate
                            else:
                                outputs = {"value": candidate}
                        elif isinstance(outv, dict):
                            outputs = outv
                    except Exception:
                        pass
                elif "result" in result_data:
                    outputs = result_data.get("result") or {}
            elif hasattr(result_data, 'outputs'):
                try:
                    outputs = result_data.outputs[0]
                except Exception:
                    outputs = {"value": getattr(result_data, 'outputs', None)}

            extracted_outputs_text = _extract_text(outputs)
            if extracted_outputs_text:
                outputs = {"text": extracted_outputs_text}
            else:
                fallback_text = _extract_text(result_data)
                if fallback_text:
                    outputs = {"text": fallback_text}
            # As a final fallback, serialize the entire result for visibility
            if not outputs or (isinstance(outputs, dict) and not outputs):
                try:
                    outputs = {"raw": _json.dumps(result_data, ensure_ascii=False, default=str)}
                except Exception:
                    outputs = {"raw": str(result_data)}


            return ExecuteFlowResponse(
                success=True,
                session_id=f"internal-{int(time.time())}",
                outputs=outputs,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            # 오류 발생 시, 스택 트레이스를 포함하여 로깅하는 것이 좋습니다.
            import traceback
            error_detail = f"LangFlow internal execution error: {str(e)}\n{traceback.format_exc()}"
            return ExecuteFlowResponse(success=False, error=error_detail, execution_time=time.time() - start_time)

# 전역 서비스 인스턴스
langflow_service = LangFlowExecutionService()
