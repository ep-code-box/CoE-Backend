"""
서비스 레이어 단위 테스트
"""
import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from services.analysis_service import AnalysisService
from core.database import AnalysisRequest, AnalysisStatus


@pytest.mark.unit
class TestAnalysisService:
    """분석 서비스 테스트"""
    
    def test_create_analysis_request_success(self, mock_db):
        """분석 요청 생성 성공 테스트"""
        # Mock 설정
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_analysis.analysis_id = "test-analysis-id"
        mock_analysis.status = AnalysisStatus.PENDING
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        repositories = [
            {"url": "https://github.com/test/repo1", "branch": "main"},
            {"url": "https://github.com/test/repo2", "branch": "develop"}
        ]
        
        # 실제 AnalysisRequest 객체 생성을 Mock
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            
            result = AnalysisService.create_analysis_request(
                db=mock_db,
                repositories=repositories,
                include_ast=True,
                include_tech_spec=True,
                include_correlation=True,
                analysis_id="test-analysis-id"
            )
        
        # 검증
        assert result == mock_analysis
        mock_db.add.assert_called_once_with(mock_analysis)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_analysis)
    
    def test_create_analysis_request_auto_generate_id(self, mock_db):
        """분석 요청 ID 자동 생성 테스트"""
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            with patch('services.analysis_service.uuid.uuid4') as mock_uuid:
                mock_uuid.return_value = Mock(spec=uuid.UUID)
                mock_uuid.return_value.__str__ = Mock(return_value="auto-generated-id")
                
                result = AnalysisService.create_analysis_request(
                    db=mock_db,
                    repositories=repositories
                )
        
        # UUID 생성이 호출되었는지 확인
        mock_uuid.assert_called_once()
        assert result == mock_analysis
    
    def test_create_analysis_request_duplicate_id_error(self, mock_db):
        """중복 분석 ID 에러 테스트"""
        mock_db.add = Mock()
        mock_db.commit = Mock(side_effect=IntegrityError("", "", ""))
        mock_db.rollback = Mock()
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        with patch('services.analysis_service.AnalysisRequest'):
            with pytest.raises(ValueError) as exc_info:
                AnalysisService.create_analysis_request(
                    db=mock_db,
                    repositories=repositories,
                    analysis_id="duplicate-id"
                )
        
        assert "already exists" in str(exc_info.value)
        mock_db.rollback.assert_called_once()
    
    def test_create_analysis_request_default_parameters(self, mock_db):
        """분석 요청 기본 파라미터 테스트"""
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            
            AnalysisService.create_analysis_request(
                db=mock_db,
                repositories=repositories
            )
        
        # 기본값으로 호출되었는지 확인
        call_args = mock_request_class.call_args
        assert call_args.kwargs['include_ast'] is True
        assert call_args.kwargs['include_tech_spec'] is True
        assert call_args.kwargs['include_correlation'] is True
        assert call_args.kwargs['status'] == AnalysisStatus.PENDING
    
    def test_create_analysis_request_custom_parameters(self, mock_db):
        """분석 요청 커스텀 파라미터 테스트"""
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            
            AnalysisService.create_analysis_request(
                db=mock_db,
                repositories=repositories,
                include_ast=False,
                include_tech_spec=False,
                include_correlation=False
            )
        
        # 커스텀 값으로 호출되었는지 확인
        call_args = mock_request_class.call_args
        assert call_args.kwargs['include_ast'] is False
        assert call_args.kwargs['include_tech_spec'] is False
        assert call_args.kwargs['include_correlation'] is False
    
    def test_create_analysis_request_empty_repositories(self, mock_db):
        """빈 저장소 리스트로 분석 요청 생성"""
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            
            result = AnalysisService.create_analysis_request(
                db=mock_db,
                repositories=[]
            )
        
        assert result == mock_analysis
        call_args = mock_request_class.call_args
        assert call_args.kwargs['repositories'] == []
    
    def test_create_analysis_request_complex_repositories(self, mock_db):
        """복잡한 저장소 정보로 분석 요청 생성"""
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        repositories = [
            {
                "url": "https://github.com/org/repo1",
                "branch": "main",
                "path": "/src",
                "exclude_patterns": ["*.test.js", "node_modules/"]
            },
            {
                "url": "https://gitlab.com/org/repo2",
                "branch": "develop",
                "auth_token": "secret-token"
            }
        ]
        
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            
            result = AnalysisService.create_analysis_request(
                db=mock_db,
                repositories=repositories
            )
        
        assert result == mock_analysis
        call_args = mock_request_class.call_args
        assert call_args.kwargs['repositories'] == repositories


@pytest.mark.unit
class TestAnalysisServiceIntegration:
    """분석 서비스 통합 테스트"""
    
    def test_analysis_request_lifecycle(self, mock_db):
        """분석 요청 생명주기 테스트"""
        # 1. 분석 요청 생성
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_analysis.analysis_id = "lifecycle-test"
        mock_analysis.status = AnalysisStatus.PENDING
        mock_analysis.created_at = datetime.utcnow()
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
            mock_request_class.return_value = mock_analysis
            
            # 분석 요청 생성
            result = AnalysisService.create_analysis_request(
                db=mock_db,
                repositories=repositories,
                analysis_id="lifecycle-test"
            )
        
        # 생성 검증
        assert result.analysis_id == "lifecycle-test"
        assert result.status == AnalysisStatus.PENDING
        assert result.created_at is not None
        
        # 데이터베이스 호출 검증
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_analysis_request_error_recovery(self, mock_db):
        """분석 요청 에러 복구 테스트"""
        mock_db.add = Mock()
        mock_db.commit = Mock(side_effect=IntegrityError("", "", ""))
        mock_db.rollback = Mock()
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        with patch('services.analysis_service.AnalysisRequest'):
            # 에러 발생 시 적절한 예외가 발생하는지 확인
            with pytest.raises(ValueError):
                AnalysisService.create_analysis_request(
                    db=mock_db,
                    repositories=repositories,
                    analysis_id="error-test"
                )
        
        # 롤백이 호출되었는지 확인
        mock_db.rollback.assert_called_once()
    
    def test_analysis_request_parameter_validation(self, mock_db):
        """분석 요청 파라미터 검증 테스트"""
        mock_analysis = Mock(spec=AnalysisRequest)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # 다양한 파라미터 조합 테스트
        test_cases = [
            # (include_ast, include_tech_spec, include_correlation)
            (True, True, True),
            (True, True, False),
            (True, False, True),
            (False, True, True),
            (False, False, False),
        ]
        
        repositories = [{"url": "https://github.com/test/repo", "branch": "main"}]
        
        for ast, tech, corr in test_cases:
            with patch('services.analysis_service.AnalysisRequest') as mock_request_class:
                mock_request_class.return_value = mock_analysis
                
                result = AnalysisService.create_analysis_request(
                    db=mock_db,
                    repositories=repositories,
                    include_ast=ast,
                    include_tech_spec=tech,
                    include_correlation=corr
                )
            
            # 파라미터가 올바르게 전달되었는지 확인
            call_args = mock_request_class.call_args
            assert call_args.kwargs['include_ast'] == ast
            assert call_args.kwargs['include_tech_spec'] == tech
            assert call_args.kwargs['include_correlation'] == corr
            assert result == mock_analysis