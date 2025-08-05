"""
JWT 토큰 기반 인증 유틸리티 모듈
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import redis
import json

from .database import User, UserRole, RefreshToken, get_db

# 환경 변수 로드
load_dotenv()

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Redis 설정
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "coe_redis_password")
REDIS_DB = int(os.getenv("REDIS_AUTH_DB", "1"))

# 패스워드 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis 클라이언트 초기화
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        decode_responses=True
    )
    # 연결 테스트
    redis_client.ping()
    print("✅ Redis 연결 성공")
except Exception as e:
    print(f"❌ Redis 연결 실패: {e}")
    redis_client = None

class AuthenticationError(HTTPException):
    """인증 관련 예외"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class AuthorizationError(HTTPException):
    """권한 관련 예외"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int) -> str:
    """리프레시 토큰 생성"""
    to_encode = {"user_id": user_id}
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """토큰 검증"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 토큰 타입 확인
        if payload.get("type") != token_type:
            raise AuthenticationError("Invalid token type")
        
        # 만료 시간 확인
        exp = payload.get("exp")
        if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
            raise AuthenticationError("Token expired")
        
        return payload
    except JWTError:
        raise AuthenticationError("Invalid token")

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """사용자 인증"""
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    # 마지막 로그인 시간 업데이트
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user

def get_user_permissions(db: Session, user_id: int) -> List[str]:
    """사용자 권한 조회"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    permissions = set()
    
    # 슈퍼유저는 모든 권한
    if user.is_superuser:
        permissions.add("*")
    
    # 역할별 권한 수집
    for role_mapping in user.role_mappings:
        role_permissions = role_mapping.role.permissions or []
        permissions.update(role_permissions)
    
    return list(permissions)

def get_current_user(token: str, db: Session) -> User:
    """현재 사용자 조회"""
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise AuthenticationError("Invalid authentication credentials")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid authentication credentials")
    return user

def check_permission(user_permissions: List[str], required_permission: str) -> bool:
    """권한 확인"""
    if "*" in user_permissions:
        return True
    
    return required_permission in user_permissions

def store_refresh_token(db: Session, user_id: int, refresh_token: str) -> RefreshToken:
    """리프레시 토큰 저장"""
    # 기존 토큰들 무효화
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True, "revoked_at": datetime.utcnow()})
    
    # 새 토큰 저장
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    return db_token

def verify_refresh_token(db: Session, refresh_token: str) -> Optional[User]:
    """리프레시 토큰 검증"""
    try:
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
        
        # 데이터베이스에서 토큰 확인
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not db_token:
            return None
        
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    except AuthenticationError:
        return None

def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    """리프레시 토큰 무효화"""
    try:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False
        ).first()
        
        if db_token:
            db_token.is_revoked = True
            db_token.revoked_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    except Exception:
        return False

def revoke_token(token: str) -> bool:
    """액세스 토큰을 블랙리스트에 추가하여 무효화"""
    try:
        payload = verify_token(token)
        expires_at = datetime.fromtimestamp(payload["exp"])
        return blacklist_token(token, expires_at)
    except Exception as e:
        print(f"토큰 무효화 실패: {e}")
        return False

def is_token_revoked(token: str) -> bool:
    """토큰이 무효화되었는지 확인"""
    return is_token_blacklisted(token)

def blacklist_token(token: str, expires_at: datetime) -> bool:
    """토큰 블랙리스트에 추가 (Redis 사용)"""
    if not redis_client:
        return False
    
    try:
        # 토큰 해시 생성
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Redis에 저장 (만료 시간까지)
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            redis_client.setex(f"blacklist:{token_hash}", ttl, "1")
        
        return True
    except Exception as e:
        print(f"토큰 블랙리스트 추가 실패: {e}")
        return False

def is_token_blacklisted(token: str) -> bool:
    """토큰이 블랙리스트에 있는지 확인"""
    if not redis_client:
        return False
    
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return redis_client.exists(f"blacklist:{token_hash}")
    except Exception:
        return False

def store_user_session(user_id: int, session_data: Dict[str, Any]) -> bool:
    """사용자 세션 정보 저장 (Redis)"""
    if not redis_client:
        return False
    
    try:
        session_key = f"session:{user_id}"
        redis_client.setex(
            session_key, 
            ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 액세스 토큰과 동일한 만료 시간
            json.dumps(session_data)
        )
        return True
    except Exception as e:
        print(f"세션 저장 실패: {e}")
        return False

def get_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """사용자 세션 정보 조회"""
    if not redis_client:
        return None
    
    try:
        session_key = f"session:{user_id}"
        session_data = redis_client.get(session_key)
        if session_data:
            return json.loads(session_data)
        return None
    except Exception as e:
        print(f"세션 조회 실패: {e}")
        return None

def delete_user_session(user_id: int) -> bool:
    """사용자 세션 삭제"""
    if not redis_client:
        return False
    
    try:
        session_key = f"session:{user_id}"
        redis_client.delete(session_key)
        return True
    except Exception as e:
        print(f"세션 삭제 실패: {e}")
        return False