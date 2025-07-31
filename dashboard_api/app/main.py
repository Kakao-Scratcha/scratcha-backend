# backend/dashboard_api/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # CORS 미들웨어 추가
from dashboard_api.app.routers import users, auth

app = FastAPI(
    title="Dashboard API",
    description="API for user management, application, API keys, statistics, and billing.",
    version="0.1.0"
)

# # 데이터베이스 테이블 생성 (첫 실행 시 필요)
# # 프로덕션에서는 Alembic과 같은 마이그레이션 도구를 사용하는 것이 권장됩니다.
# Base.metadata.create_all(bind=engine)

# CORS 미들웨어 설정 (개발 환경용)
origins = [
    "http://localhost",
    "http://localhost:3000",  # 프론트엔드 개발 서버 URL
    "http://localhost:80",  # Nginx
    "http://127.0.0.1:80",  # Nginx
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


@app.get("/")
def read_root():
    return {"message": "Welcome to Dashboard API! For user management and billing."}


# 라우터 등록
app.include_router(users.router, prefix="/api/dashboard")
app.include_router(auth.router, prefix="/api/dashboard")
