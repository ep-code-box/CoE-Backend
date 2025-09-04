import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from core.database import LangFlow
from datetime import datetime

class LangFlowService:
    """LangFlow 데이터베이스 서비스 클래스"""
    
    @staticmethod
    def create_flow(db: Session, name: str, flow_data: Dict[str, Any], flow_id: str, description: Optional[str] = None) -> LangFlow:
        """새로운 LangFlow를 생성하거나 기존 LangFlow를 업데이트합니다."""
        try:
            # flow_id로 기존 LangFlow 조회
            existing_flow = db.query(LangFlow).filter(LangFlow.flow_id == flow_id).first()

            # flow_data_str = json.dumps(flow_data, ensure_ascii=False, indent=2) # SQLAlchemy JSON type handles serialization

            if existing_flow:
                # 기존 LangFlow 업데이트
                existing_flow.name = name
                existing_flow.description = description
                existing_flow.flow_data = flow_data
                existing_flow.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing_flow)
                return existing_flow
            else:
                # 새로운 LangFlow 생성
                db_flow = LangFlow(
                    name=name,
                    description=description,
                    flow_data=flow_data,
                    flow_id=flow_id,
                    is_active=True,
                )
                db.add(db_flow)
                db.commit()
                db.refresh(db_flow)
                return db_flow
        except IntegrityError as e:
            db.rollback()
            # Duplicate entry for 'ix_langflows_flow_id' or 'ix_langflows_name'
            if "ix_langflows_flow_id" in str(e):
                raise ValueError(f"Flow with ID '{flow_id}' already exists.")
            elif "ix_langflows_name" in str(e):
                raise ValueError(f"Flow with name '{name}' already exists.")
            else:
                raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create or update flow: {str(e)}")
    
    @staticmethod
    def get_flow_by_name(db: Session, name: str) -> Optional[LangFlow]:
        """이름으로 LangFlow를 조회합니다."""
        return db.query(LangFlow).filter(LangFlow.name == name, LangFlow.is_active == True).first()
    
    @staticmethod
    def get_flow_by_id(db: Session, flow_id: int) -> Optional[LangFlow]:
        """ID로 LangFlow를 조회합니다."""
        return db.query(LangFlow).filter(LangFlow.id == flow_id, LangFlow.is_active == True).first()
    
    @staticmethod
    def get_all_flows(db: Session) -> List[LangFlow]:
        """모든 활성 LangFlow를 조회합니다. (is_active가 NULL인 레거시 데이터도 포함)"""
        from sqlalchemy import or_, true
        return (
            db.query(LangFlow)
            .filter(or_(LangFlow.is_active == True, LangFlow.is_active.is_(None)))
            .order_by(LangFlow.created_at.desc())
            .all()
        )
    
    @staticmethod
    def update_flow(db: Session, name: str, flow_data: Optional[Dict[str, Any]] = None, 
                   description: Optional[str] = None) -> Optional[LangFlow]:
        """LangFlow를 업데이트합니다."""
        try:
            db_flow = LangFlowService.get_flow_by_name(db, name)
            if not db_flow:
                return None
            
            if flow_data is not None:
                db_flow.flow_data = flow_data
            
            if description is not None:
                db_flow.description = description
            
            db_flow.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_flow)
            
            return db_flow
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update flow: {str(e)}")
    
    @staticmethod
    def delete_flow(db: Session, name: str) -> bool:
        """LangFlow를 이름으로 삭제합니다 (소프트 삭제)."""
        try:
            db_flow = LangFlowService.get_flow_by_name(db, name)
            if not db_flow:
                return False
            
            db_flow.is_active = False
            db_flow.updated_at = datetime.utcnow()
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to delete flow: {str(e)}")

    @staticmethod
    def delete_flow_by_id(db: Session, flow_id: int) -> Optional[LangFlow]:
        """LangFlow를 ID로 삭제합니다 (소프트 삭제)."""
        try:
            db_flow = LangFlowService.get_flow_by_id(db, flow_id)
            if not db_flow:
                return None
            
            db_flow.is_active = False
            db_flow.updated_at = datetime.utcnow()
            
            db.commit()
            return db_flow
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to delete flow by ID: {str(e)}")
    
    @staticmethod
    def get_flow_data_as_dict(flow: LangFlow) -> Dict[str, Any]:
        """LangFlow의 flow_data를 딕셔너리로 반환합니다."""
        # flow.flow_data는 이미 SQLAlchemy에 의해 딕셔너리로 로드됩니다.
        return flow.flow_data

# 편의 함수들
def get_langflow_service() -> LangFlowService:
    """LangFlowService 인스턴스를 반환합니다."""
    return LangFlowService()
