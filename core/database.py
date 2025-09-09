import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey, Enum, DECIMAL, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import enum
import redis

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "coe_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "coe_password")
DB_NAME = os.getenv("DB_NAME", "coe_db")

# MariaDB 연결 URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 및 세션 설정 (최적화)
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # 프로덕션에서는 False로 설정
    pool_pre_ping=True, 
    pool_recycle=300,
    pool_size=10,  # 연결 풀 크기
    max_overflow=20,  # 최대 오버플로우 연결 수
    pool_timeout=30,  # 연결 대기 시간
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis 클라이언트 설정
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_AUTH_DB", 1))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    db=REDIS_DB, 
    password=REDIS_PASSWORD, 
    decode_responses=True
)

# Enum 정의
class AnalysisStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RepositoryStatus(enum.Enum):
    PENDING = "PENDING"
    CLONING = "CLONING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DependencyType(enum.Enum):
    FRAMEWORK = "FRAMEWORK"
    LIBRARY = "LIBRARY"
    TOOL = "TOOL"
    LANGUAGE = "LANGUAGE"

class DocumentType(enum.Enum):
    README = "README"
    API_DOC = "API_DOC"
    WIKI = "WIKI"
    CHANGELOG = "CHANGELOG"
    CONTRIBUTING = "CONTRIBUTING"
    OTHER = "OTHER"

class SourceType(enum.Enum):
    CODE = "CODE"
    DOCUMENT = "DOCUMENT"
    AST_NODE = "AST_NODE"

class StandardType(enum.Enum):
    CODING_STYLE = "CODING_STYLE"
    ARCHITECTURE_PATTERN = "ARCHITECTURE_PATTERN"
    COMMON_FUNCTIONS = "COMMON_FUNCTIONS"
    BEST_PRACTICES = "BEST_PRACTICES"

class HTTPMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

# 데이터베이스 모델 정의



# LangFlow 테이블 모델
class LangFlow(Base):
    __tablename__ = "langflows"
    extend_existing=True
    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    flow_data = Column(JSON, nullable=False)  # JSON 데이터를 문자열로 저장
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 관계 설정 (여러 컨텍스트 매핑 가능)
    tool_mappings = relationship("LangflowToolMapping", back_populates="flow", uselist=True)

class LangflowToolMapping(Base):
    __tablename__ = "langflow_tool_mappings"
    extend_existing=True
    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(String(255), ForeignKey('langflows.flow_id'), nullable=False)
    # 어떤 프론트(context)에서 사용 가능한지 표시 (ex: 'aider', 'openWebUi')
    context = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    flow = relationship("LangFlow", back_populates="tool_mappings")


# 데이터베이스 모델 정의

class APILog(Base):
    __tablename__ = "api_logs"
    extend_existing=True
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100))
    endpoint = Column(String(255), nullable=False)
    method = Column(Enum(HTTPMethod), nullable=False)
    request_data = Column(JSON)
    response_status = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 도구 관련 필드 추가
    selected_tool = Column(String(100), nullable=True)  # 선택된 도구명
    tool_execution_time_ms = Column(Integer, nullable=True)  # 도구 실행 시간
    tool_success = Column(Boolean, nullable=True)  # 도구 실행 성공 여부
    tool_error_message = Column(Text, nullable=True)  # 도구 실행 오류 메시지

# 채팅 메시지 히스토리 테이블
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    extend_existing=True
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    turn_number = Column(Integer, nullable=False)
    
    # 도구 관련 메타데이터
    selected_tool = Column(String(100), nullable=True)  # 이 메시지와 관련된 선택된 도구
    tool_execution_time_ms = Column(Integer, nullable=True)  # 도구 실행 시간
    tool_success = Column(Boolean, nullable=True)  # 도구 실행 성공 여부
    tool_metadata = Column(JSON, nullable=True)  # 도구 실행 관련 추가 메타데이터

# 대화 요약 테이블
class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    extend_existing=True
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False)
    summary_content = Column(Text, nullable=False)
    total_turns = Column(Integer, default=0)
    tools_used = Column(JSON, nullable=True)  # 사용된 도구들의 목록과 통계
    group_name = Column(String(255), nullable=True) # group_name 컬럼 추가
    created_at = Column(DateTime, default=datetime.utcnow)

# 데이터베이스 테이블 생성
def create_tables():
    """데이터베이스에 모든 테이블을 생성합니다."""
    print("🔄 데이터베이스 테이블 생성을 시작합니다...")
    try:
        # Base에 정의된 모든 테이블을 생성
        Base.metadata.create_all(bind=engine)
        print("✅ 모든 데이터베이스 테이블이 성공적으로 확인 또는 생성되었습니다.")
        
        # (선택 사항) 각 테이블 생성 여부 확인 로그
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        print(f"🔍 현재 데이터베이스에 존재하는 테이블: {table_names}")
        
    except Exception as e:
        print(f"❌ 테이블 생성 중 심각한 오류 발생: {e}")

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

# 데이터베이스 초기화 상태 추적 (테이블 확인)
def _is_database_initialized():
    """데이터베이스가 이미 초기화되었는지 확인합니다."""
    try:
        inspector = inspect(engine)
        # 주요 테이블이 있는지 확인
        # Backend에서 필수로 사용하는 테이블 기준으로 축소
        # Include langflows-related tables to ensure LangFlow features work
        required_tables = {'chat_messages', 'conversation_summaries', 'langflows'}
        existing_tables = set(inspector.get_table_names())
        print(f"🔍 현재 데이터베이스에 존재하는 테이블: {existing_tables}")
        print(f"🔍 필요한 테이블: {required_tables}")
        is_initialized = required_tables.issubset(existing_tables)
        print(f"🔍 초기화 상태: {is_initialized}")
        return is_initialized
    except Exception as e:
        # 데이터베이스 연결 실패 등 예외 발생 시 초기화되지 않은 것으로 간주
        print(f"⚠️ 데이터베이스 확인 중 오류 발생 (초기화 필요 가능성): {e}")
        return False

# 데이터베이스 초기화
def init_database():
    """데이터베이스를 초기화합니다."""
    print(f"🔄 CoE-Backend 데이터베이스 초기화 시작...")
    print(f"📊 연결 정보: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    try:
        # 이미 초기화되었다면 건너뛰기
        if _is_database_initialized():
            print("✅ 데이터베이스가 이미 초기화되었습니다. 건너뜁니다.")
            return True
        
        print("🔄 데이터베이스 초기화가 필요합니다...")
        
        # 연결 테스트
        if not test_connection():
            print("❌ 데이터베이스 연결 테스트 실패")
            return False
        
        # 필요한 최소 테이블이 없으면 직접 생성 시도 (로컬/개발 환경 호환성)
        if not _is_database_initialized():
            create_tables()

        # 초기화 완료 후 다시 확인 (테이블 생성 후 잠시 대기)
        import time
        time.sleep(1)

        if not _is_database_initialized():
            print("❌ 초기화 후에도 데이터베이스 테이블이 확인되지 않았습니다.")
            return False
            
        print("✅ 데이터베이스 초기화가 성공적으로 완료되었습니다.")
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
