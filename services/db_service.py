import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from core.database import LangFlow
from datetime import datetime

class LangFlowService:
    """LangFlow 데이터베이스 서비스 클래스"""
    
    @staticmethod
    def create_flow(db: Session, name: str, flow_data: Dict[str, Any], flow_id: str, description: Optional[str] = None) -> LangFlow:
        """새로운 LangFlow를 생성합니다."""
        try:
            # JSON 데이터를 문자열로 변환
            flow_data_str = json.dumps(flow_data, ensure_ascii=False, indent=2)
            
            db_flow = LangFlow(
                name=name,
                description=description,
                flow_data=flow_data_str,
                flow_id=flow_id
            )
            
            db.add(db_flow)
            db.commit()
            db.refresh(db_flow)
            
            return db_flow
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Flow with name '{name}' already exists")
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create flow: {str(e)}")
    
    @staticmethod
    def get_flow_by_name(db: Session, name: str) -> Optional[LangFlow]:
        """이름으로 LangFlow를 조회합니다."""
        return db.query(LangFlow).filter(LangFlow.name == name, LangFlow.is_active).first()
    
    @staticmethod
    def get_flow_by_id(db: Session, flow_id: int) -> Optional[LangFlow]:
        """ID로 LangFlow를 조회합니다."""
        return db.query(LangFlow).filter(LangFlow.id == flow_id, LangFlow.is_active).first()
    
    @staticmethod
    def get_all_flows(db: Session) -> List[LangFlow]:
        """모든 활성 LangFlow를 조회합니다."""
        return db.query(LangFlow).filter(LangFlow.is_active).order_by(LangFlow.created_at.desc()).all()
    
    @staticmethod
    def update_flow(db: Session, name: str, flow_data: Optional[Dict[str, Any]] = None, 
                   description: Optional[str] = None) -> Optional[LangFlow]:
        """LangFlow를 업데이트합니다."""
        try:
            db_flow = LangFlowService.get_flow_by_name(db, name)
            if not db_flow:
                return None
            
            if flow_data is not None:
                db_flow.flow_data = json.dumps(flow_data, ensure_ascii=False, indent=2)
            
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
        try:
            return json.loads(flow.flow_data)
        except json.JSONDecodeError:
            return {}

class DatabaseService:
    """일반적인 데이터베이스 관리 서비스 클래스"""
    
    @staticmethod
    def get_table_info(db: Session) -> List[Dict[str, Any]]:
        """데이터베이스의 테이블 정보를 조회합니다."""
        try:
            result = db.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            
            table_info = []
            for table in tables:
                # 테이블 구조 정보 조회
                result = db.execute(text(f"DESCRIBE {table}"))
                columns = result.fetchall()
                
                # 테이블 행 수 조회
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                row_count = result.fetchone()[0]
                
                table_info.append({
                    "table_name": table,
                    "columns": [
                        {
                            "field": col[0],
                            "type": col[1],
                            "null": col[2],
                            "key": col[3],
                            "default": col[4],
                            "extra": col[5]
                        } for col in columns
                    ],
                    "row_count": row_count
                })
            
            return table_info
        except Exception as e:
            raise Exception(f"Failed to get table info: {str(e)}")
    
    @staticmethod
    def execute_query(db: Session, query: str) -> Dict[str, Any]:
        """SQL 쿼리를 실행합니다 (SELECT만 허용)."""
        try:
            # 보안을 위해 SELECT 쿼리만 허용
            if not query.strip().upper().startswith('SELECT'):
                raise ValueError("Only SELECT queries are allowed")
            
            result = db.execute(text(query))
            
            # 결과가 있는 경우
            if result.returns_rows:
                columns = result.keys()
                rows = result.fetchall()
                
                return {
                    "columns": list(columns),
                    "rows": [list(row) for row in rows],
                    "row_count": len(rows)
                }
            else:
                return {
                    "message": "Query executed successfully",
                    "affected_rows": result.rowcount
                }
        except Exception as e:
            raise Exception(f"Failed to execute query: {str(e)}")

# 편의 함수들
def get_langflow_service() -> LangFlowService:
    """LangFlowService 인스턴스를 반환합니다."""
    return LangFlowService()

def get_database_service() -> DatabaseService:
    """DatabaseService 인스턴스를 반환합니다."""
    return DatabaseService()