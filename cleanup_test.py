from database import SessionLocal
from db_service import LangFlowService

db = SessionLocal()
try:
    success = LangFlowService.delete_flow(db, 'test_flow')
    if success:
        print('✅ Deleted existing test_flow')
    else:
        print('ℹ️ No test_flow to delete')
except Exception as e:
    print(f'❌ Error: {e}')
finally:
    db.close()