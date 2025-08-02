"""
사용자 인증 관련 API 엔드포인트
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db, User, UserRole, UserRoleMapping
from core.auth import (
    authenticate_user, create_access_token, create_refresh_token,
    get_password_hash, verify_refresh_token, store_refresh_token,
    revoke_refresh_token, get_user_permissions, verify_token,
    is_token_blacklisted, blacklist_token, store_user_session,
    delete_user_session, AuthenticationError, AuthorizationError,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from core.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, UserUpdateRequest,
    PasswordChangeRequest, RoleResponse, ErrorResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """현재 인증된 사용자 조회"""
    token = credentials.credentials
    
    # 토큰 블랙리스트 확인
    if is_token_blacklisted(token):
        raise AuthenticationError("Token has been revoked")
    
    try:
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        return user
    except AuthenticationError:
        raise
    except Exception:
        raise AuthenticationError("Invalid token")

def require_permission(permission: str):
    """권한 확인 데코레이터"""
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        user_permissions = get_user_permissions(db, current_user.id)
        
        if not any(perm == "*" or perm == permission for perm in user_permissions):
            raise AuthorizationError(f"Permission '{permission}' required")
        
        return current_user
    
    return permission_checker

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """사용자 등록"""
    # 중복 확인
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # 새 사용자 생성
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 기본 'user' 역할 할당
    user_role = db.query(UserRole).filter(UserRole.name == "user").first()
    if user_role:
        role_mapping = UserRoleMapping(
            user_id=db_user.id,
            role_id=user_role.id
        )
        db.add(role_mapping)
        db.commit()
    
    # 사용자 정보 반환 - role_mappings 관계가 비활성화되어 있으므로 직접 쿼리
    roles = []
    role_mappings = db.query(UserRoleMapping).filter(UserRoleMapping.user_id == db_user.id).all()
    for mapping in role_mappings:
        role = db.query(UserRole).filter(UserRole.id == mapping.role_id).first()
        if role:
            roles.append(role.name)
    
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        is_active=db_user.is_active,
        is_superuser=db_user.is_superuser,
        created_at=db_user.created_at.isoformat(),
        last_login=db_user.last_login.isoformat() if db_user.last_login else None,
        roles=roles
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """사용자 로그인"""
    user = authenticate_user(db, user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    # 리프레시 토큰 저장
    store_refresh_token(db, user.id, refresh_token)
    
    # 세션 정보 저장
    session_data = {
        "user_id": user.id,
        "username": user.username,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent", ""),
        "login_time": datetime.utcnow().isoformat()
    }
    store_user_session(user.id, session_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """액세스 토큰 갱신"""
    user = verify_refresh_token(db, token_data.refresh_token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # 새 액세스 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=token_data.refresh_token,  # 기존 리프레시 토큰 재사용
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 로그아웃"""
    token = credentials.credentials
    
    try:
        # 토큰 정보 추출
        payload = verify_token(token, "access")
        exp = payload.get("exp")
        
        if exp:
            expires_at = datetime.fromtimestamp(exp)
            # 토큰을 블랙리스트에 추가
            blacklist_token(token, expires_at)
        
        # 사용자 세션 삭제
        delete_user_session(current_user.id)
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/revoke-refresh")
async def revoke_refresh_token_endpoint(
    token_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """리프레시 토큰 무효화"""
    success = revoke_refresh_token(db, token_data.refresh_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke refresh token"
        )
    
    return {"message": "Refresh token revoked successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자 정보 조회"""
    roles = [mapping.role.name for mapping in current_user.role_mappings]
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        roles=roles
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자 정보 수정"""
    # 이메일 중복 확인
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
    
    # 사용자 정보 업데이트
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.is_active is not None and current_user.is_superuser:
        current_user.is_active = user_update.is_active
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    roles = [mapping.role.name for mapping in current_user.role_mappings]
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        roles=roles
    )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """비밀번호 변경"""
    from core.auth import verify_password
    
    # 현재 비밀번호 확인
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # 새 비밀번호 설정
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """역할 목록 조회 (관리자 전용)"""
    roles = db.query(UserRole).all()
    
    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=role.permissions or []
        )
        for role in roles
    ]

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(require_permission("manage_users")),
    db: Session = Depends(get_db)
):
    """사용자 목록 조회 (관리자 전용)"""
    users = db.query(User).all()
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
            roles=[mapping.role.name for mapping in user.role_mappings]
        )
        for user in users
    ]