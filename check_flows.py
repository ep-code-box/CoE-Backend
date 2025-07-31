from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(text('SELECT * FROM langflows'))
    rows = result.fetchall()
    print(f'Found {len(rows)} flows in database')
    for row in rows:
        print(f'  - ID: {row[0]}, Name: {row[1]}, Active: {row[6]}')
        
    # 모든 비활성 플로우 삭제
    if rows:
        db.execute(text('DELETE FROM langflows WHERE name = "test_flow"'))
        db.commit()
        print('Deleted test_flow records')
finally:
    db.close()