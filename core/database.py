import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey, Enum, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import enum

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

# 사용자 인증 관련 모델
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # 관계 설정
    role_mappings = relationship("UserRoleMapping", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    role_mappings = relationship("UserRoleMapping", back_populates="role", cascade="all, delete-orphan")

class UserRoleMapping(Base):
    __tablename__ = "user_role_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("user_roles.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, nullable=True)  # ForeignKey 제거하여 순환 참조 방지
    
    # 관계 설정
    user = relationship("User", back_populates="role_mappings")
    role = relationship("UserRole", back_populates="role_mappings")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    # 관계 설정
    user = relationship("User", back_populates="refresh_tokens")

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

# 분석 요청 테이블
class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), unique=True, index=True, nullable=False)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    repositories = Column(JSON, nullable=False)
    include_ast = Column(Boolean, default=True)
    include_tech_spec = Column(Boolean, default=True)
    include_correlation = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 관계 설정
    repository_analyses = relationship("RepositoryAnalysis", back_populates="analysis_request", cascade="all, delete-orphan")
    correlation_analyses = relationship("CorrelationAnalysis", back_populates="analysis_request", cascade="all, delete-orphan")
    development_standards = relationship("DevelopmentStandard", back_populates="analysis_request", cascade="all, delete-orphan")

# 레포지토리 분석 결과 테이블
class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_requests.analysis_id"), nullable=False)
    repository_url = Column(String(500), nullable=False)
    repository_name = Column(String(255))
    branch = Column(String(100), default="main")
    clone_path = Column(String(500))
    status = Column(Enum(RepositoryStatus), default=RepositoryStatus.PENDING)
    files_count = Column(Integer, default=0)
    lines_of_code = Column(Integer, default=0)
    languages = Column(JSON)
    frameworks = Column(JSON)
    dependencies = Column(JSON)
    ast_data = Column(Text)
    tech_specs = Column(JSON)
    code_metrics = Column(JSON)
    documentation_files = Column(JSON)
    config_files = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    analysis_request = relationship("AnalysisRequest", back_populates="repository_analyses")
    code_files = relationship("CodeFile", back_populates="repository_analysis", cascade="all, delete-orphan")
    tech_dependencies = relationship("TechDependency", back_populates="repository_analysis", cascade="all, delete-orphan")
    document_analyses = relationship("DocumentAnalysis", back_populates="repository_analysis", cascade="all, delete-orphan")

# 코드 파일 정보 테이블
class CodeFile(Base):
    __tablename__ = "code_files"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_analysis_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    language = Column(String(50))
    lines_of_code = Column(Integer, default=0)
    complexity_score = Column(DECIMAL(5, 2))
    last_modified = Column(DateTime)
    file_hash = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    repository_analysis = relationship("RepositoryAnalysis", back_populates="code_files")
    ast_nodes = relationship("ASTNode", back_populates="code_file", cascade="all, delete-orphan")

# AST 노드 테이블
class ASTNode(Base):
    __tablename__ = "ast_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    code_file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False)
    node_type = Column(String(100), nullable=False)
    node_name = Column(String(255))
    line_start = Column(Integer)
    line_end = Column(Integer)
    parent_id = Column(Integer, ForeignKey("ast_nodes.id"))
    node_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    code_file = relationship("CodeFile", back_populates="ast_nodes")
    parent = relationship("ASTNode", remote_side=[id])

# 기술 스택 및 의존성 테이블
class TechDependency(Base):
    __tablename__ = "tech_dependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_analysis_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    dependency_type = Column(Enum(DependencyType), nullable=False)
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    package_manager = Column(String(50))
    is_dev_dependency = Column(Boolean, default=False)
    license = Column(String(100))
    vulnerability_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    repository_analysis = relationship("RepositoryAnalysis", back_populates="tech_dependencies")

# 레포지토리 간 연관도 분석 테이블
class CorrelationAnalysis(Base):
    __tablename__ = "correlation_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_requests.analysis_id"), nullable=False)
    repository1_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    repository2_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    common_dependencies = Column(JSON)
    similar_patterns = Column(JSON)
    architecture_similarity = Column(DECIMAL(5, 4), default=0.0000)
    shared_technologies = Column(JSON)
    similarity_score = Column(DECIMAL(5, 4), default=0.0000)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    analysis_request = relationship("AnalysisRequest", back_populates="correlation_analyses")

# 문서 분석 결과 테이블
class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_analysis_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    document_path = Column(String(1000), nullable=False)
    document_type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    title = Column(String(500))
    content = Column(Text)
    extracted_sections = Column(JSON)
    code_examples = Column(JSON)
    api_endpoints = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    repository_analysis = relationship("RepositoryAnalysis", back_populates="document_analyses")

# 벡터 임베딩 메타데이터 테이블
class VectorEmbedding(Base):
    __tablename__ = "vector_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(Enum(SourceType), nullable=False)
    source_id = Column(Integer, nullable=False)
    chunk_id = Column(String(100), nullable=False)
    collection_name = Column(String(255), nullable=False)
    embedding_model = Column(String(100), default="default")
    chunk_text = Column(Text)
    node_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# 개발 표준 문서 테이블
class DevelopmentStandard(Base):
    __tablename__ = "development_standards"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_requests.analysis_id"), nullable=False)
    standard_type = Column(Enum(StandardType), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    examples = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    analysis_request = relationship("AnalysisRequest", back_populates="development_standards")

# 사용자 세션 테이블
class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_agent = Column(Text)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # 관계 설정
    api_logs = relationship("APILog", back_populates="user_session")

# API 호출 로그 테이블
class APILog(Base):
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("user_sessions.session_id"))
    endpoint = Column(String(255), nullable=False)
    method = Column(Enum(HTTPMethod), nullable=False)
    request_data = Column(JSON)
    response_status = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    user_session = relationship("UserSession", back_populates="api_logs")

# 백워드 호환성을 위한 RAG 분석 결과 테이블 (CoE-RagPipeline과 호환)
class RagAnalysisResult(Base):
    __tablename__ = "rag_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(255), unique=True, index=True, nullable=False)
    git_url = Column(String(500), index=True, nullable=False)
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    repository_count = Column(Integer, default=0)
    total_files = Column(Integer, default=0)
    total_lines_of_code = Column(Integer, default=0)
    
    # 분석 결과 데이터 (JSON 형태로 저장)
    repositories_data = Column(Text, nullable=True)
    correlation_data = Column(Text, nullable=True)
    tech_specs_summary = Column(Text, nullable=True)
    
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