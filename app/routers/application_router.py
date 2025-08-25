# app/routers/application_router.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.models.user import User
from app.core.security import getCurrentUser
from db.session import get_db
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse, CountResponse
from app.services.application_service import ApplicationService

# API 라우터 객체 생성
router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)


def getApplicationService(db: Session = Depends(get_db)) -> ApplicationService:
    """
    FastAPI 의존성 주입을 통해 ApplicationService 인스턴스를 생성하고 반환합니다.

    Args:
        db (Session, optional): `get_db` 의존성에서 제공하는 데이터베이스 세션.

    Returns:
        ApplicationService: ApplicationService의 인스턴스.
    """
    return ApplicationService(db)


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 애플리케이션 생성",
    description="새로운 애플리케이션을 생성하고, 해당 애플리케이션에 대한 API 키를 함께 발급합니다.",
)
def createApplication(
    createAppSchema: ApplicationCreate,
    currentUser: User = Depends(getCurrentUser),
    appService: ApplicationService = Depends(getApplicationService)
):
    """
    새로운 애플리케이션을 생성합니다.

    Args:
        createAppSchema (ApplicationCreate): 생성할 애플리케이션의 데이터 (스키마).
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        appService (ApplicationService): 의존성으로 주입된 애플리케이션 서비스 객체.

    Returns:
        ApplicationResponse: 생성된 애플리케이션의 상세 정보 (발급된 API 키 포함).
    """
    # 1. 인증된 사용자와 요청된 정보를 바탕으로 애플리케이션 생성 서비스를 호출합니다.
    newApp = appService.createApplication(currentUser, createAppSchema)
    # 2. 생성된 애플리케이션 정보를 반환합니다.
    return newApp


@router.get(
    "/all",
    response_model=List[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="내 애플리케이션 목록 조회",
    description="현재 인증된 사용자가 소유한 모든 애플리케이션의 목록을 조회합니다.",
)
def getApplications(
    currentUser: User = Depends(getCurrentUser),
    appService: ApplicationService = Depends(getApplicationService)
):
    """
    현재 인증된 사용자의 모든 애플리케이션 목록을 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        appService (ApplicationService): 의존성으로 주입된 애플리케이션 서비스 객체.

    Returns:
        List[ApplicationResponse]: 사용자의 애플리케이션 목록.
    """
    # 1. 현재 사용자의 모든 애플리케이션을 조회하는 서비스를 호출합니다.
    userApps = appService.getApplications(currentUser)
    # 2. 조회된 애플리케이션 목록을 반환합니다.
    return userApps


@router.get(
    "/count",
    response_model=CountResponse,
    status_code=status.HTTP_200_OK,
    summary="내 애플리케이션 개수 조회",
    description="현재 인증된 사용자가 소유한 애플리케이션의 총 개수를 조회합니다.",
)
def getApplicationsCount(
    currentUser: User = Depends(getCurrentUser),
    appService: ApplicationService = Depends(getApplicationService)
):
    """
    현재 인증된 사용자의 애플리케이션 총 개수를 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        appService (ApplicationService): 의존성으로 주입된 애플리케이션 서비스 객체.

    Returns:
        CountResponse: 애플리케이션의 총 개수를 포함하는 응답.
    """
    # 1. 현재 사용자의 애플리케이션 개수를 조회하는 서비스를 호출합니다.
    appCount = appService.getApplicationsCount(currentUser)
    # 2. 조회된 개수를 반환합니다.
    return appCount


@router.get(
    "/{appId}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 애플리케이션 상세 조회",
    description="애플리케이션 ID를 사용하여 특정 애플리케이션의 상세 정보를 조회합니다.",
)
def getApplication(
    appId: int,
    currentUser: User = Depends(getCurrentUser),
    appService: ApplicationService = Depends(getApplicationService)
):
    """
    애플리케이션 ID(`appId`)로 특정 애플리케이션의 정보를 조회합니다.

    Args:
        appId (int): 조회할 애플리케이션의 고유 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        appService (ApplicationService): 의존성으로 주입된 애플리케이션 서비스 객체.

    Returns:
        ApplicationResponse: 조회된 애플리케이션의 상세 정보.
    """
    # 1. 특정 애플리케이션을 조회하는 서비스를 호출합니다.
    application = appService.getApplication(appId, currentUser)
    # 2. 조회된 애플리케이션 정보를 반환합니다.
    return application


@router.patch(
    "/{appId}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="애플리케이션 정보 업데이트",
    description="애플리케이션의 이름 또는 설명을 업데이트합니다.",
)
def updateApplication(
    appId: int,
    appUpdateSchema: ApplicationUpdate,
    currentUser: User = Depends(getCurrentUser),
    appService: ApplicationService = Depends(getApplicationService)
):
    """
    애플리케이션 ID(`appId`)에 해당하는 애플리케이션의 정보를 수정합니다.

    Args:
        appId (int): 수정할 애플리케이션의 고유 ID.
        appUpdateSchema (ApplicationUpdate): 업데이트할 애플리케이션의 데이터 (스키마).
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        appService (ApplicationService): 의존성으로 주입된 애플리케이션 서비스 객체.

    Returns:
        ApplicationResponse: 수정된 애플리케이션의 상세 정보.
    """
    # 1. 애플리케이션 정보를 업데이트하는 서비스를 호출합니다.
    updatedApp = appService.updateApplication(appId, currentUser, appUpdateSchema)
    # 2. 수정된 애플리케이션 정보를 반환합니다.
    return updatedApp


@router.delete(
    "/{appId}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="애플리케이션 삭제",
    description="지정된 애플리케이션을 소프트 삭제(soft-delete) 처리합니다.",
)
def deleteApplication(
    appId: int,
    currentUser: User = Depends(getCurrentUser),
    appService: ApplicationService = Depends(getApplicationService)
):
    """
    애플리케이션 ID(`appId`)에 해당하는 애플리케이션을 소프트 삭제합니다.

    Args:
        appId (int): 삭제할 애플리케이션의 고유 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        appService (ApplicationService): 의존성으로 주입된 애플리케이션 서비스 객체.

    Returns:
        ApplicationResponse: 삭제 처리된 애플리케이션의 상세 정보.
    """
    # 1. 애플리케이션을 삭제하는 서비스를 호출합니다.
    deletedApp = appService.deleteApplication(appId, currentUser)
    # 2. 삭제 처리된 애플리케이션 정보를 반환합니다.
    return deletedApp