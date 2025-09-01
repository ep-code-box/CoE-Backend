from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

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
def get_database_service() -> DatabaseService:
    """DatabaseService 인스턴스를 반환합니다."""
    return DatabaseService()