# app/routers/captcha_router.py

from fastapi import APIRouter, Depends, status, Request, Header, Response
from sqlalchemy.orm import Session
from typing import Annotated
from celery.result import AsyncResult

# 프로젝트 의존성 및 모델, 서비스 임포트
from app.core.security import getValidApiKey
from app.models.api_key import ApiKey
from db.session import get_db
from app.schemas.captcha import CaptchaProblemResponse, CaptchaVerificationRequest, CaptchaVerificationResponse, CaptchaTaskResponse
from app.services.captcha_service import CaptchaService
from app.celery_app import celery_app


# API 라우터 객체 생성
router = APIRouter(
    prefix="/captcha",
    tags=["Captcha"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/problem",
    response_model=CaptchaProblemResponse,
    status_code=status.HTTP_200_OK,
    summary="새로운 캡챠 문제 요청",
    description="유효한 API 키로 새로운 캡챠 문제(이미지, 선택지 등)와 문제 해결을 위한 고유 토큰을 발급받습니다."
)
def getCaptchaProblem(
    request: Request,
    apiKey: ApiKey = Depends(getValidApiKey),
    db: Session = Depends(get_db)
):
    """
    새로운 캡챠 문제를 생성하고 클라이언트에게 반환합니다.

    이 엔드포인트는 'X-Api-Key' 헤더를 통해 유효한 API 키를 받아야만 호출할 수 있습니다.

    Args:
        request (Request): FastAPI의 Request 객체. 클라이언트 IP와 User-Agent를 얻기 위해 사용됩니다.
        apiKey (ApiKey): `getValidApiKey` 의존성으로 주입된, 유효성이 검증된 API 키 객체.
        db (Session): `get_db` 의존성으로 주입된 데이터베이스 세션.

    Returns:
        CaptchaProblemResponse: 생성된 캡챠 문제의 상세 정보 (클라이언트 토큰, 이미지 URL, 프롬프트, 선택지).
    """
    captchaService = CaptchaService(db)
    ipAddress = request.client.host
    userAgent = request.headers.get("user-agent")
    newProblem = captchaService.generateCaptchaProblem(apiKey, ipAddress, userAgent)
    return newProblem


@router.post(
    "/verify",
    response_model=CaptchaTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="캡챠 답변 비동기 검증 요청",
    description="캡챠 답변을 비동기적으로 검증하는 작업을 시작하고 작업 ID를 반환합니다."
)
def verifyCaptchaAnswer(
    request: CaptchaVerificationRequest,
    fastApiRequest: Request,
    clientToken: Annotated[str, Header(alias="X-Client-Token")],
    db: Session = Depends(get_db)
):
    """
    사용자가 제출한 캡챠 답변의 검증을 비동기 작업으로 요청합니다.
    
    요청을 받으면 즉시 작업을 생성하고, 클라이언트에게는 작업 ID를 포함한 `202 Accepted` 응답을 보냅니다.
    실제 검증은 백그라운드에서 처리됩니다.

    Args:
        request (CaptchaVerificationRequest): 클라이언트가 제출한 캡챠 답변 데이터 (정답).
        fastApiRequest (Request): FastAPI의 Request 객체. 클라이언트 IP와 User-Agent를 얻기 위해 사용됩니다.
        clientToken (str): `X-Client-Token` 헤더로 전달되는 고유 클라이언트 토큰.
        db (Session): 데이터베이스 세션.

    Returns:
        CaptchaTaskResponse: 생성된 비동기 작업의 ID가 포함된 응답.
    """
    captchaService = CaptchaService(db)
    ipAddress = fastApiRequest.client.host
    userAgent = fastApiRequest.headers.get("user-agent")
    
    # 비동기 검증 서비스를 호출하고 작업 ID를 받습니다.
    taskId = captchaService.verifyCaptchaAnswerAsync(
        clientToken, request, ipAddress, userAgent)
        
    return CaptchaTaskResponse(taskId=taskId)


@router.get(
    "/verify/result/{taskId}",
    summary="캡챠 검증 결과 확인",
    description="작업 ID를 사용하여 비동기 캡챠 검증 결과를 확인합니다.",
    responses={
        200: {"description": "작업 성공", "model": CaptchaVerificationResponse},
        202: {"description": "작업이 아직 처리 중입니다."},
        500: {"description": "작업 실행 중 오류가 발생했습니다."}
    }
)
def getVerifyResult(taskId: str, response: Response):
    """
    비동기 캡챠 검증 작업의 결과를 조회합니다.

    클라이언트는 `/verify` 요청으로 받은 작업 ID(taskId)를 사용하여
    이 엔드포인트를 주기적으로(polling) 호출하여 결과를 확인할 수 있습니다.

    Args:
        taskId (str): 확인할 작업의 ID.
        response (Response): FastAPI Response 객체. 상태 코드를 동적으로 변경하기 위해 사용됩니다.

    Returns:
        Union[CaptchaVerificationResponse, dict]: 작업 상태에 따라 다른 응답을 반환합니다.
            - 성공(SUCCESS): `CaptchaVerificationResponse` 모델에 따른 검증 결과.
            - 처리 중(PENDING): `202 Accepted` 상태 코드와 함께 처리 중 메시지.
            - 실패(FAILURE): `500 Internal Server Error` 상태 코드와 함께 오류 메시지.
    """
    # Celery의 AsyncResult를 사용하여 작업 ID에 해당하는 결과를 조회합니다.
    taskResult = AsyncResult(taskId, app=celery_app)

    # 작업이 완료되었는지 확인합니다.
    if taskResult.ready():
        # 작업이 성공적으로 완료되었는지 확인합니다.
        if taskResult.successful():
            # 성공했다면, 작업의 반환값(dict)을 CaptchaVerificationResponse 모델로 변환하여 반환합니다.
            return CaptchaVerificationResponse(**taskResult.result)
        else:
            # 작업이 실패했다면, 500 오류를 반환합니다.
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"message": "작업 실행 중 오류가 발생했습니다.", "error": str(taskResult.info)}
    else:
        # 작업이 아직 처리 중이라면, 202 상태 코드를 반환합니다.
        response.status_code = status.HTTP_202_ACCEPTED
        return {"message": "작업이 아직 처리 중입니다."}