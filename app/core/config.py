from pytz import timezone
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 환경 변수를 로드합니다.


class Settings:
    # 시간대 설정
    TIMEZONE = timezone("Asia/Seoul")

    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 애플리케이션 설정
    MAX_APPLICATIONS_PER_USER = 3

    # CORS 설정
    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",  # 프론트엔드 개발 서버 URL
        "http://localhost:80",  # Nginx
        "http://127.0.0.1:80",  # Nginx
    ]

    # 세션 및 관리자 인증 시크릿 키
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY")

    # 캡챠 타임아웃 설정 (분)
    CAPTCHA_TIMEOUT_MINUTES: int = 3

    # 데이터베이스 URL
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # 사용자 이름 정규식 패턴
    USER_NAME_REGEX_PATTERN: str = r"^[가-힣a-zA-Z0-9._-]+$"

    # 토스 페이먼츠 시크릿 키
    TOSS_SECRET_KEY: str = os.getenv("TOSS_SECRET_KEY")

    # 결제 정책 정의
    ALLOWED_PAYMENT_PLANS = {
        1000: 5000,
        10000: 40000,
        100000: 300000,
    }

    # --- 비동기 작업을 위한 Celery 및 RabbitMQ 설정 ---

    # RabbitMQ 접속 정보. .env 파일 또는 환경변수에서 값을 가져옵니다.
    # 기본값이 없으므로, 반드시 환경변수가 설정되어야 합니다.
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT"))
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST")

    # Celery가 사용할 메시지 브로커의 URL을 조합합니다.
    # 형식: amqp://{사용자이름}:{비밀번호}@{호스트}:{포트}/{가상호스트}
    CELERY_BROKER_URL: str = (
        f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASSWORD')}@"
        f"{os.getenv('RABBITMQ_HOST')}:{os.getenv('RABBITMQ_PORT')}"
        f"{os.getenv('RABBITMQ_VHOST')}"
    )
    # Celery 작업 결과를 저장할 백엔드를 설정합니다.
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

    # S3/KS3 설정
    KS3_ENDPOINT: str = os.getenv("KS3_ENDPOINT")
    KS3_REGION: str = os.getenv("KS3_REGION", "ap-northeast-2")
    KS3_BUCKET: str = os.getenv("KS3_BUCKET")
    KS3_ACCESS_KEY: str = os.getenv("KS3_ACCESS_KEY")
    KS3_SECRET_KEY: str = os.getenv("KS3_SECRET_KEY")
    KS3_PREFIX: str = os.getenv("KS3_PREFIX", "")
    KS3_FORCE_PATH_STYLE: bool = os.getenv("KS3_FORCE_PATH_STYLE", "1") == "1"

    KS3_BASE_URL: str = os.getenv("KS3_BASE_URL")

    @property
    def ENABLE_KS3(self) -> bool:
        _enable = os.getenv("KS3_ENABLE")
        if _enable is None:
            return all([self.KS3_BUCKET, self.KS3_ENDPOINT, self.KS3_ACCESS_KEY, self.KS3_SECRET_KEY])
        return _enable == "1"


# 설정 클래스의 인스턴스를 생성하여 애플리케이션 전체에서 사용합니다.
settings = Settings()