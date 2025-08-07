"""
인증 미들웨어 및 보안 관련 미들웨어
"""



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
        logger.info(f"Content-Type: {request.headers.get('content-type')}")
        
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