import os
import logging.config
import uvicorn
from dotenv import load_dotenv
from core.logging_config import get_simple_logging_config


class ServerRunner:
    """서버 실행을 담당하는 클래스"""
    
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = 8000
        self.is_development = False
    
    def load_environment(self):
        """환경 변수 로드 및 설정"""
        # .env 파일 로드 (개발 환경에서만 필요)
        load_dotenv()
        
        # 환경 변수를 통해 개발 모드와 프로덕션 모드를 구분
        self.is_development = os.getenv("APP_ENV") == "development"
        
        # 포트 설정 (환경 변수에서 가져오거나 기본값 사용)
        port_env = os.getenv("PORT")
        if port_env:
            self.port = int(port_env)
    
    def get_reload_dirs(self):
        """개발 모드에서 감시할 디렉토리 목록"""
        return [
            "api", "config", "core", "routers", 
            "services", "flows", "tools", "utils"
        ]
    
    def get_reload_excludes(self):
        """개발 모드에서 제외할 디렉토리/파일 목록"""
        return [
            ".*", ".py[cod]", "__pycache__", ".env", 
            ".venv", ".git", "output", "gitsync"
        ]
    
    def run(self):
        """서버 실행"""
        self.load_environment()
        
        print(f"🚀 Starting server in {'development (hot-reload enabled)' if self.is_development else 'production'} mode.")
        print(f"📍 Server will be available at http://{self.host}:{self.port}")
        
        # 로깅 설정을 uvicorn에 직접 전달
        log_config = get_simple_logging_config()
        
        uvicorn.run(
            "main:app",
            host=self.host,
            port=self.port,
            reload=self.is_development,
            reload_dirs=self.get_reload_dirs() if self.is_development else None,
            reload_excludes=self.get_reload_excludes() if self.is_development else None,
            access_log=True,
            log_level="info",
            log_config=log_config
        )


def run_server():
    """서버 실행 함수"""
    runner = ServerRunner()
    runner.run()


if __name__ == "__main__":
    run_server()
