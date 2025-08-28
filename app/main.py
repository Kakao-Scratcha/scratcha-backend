# backend/main.py

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware  # CORS 미들웨어 추가
from starlette.middleware.sessions import SessionMiddleware  # SessionMiddleware 추가
from db.session import engine
from contextlib import asynccontextmanager  # asynccontextmanager 임포트

from app.routers import users_router, auth_router, application_router, api_key_router, captcha_router, usage_stats_router
from app.admin.admin import setup_admin
from app.admin.auth import AdminAuth
from app.core.config import settings  # settings 객체 임포트
# Import scheduler functions
from app.tasks.scheduler import start_scheduler, shutdown_scheduler

# Define the lifespan context manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    print("Starting scheduler...")
    start_scheduler()
    yield
    # Shutdown event
    print("Shutting down scheduler...")
    shutdown_scheduler()

app = FastAPI(
    title="Dashboard API",
    description="scratcha API 서버",
    version="0.1.0",
    lifespan=lifespan  # Add lifespan to FastAPI app
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 모델 유효성 검사 오류에 대한 커스텀 핸들러.
    오류 메시지를 더 읽기 쉬운 형식으로 재구성합니다.
    """
    errors = {}
    for error in exc.errors():
        field_name = str(error['loc'][-1])
        message = error['msg']

        # 'Value error, ' 접두사 제거
        if error['type'] == 'value_error':
            message = message.removeprefix('Value error, ')

        errors[field_name] = message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "입력 값의 유효성 검사에 실패했습니다.", "errors": errors},
    )

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# SessionMiddleware를 추가하여 request.session을 사용할 수 있도록 합니다.
# SQLAdmin의 인증 백엔드(AdminAuth)가 세션에 접근하기 위해 필요합니다.
# secret_key는 세션 데이터를 암호화하는 데 사용됩니다. 실제 운영 환경에서는 환경 변수 등으로 관리해야 합니다.
app.add_middleware(SessionMiddleware,
                   secret_key=settings.SESSION_SECRET_KEY)  # 하드코딩된 시크릿 키

# SQLAdmin 관리자 인터페이스를 설정합니다.
# setup_admin 함수를 통해 모든 ModelView가 등록됩니다.
authentication_backend = AdminAuth(
    secret_key=settings.SESSION_SECRET_KEY)  # 하드코딩된 시크릿 키
admin = setup_admin(app, engine)
admin.authentication_backend = authentication_backend


@app.get("/")
def read_root():
    return {"message": "Welcome to Dashboard API! For user management and billing."}


# 라우터 등록
app.include_router(users_router.router, prefix="/api/dashboard")
app.include_router(auth_router.router, prefix="/api/dashboard")
app.include_router(application_router.router, prefix="/api/dashboard")
app.include_router(api_key_router.router, prefix="/api/dashboard")
app.include_router(usage_stats_router.router, prefix="/api/dashboard")
app.include_router(captcha_router.router, prefix="/api")
