# Backend

백엔드 API 서버 디렉토리입니다.

## 기술 스택

- Python 3.8+
- FastAPI
- SQLAlchemy
- PostgreSQL/MongoDB
- Redis
- Celery (비동기 작업)

## 개발 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 테스트 실행
pytest
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 폴더 구조

```
backend/
├── app/
│   ├── api/           # API 라우터
│   ├── core/          # 설정, 보안 등 핵심 모듈
│   ├── models/        # 데이터베이스 모델
│   ├── schemas/       # Pydantic 스키마
│   ├── services/      # 비즈니스 로직
│   └── utils/         # 유틸리티 함수
├── tests/             # 테스트 파일
├── alembic/           # 데이터베이스 마이그레이션
├── requirements.txt   # Python 의존성
└── main.py           # 애플리케이션 진입점
```

## 환경 변수

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
``` 