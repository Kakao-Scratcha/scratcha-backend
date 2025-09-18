# Scratcha Backend

본 프로젝트는 Scratcha 서비스의 백엔드 API 서버입니다.

## 1. 기술 스택 (Tech Stack)

-   **Language**: Python 3.8+
-   **Framework**: FastAPI
-   **ORM**: SQLAlchemy
-   **Database**: MySQL
-   **Database Migration**: Alembic
-   **Async Tasks**: Celery
-   **Message Broker**: RabbitMQ
-   **Deployment**: Docker

## 2. 프로젝트 구조 (Project Structure)

```
.
├── alembic/              # Alembic 데이터베이스 마이그레이션
├── app/
│   ├── admin/            # Admin 페이지 관련 (FastAPI-Admin)
│   ├── core/             # 설정, 보안 등 핵심 모듈
│   ├── models/           # SQLAlchemy DB 모델
│   ├── repositories/     # DB 데이터 접근 로직
│   ├── routers/          # API 엔드포인트 라우터
│   ├── schemas/          # Pydantic 데이터 검증 스키마
│   ├── services/         # 비즈니스 로직
│   └── tasks/            # Celery 비동기 작업
├── db/                   # DB 세션 및 초기화
├── requirements.txt      # Python 의존성 목록
├── docker-compose.yml    # Docker Compose 설정
├── Dockerfile            # Docker 이미지 설정
└── alembic.ini           # Alembic 설정 파일
```

## 3. 설치 및 설정 (Installation & Set up)

### 1) 가상환경 및 의존성 설치

```bash
# Python 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2) 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래 내용을 기반으로 값을 설정합니다.

```env
# JWT
SECRET_KEY=your-jwt-secret-key

# Database (MySQL)
DATABASE_URL=mysql+pymysql://user:password@host:port/dbname

# RabbitMQ (Celery Broker)
RABBITMQ_USER=your-rabbitmq-user
RABBITMQ_PASSWORD=your-rabbitmq-password
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_VHOST=/

# Celery Backend (Optional, for storing results)
CELERY_RESULT_BACKEND=rpc://


# Toss Payments
TOSS_SECRET_KEY=your-toss-payments-secret-key

# KS3 (Object Storage)
KS3_ENABLE=1
KS3_ENDPOINT=
KS3_REGION=ap-northeast-2
KS3_BUCKET=
KS3_ACCESS_KEY=
KS3_SECRET_KEY=
KS3_PREFIX=
KS3_FORCE_PATH_STYLE=1
KS3_BASE_URL=
```

## 4. 실행 (Running the Application)

### 개발 서버

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose 사용

```bash
docker-compose up -d
```

## 5. 데이터베이스 마이그레이션 (Database Migration)

Alembic을 사용하여 데이터베이스 스키마를 관리합니다.

```bash
# 새로운 마이그레이션 파일 생성
alembic revision --autogenerate -m "migration_message"

# 데이터베이스에 마이그레이션 적용
alembic upgrade head
```

## 6. API 문서 (API Documentation)

개발 서버 실행 후, 아래 URL에서 API 문서를 확인할 수 있습니다.

-   **Swagger UI**: http://localhost:8000/docs
