"""
LangFlow 실행 서비스
내부 LangFlow 라이브러리를 사용하여 플로우를 직접 실행합니다.
"""

import time
import inspect
from typing import Dict, Any, Optional
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
            if isinstance(result_data, dict) and "outputs" in result_data:
                 outputs = result_data.get("outputs", [{}])[0]
            elif hasattr(result_data, 'outputs'):
                 outputs = result_data.outputs[0]


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
