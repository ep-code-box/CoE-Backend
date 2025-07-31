import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "6667")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "acce")
DB_NAME = os.getenv("DB_NAME", "coe_db")

# MariaDB 연결 URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# LangFlow 테이블 모델
class LangFlow(Base):
    __tablename__ = "langflows"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    flow_data = Column(Text, nullable=False)  # JSON 데이터를 문자열로 저장
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# RAG Pipeline 분석 결과 테이블 모델
class RagAnalysisResult(Base):
    __tablename__ = "rag_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(255), unique=True, index=True, nullable=False)
    git_url = Column(String(500), index=True, nullable=False)  # Git URL을 키로 사용
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False)  # 분석일자
    status = Column(String(50), nullable=False)  # pending, running, completed, failed
    repository_count = Column(Integer, default=0)
    total_files = Column(Integer, default=0)
    total_lines_of_code = Column(Integer, default=0)
    
    # 분석 결과 데이터 (JSON 형태로 저장)
    repositories_data = Column(Text, nullable=True)  # RepositoryAnalysis 목록을 JSON으로 저장
    correlation_data = Column(Text, nullable=True)   # CorrelationAnalysis를 JSON으로 저장
    tech_specs_summary = Column(Text, nullable=True) # 기술스펙 요약을 JSON으로 저장
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 인덱스 추가
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )

# 데이터베이스 테이블 생성
def create_tables():
    """데이터베이스 테이블을 생성합니다."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 데이터베이스 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류 발생: {e}")

# 데이터베이스 세션 의존성
def get_db():
    """데이터베이스 세션을 반환합니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 연결 테스트
def test_connection():
    """데이터베이스 연결을 테스트합니다."""
    try:
        # 먼저 데이터베이스 없이 연결 테스트
        test_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
        test_engine = create_engine(test_url)
        
        with test_engine.connect() as connection:
            # 데이터베이스 생성
            from sqlalchemy import text
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            print(f"✅ 데이터베이스 '{DB_NAME}' 생성/확인 완료")
        
        # 이제 실제 데이터베이스에 연결
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ MariaDB 연결 성공!")
            return True
    except Exception as e:
        print(f"❌ MariaDB 연결 실패: {e}")
        return False

# 데이터베이스 초기화
def init_database():
    """데이터베이스를 초기화합니다."""
    print("🔄 데이터베이스 초기화 중...")
    
    # 연결 테스트
    if not test_connection():
        return False
    
    # 테이블 생성
    create_tables()
    return True