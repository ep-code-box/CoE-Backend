import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from core.database import (
    AnalysisRequest, RepositoryAnalysis, CodeFile, DevelopmentStandard, AnalysisStatus, RepositoryStatus, StandardType
)

class AnalysisService:
    """분석 요청 및 결과 관리 서비스"""
    
    @staticmethod
    def create_analysis_request(
        db: Session, 
        repositories: List[Dict[str, Any]], 
        include_ast: bool = True,
        include_tech_spec: bool = True,
        include_correlation: bool = True,
        analysis_id: Optional[str] = None
    ) -> AnalysisRequest:
        """새로운 분석 요청을 생성합니다."""
        try:
            if not analysis_id:
                analysis_id = str(uuid.uuid4())
            
            db_analysis = AnalysisRequest(
                analysis_id=analysis_id,
                repositories=repositories,
                include_ast=include_ast,
                include_tech_spec=include_tech_spec,
                include_correlation=include_correlation,
                status=AnalysisStatus.PENDING
            )
            
            db.add(db_analysis)
            db.commit()
            db.refresh(db_analysis)
            
            return db_analysis
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Analysis with ID '{analysis_id}' already exists")
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create analysis request: {str(e)}")
    
    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: str) -> Optional[AnalysisRequest]:
        """분석 ID로 분석 요청을 조회합니다."""
        return db.query(AnalysisRequest).filter(AnalysisRequest.analysis_id == analysis_id).first()
    
    @staticmethod
    def get_all_analyses(db: Session, limit: int = 100, offset: int = 0) -> List[AnalysisRequest]:
        """모든 분석 요청을 조회합니다."""
        return db.query(AnalysisRequest).order_by(AnalysisRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def update_analysis_status(
        db: Session, 
        analysis_id: str, 
        status: AnalysisStatus,
        error_message: Optional[str] = None
    ) -> Optional[AnalysisRequest]:
        """분석 상태를 업데이트합니다."""
        try:
            db_analysis = AnalysisService.get_analysis_by_id(db, analysis_id)
            if not db_analysis:
                return None
            
            db_analysis.status = status
            db_analysis.updated_at = datetime.utcnow()
            
            if status == AnalysisStatus.COMPLETED:
                db_analysis.completed_at = datetime.utcnow()
            
            if error_message:
                db_analysis.error_message = error_message
            
            db.commit()
            db.refresh(db_analysis)
            
            return db_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update analysis status: {str(e)}")

class RepositoryAnalysisService:
    """레포지토리 분석 결과 관리 서비스"""
    
    @staticmethod
    def create_repository_analysis(
        db: Session,
        analysis_id: str,
        repository_url: str,
        repository_name: Optional[str] = None,
        branch: str = "main",
        clone_path: Optional[str] = None
    ) -> RepositoryAnalysis:
        """새로운 레포지토리 분석을 생성합니다."""
        try:
            db_repo_analysis = RepositoryAnalysis(
                analysis_id=analysis_id,
                repository_url=repository_url,
                repository_name=repository_name,
                branch=branch,
                clone_path=clone_path,
                status=RepositoryStatus.PENDING
            )
            
            db.add(db_repo_analysis)
            db.commit()
            db.refresh(db_repo_analysis)
            
            return db_repo_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create repository analysis: {str(e)}")
    
    @staticmethod
    def update_repository_analysis(
        db: Session,
        repo_analysis_id: int,
        status: Optional[RepositoryStatus] = None,
        files_count: Optional[int] = None,
        lines_of_code: Optional[int] = None,
        languages: Optional[List[str]] = None,
        frameworks: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        ast_data: Optional[str] = None,
        tech_specs: Optional[Dict[str, Any]] = None,
        code_metrics: Optional[Dict[str, Any]] = None,
        documentation_files: Optional[List[str]] = None,
        config_files: Optional[List[str]] = None
    ) -> Optional[RepositoryAnalysis]:
        """레포지토리 분석 결과를 업데이트합니다."""
        try:
            db_repo_analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.id == repo_analysis_id).first()
            if not db_repo_analysis:
                return None
            
            if status is not None:
                db_repo_analysis.status = status
            if files_count is not None:
                db_repo_analysis.files_count = files_count
            if lines_of_code is not None:
                db_repo_analysis.lines_of_code = lines_of_code
            if languages is not None:
                db_repo_analysis.languages = languages
            if frameworks is not None:
                db_repo_analysis.frameworks = frameworks
            if dependencies is not None:
                db_repo_analysis.dependencies = dependencies
            if ast_data is not None:
                db_repo_analysis.ast_data = ast_data
            if tech_specs is not None:
                db_repo_analysis.tech_specs = tech_specs
            if code_metrics is not None:
                db_repo_analysis.code_metrics = code_metrics
            if documentation_files is not None:
                db_repo_analysis.documentation_files = documentation_files
            if config_files is not None:
                db_repo_analysis.config_files = config_files
            
            db_repo_analysis.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_repo_analysis)
            
            return db_repo_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update repository analysis: {str(e)}")
    
    @staticmethod
    def get_repositories_by_analysis_id(db: Session, analysis_id: str) -> List[RepositoryAnalysis]:
        """분석 ID로 레포지토리 분석 결과들을 조회합니다."""
        return db.query(RepositoryAnalysis).filter(RepositoryAnalysis.analysis_id == analysis_id).all()

class CodeFileService:
    """코드 파일 관리 서비스"""
    
    @staticmethod
    def create_code_file(
        db: Session,
        repository_analysis_id: int,
        file_path: str,
        file_name: str,
        file_size: int = 0,
        language: Optional[str] = None,
        lines_of_code: int = 0,
        complexity_score: Optional[float] = None,
        last_modified: Optional[datetime] = None,
        file_hash: Optional[str] = None
    ) -> CodeFile:
        """새로운 코드 파일을 생성합니다."""
        try:
            db_code_file = CodeFile(
                repository_analysis_id=repository_analysis_id,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                language=language,
                lines_of_code=lines_of_code,
                complexity_score=complexity_score,
                last_modified=last_modified,
                file_hash=file_hash
            )
            
            db.add(db_code_file)
            db.commit()
            db.refresh(db_code_file)
            
            return db_code_file
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create code file: {str(e)}")
    
    @staticmethod
    def get_files_by_repository_analysis_id(db: Session, repository_analysis_id: int) -> List[CodeFile]:
        """레포지토리 분석 ID로 코드 파일들을 조회합니다."""
        return db.query(CodeFile).filter(CodeFile.repository_analysis_id == repository_analysis_id).all()

class DevelopmentStandardService:
    """개발 표준 문서 관리 서비스"""
    
    @staticmethod
    def create_development_standard(
        db: Session,
        analysis_id: str,
        standard_type: StandardType,
        title: str,
        content: str,
        examples: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None
    ) -> DevelopmentStandard:
        """새로운 개발 표준 문서를 생성합니다."""
        try:
            db_standard = DevelopmentStandard(
                analysis_id=analysis_id,
                standard_type=standard_type,
                title=title,
                content=content,
                examples=examples or {},
                recommendations=recommendations or {}
            )
            
            db.add(db_standard)
            db.commit()
            db.refresh(db_standard)
            
            return db_standard
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create development standard: {str(e)}")
    
    @staticmethod
    def get_standards_by_analysis_id(db: Session, analysis_id: str) -> List[DevelopmentStandard]:
        """분석 ID로 개발 표준 문서들을 조회합니다."""
        return db.query(DevelopmentStandard).filter(DevelopmentStandard.analysis_id == analysis_id).all()
    
    @staticmethod
    def get_standards_by_type(db: Session, analysis_id: str, standard_type: StandardType) -> List[DevelopmentStandard]:
        """분석 ID와 표준 타입으로 개발 표준 문서들을 조회합니다."""
        return db.query(DevelopmentStandard).filter(
            DevelopmentStandard.analysis_id == analysis_id,
            DevelopmentStandard.standard_type == standard_type
        ).all()

# 편의 함수들
def get_analysis_service() -> AnalysisService:
    """AnalysisService 인스턴스를 반환합니다."""
    return AnalysisService()

def get_repository_analysis_service() -> RepositoryAnalysisService:
    """RepositoryAnalysisService 인스턴스를 반환합니다."""
    return RepositoryAnalysisService()

def get_code_file_service() -> CodeFileService:
    """CodeFileService 인스턴스를 반환합니다."""
    return CodeFileService()

def get_development_standard_service() -> DevelopmentStandardService:
    """DevelopmentStandardService 인스턴스를 반환합니다."""
    return DevelopmentStandardService()