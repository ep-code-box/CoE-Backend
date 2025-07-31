#!/usr/bin/env python3
"""데이터베이스 연결 및 기능 테스트 스크립트"""

from database import init_database, test_connection
from db_service import LangFlowService, DatabaseService
from database import SessionLocal

def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("=== 데이터베이스 연결 테스트 ===")
    
    # 데이터베이스 초기화
    if init_database():
        print("✅ 데이터베이스 초기화 성공")
    else:
        print("❌ 데이터베이스 초기화 실패")
        return False
    
    return True

def test_langflow_service():
    """LangFlow 서비스 테스트"""
    print("\n=== LangFlow 서비스 테스트 ===")
    
    db = SessionLocal()
    try:
        # 테스트 플로우 데이터
        test_flow_data = {
            "data": {
                "nodes": [
                    {"id": "1", "type": "input", "data": {"label": "Input"}},
                    {"id": "2", "type": "output", "data": {"label": "Output"}}
                ],
                "edges": [
                    {"id": "e1", "source": "1", "target": "2"}
                ]
            }
        }
        
        # 1. 플로우 생성 테스트
        print("1. 플로우 생성 테스트...")
        try:
            flow = LangFlowService.create_flow(
                db=db,
                name="test_flow",
                flow_data=test_flow_data,
                description="테스트 플로우"
            )
            print(f"✅ 플로우 생성 성공: ID={flow.id}, Name={flow.name}")
        except Exception as e:
            print(f"❌ 플로우 생성 실패: {e}")
            return False
        
        # 2. 플로우 조회 테스트
        print("2. 플로우 조회 테스트...")
        try:
            retrieved_flow = LangFlowService.get_flow_by_name(db, "test_flow")
            if retrieved_flow:
                print(f"✅ 플로우 조회 성공: {retrieved_flow.name}")
            else:
                print("❌ 플로우 조회 실패: 플로우를 찾을 수 없음")
                return False
        except Exception as e:
            print(f"❌ 플로우 조회 실패: {e}")
            return False
        
        # 3. 모든 플로우 목록 조회 테스트
        print("3. 플로우 목록 조회 테스트...")
        try:
            all_flows = LangFlowService.get_all_flows(db)
            print(f"✅ 플로우 목록 조회 성공: {len(all_flows)}개 플로우 발견")
        except Exception as e:
            print(f"❌ 플로우 목록 조회 실패: {e}")
            return False
        
        # 4. 플로우 업데이트 테스트
        print("4. 플로우 업데이트 테스트...")
        try:
            updated_flow = LangFlowService.update_flow(
                db=db,
                name="test_flow",
                description="업데이트된 테스트 플로우"
            )
            if updated_flow:
                print(f"✅ 플로우 업데이트 성공: {updated_flow.description}")
            else:
                print("❌ 플로우 업데이트 실패")
                return False
        except Exception as e:
            print(f"❌ 플로우 업데이트 실패: {e}")
            return False
        
        # 5. 플로우 삭제 테스트
        print("5. 플로우 삭제 테스트...")
        try:
            success = LangFlowService.delete_flow(db, "test_flow")
            if success:
                print("✅ 플로우 삭제 성공")
            else:
                print("❌ 플로우 삭제 실패")
                return False
        except Exception as e:
            print(f"❌ 플로우 삭제 실패: {e}")
            return False
        
        return True
        
    finally:
        db.close()

def test_database_service():
    """데이터베이스 서비스 테스트"""
    print("\n=== 데이터베이스 서비스 테스트 ===")
    
    db = SessionLocal()
    try:
        # 1. 테이블 정보 조회 테스트
        print("1. 테이블 정보 조회 테스트...")
        try:
            table_info = DatabaseService.get_table_info(db)
            print(f"✅ 테이블 정보 조회 성공: {len(table_info)}개 테이블 발견")
            for table in table_info:
                print(f"   - {table['table_name']}: {table['row_count']}행, {len(table['columns'])}개 컬럼")
        except Exception as e:
            print(f"❌ 테이블 정보 조회 실패: {e}")
            return False
        
        # 2. 쿼리 실행 테스트
        print("2. 쿼리 실행 테스트...")
        try:
            result = DatabaseService.execute_query(db, "SELECT COUNT(*) as total FROM langflows")
            print(f"✅ 쿼리 실행 성공: {result}")
        except Exception as e:
            print(f"❌ 쿼리 실행 실패: {e}")
            return False
        
        return True
        
    finally:
        db.close()

def main():
    """메인 테스트 함수"""
    print("🧪 CoE 백엔드 데이터베이스 테스트 시작\n")
    
    # 1. 데이터베이스 연결 테스트
    if not test_database_connection():
        print("\n❌ 데이터베이스 연결 테스트 실패")
        return
    
    # 2. LangFlow 서비스 테스트
    if not test_langflow_service():
        print("\n❌ LangFlow 서비스 테스트 실패")
        return
    
    # 3. 데이터베이스 서비스 테스트
    if not test_database_service():
        print("\n❌ 데이터베이스 서비스 테스트 실패")
        return
    
    print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()