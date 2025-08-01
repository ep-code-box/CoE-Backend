"""
LangFlow 관련 API 엔드포인트들을 담당하는 모듈입니다.
"""

import json
import os
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from core.schemas import SaveFlowRequest, FlowListResponse
from core.database import get_db
from services.db_service import LangFlowService

router = APIRouter()


@router.post("/flows/save")
async def save_flow(req: SaveFlowRequest, db: Session = Depends(get_db)):
    """LangFlow JSON을 데이터베이스에 저장합니다."""
    try:
        # 데이터베이스에 저장
        flow = LangFlowService.create_flow(
            db=db,
            name=req.name,
            description=req.description,
            flow_data=req.flow_data.model_dump()
        )
        
        # 백워드 호환성을 위해 파일로도 저장 (선택적)
        flows_dir = "flows"
        os.makedirs(flows_dir, exist_ok=True)
        
        safe_name = "".join(c for c in req.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_name}.json"
        filepath = os.path.join(flows_dir, filename)
        
        flow_data = req.flow_data.model_dump()
        flow_data["saved_name"] = req.name
        if req.description:
            flow_data["description"] = req.description
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(flow_data, f, indent=2, ensure_ascii=False)
        
        return {
            "message": f"Flow '{req.name}' saved successfully to database",
            "id": flow.id,
            "filename": filename,
            "created_at": flow.created_at.isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save flow: {str(e)}")


@router.get("/flows/list", response_model=FlowListResponse)
async def list_flows(db: Session = Depends(get_db)):
    """저장된 LangFlow 목록을 데이터베이스에서 반환합니다."""
    try:
        # 데이터베이스에서 조회
        db_flows = LangFlowService.get_all_flows(db)
        
        flows = []
        for flow in db_flows:
            flows.append({
                "name": flow.name,
                "id": str(flow.id),
                "description": flow.description or "",
                "filename": f"{flow.name}.json",
                "created_at": flow.created_at.isoformat(),
                "updated_at": flow.updated_at.isoformat()
            })
        
        return FlowListResponse(flows=flows)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list flows: {str(e)}")


@router.get("/flows/{flow_name}")
async def get_flow(flow_name: str, db: Session = Depends(get_db)):
    """특정 LangFlow JSON을 데이터베이스에서 반환합니다."""
    try:
        # 먼저 이름으로 찾기
        flow = LangFlowService.get_flow_by_name(db, flow_name)
        
        # 이름으로 찾지 못하면 ID로 찾기 (숫자인 경우)
        if not flow and flow_name.isdigit():
            flow = LangFlowService.get_flow_by_id(db, int(flow_name))
        
        if not flow:
            raise HTTPException(status_code=404, detail=f"Flow '{flow_name}' not found")
        
        # JSON 데이터 파싱
        flow_data = json.loads(flow.flow_data)
        
        # 메타데이터 추가
        flow_data.update({
            "id": flow.id,
            "saved_name": flow.name,
            "description": flow.description,
            "created_at": flow.created_at.isoformat(),
            "updated_at": flow.updated_at.isoformat(),
            "is_active": flow.is_active
        })
        
        return flow_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get flow: {str(e)}")


@router.delete("/flows/{flow_name}")
async def delete_flow(flow_name: str, db: Session = Depends(get_db)):
    """저장된 LangFlow를 데이터베이스에서 삭제합니다."""
    try:
        # 데이터베이스에서 삭제
        success = LangFlowService.delete_flow(db, flow_name)
        
        if not success:
            # ID로도 시도해보기 (숫자인 경우)
            if flow_name.isdigit():
                flow = LangFlowService.get_flow_by_id(db, int(flow_name))
                if flow:
                    success = LangFlowService.delete_flow(db, flow.name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Flow '{flow_name}' not found")
        
        # 백워드 호환성을 위해 파일도 삭제 시도 (에러 무시)
        try:
            flows_dir = "flows"
            safe_name = "".join(c for c in flow_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}.json"
            filepath = os.path.join(flows_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass  # 파일 삭제 실패는 무시
        
        return {"message": f"Flow '{flow_name}' deleted successfully from database"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete flow: {str(e)}")