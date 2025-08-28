from pytz import timezone
import os
from dotenv import load_dotenv

load_dotenv() # 환경 변수 로드

class Settings:
    # 시간대 설정
    TIMEZONE = timezone("Asia/Seoul")

    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key") # 실제 운영 환경에서는 반드시 환경 변수로 설정
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 애플리케이션 설정
    MAX_APPLICATIONS_PER_USER: dict = {
        "free": 1,
        "starter": 3,
        "pro": 5,
        "enterprise": -1  # 무제한
    }

    # CORS 설정
    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",  # 프론트엔드 개발 서버 URL
        "http://localhost:80",  # Nginx
        "http://127.0.0.1:80",  # Nginx
    ]

    # 세션 및 관리자 인증 시크릿 키
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "your-super-secret-key") # 실제 운영 환경에서는 환경 변수로 설정

    # 캡챠 타임아웃 설정 (분)
    CAPTCHA_TIMEOUT_MINUTES: int = 3

    # 사용자 이름 정규식 패턴
    USER_NAME_REGEX_PATTERN: str = r"^[가-힣a-zA-Z0-9._-]+$" # re.compile은 사용하지 않고 패턴 문자열만 관리

settings = Settings()
