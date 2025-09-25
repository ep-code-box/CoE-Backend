"""
LangFlow 실행 서비스
내부 LangFlow 라이브러리를 사용하여 플로우를 직접 실행합니다.
"""

import time
import inspect
import json as _json
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

            # Heuristic: try to extract a primary text field if still empty
            def _find_text(obj):
                try:
                    if obj is None:
                        return None

                    if isinstance(obj, (str, bytes)):
                        text_val = obj.decode("utf-8", "ignore") if isinstance(obj, bytes) else obj
                        text_val = text_val.strip()
                        return text_val or None

                    if isinstance(obj, dict):
                        category = obj.get("category")
                        entry_type = obj.get("type")

                        if category == "message" or entry_type == "message":
                            direct = obj.get("text") or obj.get("message") or obj.get("content")
                            if isinstance(direct, str) and direct.strip():
                                return direct.strip()
                            data_block = obj.get("data")
                            if isinstance(data_block, dict):
                                data_text = data_block.get("text")
                                if isinstance(data_text, str) and data_text.strip():
                                    return data_text.strip()

                        if entry_type == "data" or "data" in obj:
                            data_node = obj.get("data", obj)
                            if isinstance(data_node, dict):
                                text_field = data_node.get("text")
                                if isinstance(text_field, str) and text_field.strip():
                                    return text_field.strip()
                            nested = _find_text(data_node)
                            if nested:
                                return nested

                        if entry_type == "dataframe" or (isinstance(obj, dict) and "dataframe" in obj):
                            dataframe = obj.get("dataframe")
                            if dataframe is None and isinstance(obj.get("data"), list):
                                dataframe = obj.get("data")
                            if isinstance(dataframe, list) and dataframe:
                                first_row = dataframe[0]
                                if isinstance(first_row, dict):
                                    row_text = first_row.get("text")
                                    if isinstance(row_text, str) and row_text.strip():
                                        return row_text.strip()
                                nested = _find_text(first_row)
                                if nested:
                                    return nested

                        for key in ("text", "content", "message", "output", "result"):
                            val = obj.get(key)
                            if isinstance(val, (str, bytes)) and val:
                                if isinstance(val, bytes):
                                    decoded = val.decode("utf-8", "ignore").strip()
                                    if decoded:
                                        return decoded
                                else:
                                    stripped = val.strip()
                                    if stripped:
                                        return stripped
                            nested = _find_text(val)
                            if nested:
                                return nested

                    if isinstance(obj, list):
                        for it in obj:
                            s = _find_text(it)
                            if s:
                                return s

                    for attr in ("results", "message", "text", "content"):
                        if hasattr(obj, attr):
                            val = getattr(obj, attr)
                            if isinstance(val, (str, bytes)):
                                decoded = val.decode("utf-8", "ignore") if isinstance(val, bytes) else val
                                if decoded.strip():
                                    return decoded.strip()
                            nested = _find_text(val)
                            if nested:
                                return nested

                    for method_name in ("model_dump", "dict", "to_dict"):
                        if hasattr(obj, method_name) and callable(getattr(obj, method_name)):
                            try:
                                data_obj = getattr(obj, method_name)()
                                nested = _find_text(data_obj)
                                if nested:
                                    return nested
                            except Exception:
                                pass

                    if hasattr(obj, "data"):
                        nested = _find_text(getattr(obj, "data"))
                        if nested:
                            return nested

                    if hasattr(obj, "__dict__"):
                        return _find_text(vars(obj))
                except Exception:
                    return None
                return None

            if not outputs or (isinstance(outputs, dict) and not outputs):
                primary = _find_text(result_data)
                if primary:
                    outputs = {"text": primary}
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
