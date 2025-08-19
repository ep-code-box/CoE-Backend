"""
LangFlow 실행 서비스
내부 LangFlow 라이브러리를 사용하여 플로우를 직접 실행합니다.
"""

import time
from typing import Dict, Any, Optional
from core.schemas import ExecuteFlowResponse
# from langflow.load import run_flow_from_json # 예상되는 langflow 임포트
from langflow.processing.process import process_graph_cached

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
            # langflow 라이브러리를 사용하여 그래프 데이터 처리
            # 실제 라이브러리 함수는 `process_graph_cached` 또는 유사한 형태일 수 있습니다.
            result_data = process_graph_cached(
                data_graph=flow_data,
                inputs=inputs
            )
            
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
