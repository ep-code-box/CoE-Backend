"""
인증 미들웨어 및 보안 관련 미들웨어
"""

from typing import Optional, List
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging

from .auth import verify_token, is_token_blacklisted, AuthenticationError
from .database import get_db, User

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    인증이 필요한 엔드포인트에 대한 미들웨어
    """
    
    # 인증이 필요하지 않은 경로들
    EXCLUDED_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/test",
        "/v1/models",  # 모델 목록은 공개
    ]
    
    # 인증이 필요한 경로들 (우선순위가 높음)
    PROTECTED_PATHS = [
        "/auth/me",
        "/auth/logout",
        "/auth/change-password",
        "/auth/revoke-refresh",
        "/auth/roles",
        "/auth/users",
        "/v1/chat/completions",
        "/flows/",
        "/vector/",
        "/embeddings/",
        "/coding-assistant/",
    ]
    
    def __init__(self, app, enforce_auth: bool = True):
        super().__init__(app)
        self.enforce_auth = enforce_auth
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        # 인증 강제가 비활성화된 경우 통과
        if not self.enforce_auth:
            return await call_next(request)
        
        path = request.url.path
        method = request.method
        
        # 제외 경로 확인
        if self._is_excluded_path(path):
            return await call_next(request)
        
        # 보호된 경로 확인
        if self._is_protected_path(path):
            auth_result = await self._authenticate_request(request)
            if not auth_result["success"]:
                return JSONResponse(
                    status_code=auth_result["status_code"],
                    content={"detail": auth_result["message"]}
                )
            
            # 인증된 사용자 정보를 request state에 저장
            request.state.current_user = auth_result["user"]
        
        return await call_next(request)
    
    def _is_excluded_path(self, path: str) -> bool:
        """제외 경로인지 확인"""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)
    
    def _is_protected_path(self, path: str) -> bool:
        """보호된 경로인지 확인"""
        return any(path.startswith(protected) for protected in self.PROTECTED_PATHS)
    
    async def _authenticate_request(self, request: Request) -> dict:
        """요청 인증"""
        try:
            # Authorization 헤더에서 토큰 추출
            authorization = request.headers.get("Authorization")
            if not authorization:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Authorization header missing"
                }
            
            if not authorization.startswith("Bearer "):
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Invalid authorization header format"
                }
            
            token = authorization.split(" ")[1]
            
            # 토큰 블랙리스트 확인
            if is_token_blacklisted(token):
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Token has been revoked"
                }
            
            # 토큰 검증
            payload = verify_token(token, "access")
            user_id = payload.get("sub")
            
            if not user_id:
                return {
                    "success": False,
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "message": "Invalid token payload"
                }
            
            # 사용자 정보 조회 (간단한 캐싱을 위해 request state 사용)
            db = next(get_db())
            try:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if not user:
                    return {
                        "success": False,
                        "status_code": status.HTTP_401_UNAUTHORIZED,
                        "message": "User not found"
                    }
                
                if not user.is_active:
                    return {
                        "success": False,
                        "status_code": status.HTTP_401_UNAUTHORIZED,
                        "message": "User account is disabled"
                    }
                
                return {
                    "success": True,
                    "user": user
                }
            finally:
                db.close()
                
        except AuthenticationError as e:
            return {
                "success": False,
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "message": str(e.detail)
            }
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {
                "success": False,
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "message": "Authentication failed"
            }

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API 요청 속도 제한 미들웨어
    """
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = {}  # IP별 요청 기록
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        # 1분 이전 요청 기록 정리
        self._cleanup_old_requests(current_time)
        
        # 현재 IP의 요청 기록 확인
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # 1분 내 요청 수 확인
        recent_requests = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]
        
        if len(recent_requests) >= self.calls_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Maximum {self.calls_per_minute} requests per minute."
                }
            )
        
        # 현재 요청 기록
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)
    
    def _cleanup_old_requests(self, current_time: float):
        """1분 이전 요청 기록 정리"""
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if current_time - req_time < 60
            ]
            
            # 빈 리스트는 제거
            if not self.requests[ip]:
                del self.requests[ip]

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    보안 헤더 추가 미들웨어
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    요청 로깅 미들웨어
    """
    
    def __init__(self, app, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 정보 로깅
        logger.info(f"Request: {request.method} {request.url}")
        logger.info(f"Client: {request.client.host}")
        logger.info(f"User-Agent: {request.headers.get('user-agent', 'Unknown')}")
        
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    logger.info(f"Request body: {body.decode('utf-8')[:1000]}...")
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")
        
        response = await call_next(request)
        
        # 응답 정보 로깅
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")
        
        return response