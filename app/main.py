from fastapi import FastAPI, Request, status
import logging.config
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from db.session import engine
from app.routers import payment_router, users_router, auth_router, application_router, api_key_router, captcha_router, usage_stats_router
from app.admin.admin import setup_admin
from app.admin.auth import AdminAuth
from app.core.config import settings
from app.tasks.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    print("이벤트 스케줄러 시작...")
    logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
    start_scheduler()
    yield
    # Shutdown event
    print("이벤트 스케줄러 종료...")
    shutdown_scheduler()

app = FastAPI(
    title="Dashboard API",
    description="scratcha API 서버",
    version="0.1.0",
    lifespan=lifespan  # Add lifespan to FastAPI app
)


# 디버깅을 위해 모든 요청 헤더를 로깅하는 미들웨어
@app.middleware("http")
async def log_headers_middleware(request: Request, call_next):
    logging.info(f"Request Headers: {request.headers}")
    response = await call_next(request)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 모델 유효성 검사 오류에 대한 커스텀 핸들러.
    첫 번째 오류 메시지를 detail 필드에 직접 담아 응답합니다.
    """
    error_list = exc.errors()
    if not error_list:
        # 오류 목록이 비어있는 드문 경우
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "입력 값의 유효성 검사에 실패했습니다."},
        )

    # 첫 번째 오류 정보를 가져옵니다.
    first_error = error_list[0]
    message = first_error['msg']

    # 'Value error, ' 접두사 제거
    if first_error['type'] == 'value_error':
        message = message.removeprefix('Value error, ')

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": message},
    )

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# ProxyHeadersMiddleware는 리버스 프록시(예: Nginx, Caddy) 뒤에서 FastAPI 애플리케이션을 실행할 때 필요합니다.
# 이 미들웨어는 'X-Forwarded-For' 및 'X-Forwarded-Proto'와 같은 헤더를 처리하여,
# request.url의 scheme (http 또는 https)과 client host/ip를 올바르게 식별하도록 돕습니다.
# 이를 통해 HTTPS 환경에서 발생하는 혼합 콘텐츠(Mixed Content) 오류를 해결할 수 있습니다.
# trusted_hosts에 운영 도메인을 명시하여, 신뢰할 수 있는 프록시로부터의 요청만 허용합니다.
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=["api.scratcha.cloud", "*.scratcha.cloud"]
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
# admin.base_url = "/admin"


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
app.include_router(payment_router.router, prefix="/api")  # payment_router 추가

# 정적 파일 서빙 설정
# app.mount("/api/payments", StaticFiles(directory="pg/public"),
#           name="payments_static")
