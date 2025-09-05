from fastapi import FastAPI, Request, status, HTTPException
import logging.config
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from starlette_prometheus import PrometheusMiddleware, metrics


from db.session import engine
from app.routers import payment_router, users_router, auth_router, application_router, api_key_router, captcha_router, usage_stats_router, contact_router
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


# 로거 설정
logger = logging.getLogger(__name__)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTPException이 발생했을 때, 오류 내용을 로깅하기 위한 커스텀 핸들러입니다.
    """
    logger.error(
        f"HTTP 예외 발생: {request.method} {request.url.path} {exc.status_code} {exc.detail}"
    )
    # 기본 HTTPException 동작과 동일하게 JSON 응답을 반환합니다.
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
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

# Prometheus 미들웨어를 추가합니다.
app.add_middleware(PrometheusMiddleware)

# SQLAdmin 관리자 인터페이스를 설정합니다.
# setup_admin 함수를 통해 모든 ModelView가 등록됩니다.
authentication_backend = AdminAuth(
    secret_key=settings.SESSION_SECRET_KEY)
admin = setup_admin(app, engine)
admin.authentication_backend = authentication_backend


@app.get("/")
def read_root():
    return {"message": "Welcome to Dashboard API! For user management and billing."}


# 라우터 등록
app.include_router(users_router.router,
                   prefix="/api/dashboard")        # 유저관리 라우터
app.include_router(auth_router.router,
                   prefix="/api/dashboard")         # 로그인(인증) 라우터
app.include_router(application_router.router,
                   prefix="/api/dashboard")  # 애플리케이션 라우터
app.include_router(api_key_router.router,
                   prefix="/api/dashboard")      # API 키 라우터
app.include_router(usage_stats_router.router,
                   prefix="/api/dashboard")  # 사용량 라우터
app.include_router(captcha_router.router,
                   prefix="/api")                # 캡챠 라우터
app.include_router(payment_router.router,
                   prefix="/api")                # 결제 라우터
app.include_router(contact_router.router,
                   prefix="/api")                # 문의 라우터

# 메트릭 엔드포인트를 추가합니다.
app.add_route("/metrics", metrics)
