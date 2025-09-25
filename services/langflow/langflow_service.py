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
                    ival = inputs if isinstance(inputs, (str, bytes)) else (inputs or {}).get('input_value') or (inputs or {}).get('message') or (inputs or {})
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
                        return run_flow_from_json(flow_data, (inputs or {}).get('input_value') or (inputs or {}).get('message') or inputs or {})  # type: ignore
                    except Exception:
                        # last resort: flow only
                        return run_flow_from_json(flow=flow_data)  # type: ignore

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
                    ival = inputs if isinstance(inputs, (str, bytes)) else (inputs or {}).get('input_value') or (inputs or {}).get('message') or (inputs or {})
                    kwargs['input_value'] = ival
                if 'tweaks' in params and 'tweaks' not in kwargs:
                    kwargs['tweaks'] = None
                return run_flow_from_json(**kwargs)  # type: ignore
            except Exception:
                try:
                    return run_flow_from_json(flow=flow_data, input=inputs or {})  # type: ignore
                except Exception:
                    try:
                        return run_flow_from_json(flow_data, (inputs or {}).get('input_value') or (inputs or {}).get('message') or inputs or {})  # type: ignore
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
