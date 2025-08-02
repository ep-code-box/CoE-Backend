"""
LangFlow 실행 서비스
pip으로 설치된 langflow 라이브러리를 직접 사용하여 플로우를 실행합니다.
"""

import os
import time
import json
import tempfile
import asyncio
from typing import Dict, Any, Optional
from core.schemas import ExecuteFlowResponse
from core.database import SessionLocal
from services.db_service import LangFlowService


class LangFlowExecutionService:
    """LangFlow 실행을 담당하는 서비스 클래스"""
    
    def __init__(self, langflow_url: str = None):
        """
        LangFlow 서비스 초기화
        
        Args:
            langflow_url: 호환성을 위해 유지 (실제로는 사용하지 않음)
        """
        # 호환성을 위해 유지하지만 실제로는 사용하지 않음
        self.langflow_url = langflow_url or os.getenv("LANGFLOW_URL", "http://localhost:7860")
        self.api_key = os.getenv("LANGFLOW_API_KEY")  # 선택적 API 키
        
        # langflow 라이브러리 import
        try:
            from langflow.load import run_flow_from_json
            self.run_flow_from_json = run_flow_from_json
            self._langflow_available = True
        except ImportError as e:
            print(f"Warning: langflow library not available: {e}")
            self._langflow_available = False
        
    async def execute_flow_by_name(
        self, 
        flow_name: str, 
        inputs: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        저장된 플로우 이름으로 LangFlow 실행
        
        Args:
            flow_name: 실행할 플로우 이름
            inputs: 플로우 입력 데이터
            tweaks: 플로우 파라미터 조정
            
        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        
        if not self._langflow_available:
            return ExecuteFlowResponse(
                success=False,
                error="LangFlow library is not available",
                execution_time=time.time() - start_time
            )
        
        try:
            # 데이터베이스에서 플로우 조회
            db = SessionLocal()
            try:
                db_flow = LangFlowService.get_flow_by_name(db, flow_name)
                if not db_flow:
                    return ExecuteFlowResponse(
                        success=False,
                        error=f"Flow '{flow_name}' not found in database"
                    )
                
                # 플로우 데이터 파싱
                flow_data = json.loads(db_flow.flow_data)
                
            finally:
                db.close()
            
            # LangFlow 라이브러리로 직접 실행
            result = await self._execute_flow_direct(flow_data, inputs, tweaks)
            result.execution_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            return ExecuteFlowResponse(
                success=False,
                error=f"Error executing flow '{flow_name}': {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def execute_flow_by_id(
        self, 
        flow_id: str, 
        inputs: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        플로우 ID로 LangFlow 실행 (호환성을 위해 유지)
        
        Args:
            flow_id: LangFlow 플로우 ID
            inputs: 플로우 입력 데이터
            tweaks: 플로우 파라미터 조정
            
        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        
        if not self._langflow_available:
            return ExecuteFlowResponse(
                success=False,
                error="LangFlow library is not available",
                execution_time=time.time() - start_time
            )
        
        try:
            # 데이터베이스에서 flow_id로 플로우 찾기
            db = SessionLocal()
            try:
                # flow_id로 플로우 검색 (flow_data에서 id 필드 확인)
                flows = LangFlowService.get_all_flows(db)
                target_flow = None
                
                for flow in flows:
                    flow_data = json.loads(flow.flow_data)
                    if flow_data.get("id") == flow_id:
                        target_flow = flow_data
                        break
                
                if not target_flow:
                    return ExecuteFlowResponse(
                        success=False,
                        error=f"Flow with ID '{flow_id}' not found",
                        execution_time=time.time() - start_time
                    )
                
            finally:
                db.close()
            
            # LangFlow 라이브러리로 직접 실행
            result = await self._execute_flow_direct(target_flow, inputs, tweaks)
            result.execution_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            return ExecuteFlowResponse(
                success=False,
                error=f"Error executing flow with ID '{flow_id}': {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _execute_flow_direct(
        self,
        flow_data: Dict[str, Any],
        inputs: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        LangFlow 라이브러리를 사용하여 플로우를 직접 실행
        
        Args:
            flow_data: 플로우 JSON 데이터
            inputs: 플로우 입력 데이터
            tweaks: 플로우 파라미터 조정
            
        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        
        try:
            # 임시 파일에 플로우 데이터 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(flow_data, f)
                temp_file = f.name
            
            try:
                # 입력값 준비
                input_value = ""
                if inputs:
                    input_value = inputs.get("input_value", inputs.get("message", ""))
                
                # 비동기 실행을 위해 별도 스레드에서 실행
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._run_flow_sync,
                    temp_file,
                    input_value,
                    tweaks
                )
                
                return ExecuteFlowResponse(
                    success=True,
                    session_id=f"direct-{int(time.time())}",
                    outputs={"result": result, "text": str(result)},
                    execution_time=time.time() - start_time
                )
                
            finally:
                # 임시 파일 삭제
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            return ExecuteFlowResponse(
                success=False,
                error=f"Direct execution error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _run_flow_sync(self, flow_file: str, input_value: str, tweaks: Optional[Dict[str, Any]] = None):
        """
        동기적으로 플로우 실행 (executor에서 호출됨)
        """
        try:
            # tweaks 처리
            kwargs = {"fallback_to_env_vars": True}
            if tweaks:
                kwargs.update(tweaks)
            
            # 플로우 실행
            result = self.run_flow_from_json(
                flow=flow_file,
                input_value=input_value,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            raise Exception(f"Flow execution failed: {str(e)}")
    
    async def check_langflow_health(self) -> bool:
        """
        LangFlow 라이브러리 상태 확인
        
        Returns:
            bool: 라이브러리가 사용 가능하면 True
        """
        return self._langflow_available
    
    def get_langflow_url(self) -> str:
        """현재 설정된 LangFlow URL 반환 (호환성을 위해 유지)"""
        return self.langflow_url


# 전역 서비스 인스턴스
langflow_service = LangFlowExecutionService()