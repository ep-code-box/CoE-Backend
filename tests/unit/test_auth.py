"""
인증 모듈 단위 테스트
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from jose import jwt
from fastapi import HTTPException, status

from core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    authenticate_user,
    blacklist_token,
    is_token_blacklisted,
    SECRET_KEY,
    ALGORITHM,
    get_current_user,
    revoke_token,
    is_token_revoked
)
from core.database import User, UserRole


class TestPasswordUtils:
    """패스워드 유틸리티 테스트"""
    
    def test_password_hashing(self):
        """패스워드 해싱 테스트"""
        password = "test_password123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_password_hash_different_each_time(self):
        """같은 패스워드도 매번 다른 해시 생성"""
        password = "test_password123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenGeneration:
    """토큰 생성 테스트"""
    
    def test_create_access_token(self):
        """액세스 토큰 생성 테스트"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        
        # 토큰 디코딩 검증
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"
        assert decoded["user_id"] == 1
        assert "exp" in decoded
    
    def test_create_access_token_with_custom_expiry(self):
        """커스텀 만료시간으로 액세스 토큰 생성"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(decoded["exp"])
        expected_time = datetime.utcnow() + expires_delta
        
        # 1분 오차 허용
        assert abs((exp_time - expected_time).total_seconds()) < 120
    
    def test_create_refresh_token(self):
        """리프레시 토큰 생성 테스트"""
        user_id = 1
        token = create_refresh_token(user_id)
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["user_id"] == user_id
        assert decoded["type"] == "refresh"
        assert "exp" in decoded


class TestTokenVerification:
    """토큰 검증 테스트"""
    
    def test_verify_valid_token(self):
        """유효한 토큰 검증"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
    
    def test_verify_invalid_token(self):
        """잘못된 토큰 검증"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_expired_token(self):
        """만료된 토큰 검증"""
        data = {"sub": "testuser"}
        # 이미 만료된 토큰 생성
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserAuthentication:
    """사용자 인증 테스트"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock 사용자 객체"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = get_password_hash("correct_password")
        user.is_active = True
        return user
    
    def test_authenticate_user_success(self, mock_user):
        """사용자 인증 성공"""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_user
        
        result = authenticate_user(mock_db, "testuser", "correct_password")
        
        assert result == mock_user
        mock_db.query.assert_called_once()
    
    def test_authenticate_user_wrong_password(self, mock_user):
        """잘못된 패스워드로 인증 실패"""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_user
        
        result = authenticate_user(mock_db, "testuser", "wrong_password")
        
        assert result is None
    
    def test_authenticate_user_not_found(self):
        """존재하지 않는 사용자"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        
        result = authenticate_user(mock_db, "nonexistent", "password")
        
        assert result is False
    
    def test_authenticate_inactive_user(self, mock_user):
        """비활성 사용자 인증"""
        mock_user.is_active = False
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_user
        
        result = authenticate_user(mock_db, "testuser", "correct_password")
        
        assert result is False


class TestCurrentUser:
    """현재 사용자 조회 테스트"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock 사용자 객체"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.is_active = True
        return user
    
    @patch('core.auth.verify_token')
    def test_get_current_user_success(self, mock_verify_token, mock_user):
        """현재 사용자 조회 성공"""
        # Mock 설정
        mock_verify_token.return_value = {"user_id": 1}
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_user
        
        token = "valid.jwt.token"
        result = get_current_user(token, mock_db)
        
        assert result == mock_user
        mock_verify_token.assert_called_once_with(token)
    
    @patch('core.auth.verify_token')
    def test_get_current_user_invalid_token(self, mock_verify_token):
        """잘못된 토큰으로 현재 사용자 조회"""
        mock_verify_token.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        mock_db = Mock()
        
        with pytest.raises(HTTPException):
            get_current_user("invalid.token", mock_db)
    
    @patch('core.auth.verify_token')
    def test_get_current_user_not_found(self, mock_verify_token):
        """토큰은 유효하지만 사용자가 존재하지 않음"""
        mock_verify_token.return_value = {"user_id": 999}
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("valid.token", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRevocation:
    """토큰 폐기 테스트"""
    
    @patch('core.auth.redis_client')
    def test_revoke_token(self, mock_redis):
        """토큰 폐기 테스트"""
        token = "test.jwt.token"
        mock_redis.setex.return_value = True
        
        result = revoke_token(token)
        
        assert result is True
        mock_redis.setex.assert_called_once()
    
    @patch('core.auth.redis_client')
    def test_revoke_token_redis_error(self, mock_redis):
        """Redis 오류로 토큰 폐기 실패"""
        token = "test.jwt.token"
        mock_redis.setex.side_effect = Exception("Redis error")
        
        result = revoke_token(token)
        
        assert result is False
    
    @patch('core.auth.redis_client')
    def test_is_token_revoked_true(self, mock_redis):
        """폐기된 토큰 확인"""
        token = "revoked.jwt.token"
        mock_redis.exists.return_value = True
        
        result = is_token_revoked(token)
        
        assert result is True
        mock_redis.exists.assert_called_once()
    
    @patch('core.auth.redis_client')
    def test_is_token_revoked_false(self, mock_redis):
        """폐기되지 않은 토큰 확인"""
        token = "valid.jwt.token"
        mock_redis.exists.return_value = False
        
        result = is_token_revoked(token)
        
        assert result is False
    
    @patch('core.auth.redis_client')
    def test_is_token_revoked_redis_error(self, mock_redis):
        """Redis 오류 시 토큰 상태 확인"""
        token = "test.jwt.token"
        mock_redis.exists.side_effect = Exception("Redis error")
        
        result = is_token_revoked(token)
        
        # Redis 오류 시 안전하게 False 반환
        assert result is False


@pytest.mark.unit
class TestAuthIntegration:
    """인증 통합 테스트"""
    
    def test_full_auth_flow(self):
        """전체 인증 플로우 테스트"""
        # 1. 패스워드 해싱
        password = "test_password123"
        hashed_password = get_password_hash(password)
        
        # 2. 토큰 생성
        user_data = {"sub": "testuser", "user_id": 1}
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(1)
        
        # 3. 토큰 검증
        payload = verify_token(access_token)
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        
        # 4. 패스워드 검증
        assert verify_password(password, hashed_password) is True
        assert verify_password("wrong_password", hashed_password) is False