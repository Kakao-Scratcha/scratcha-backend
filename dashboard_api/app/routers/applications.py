# dashboard_api/app/routers/applications.py

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from dashboard_api.app.core.security import get_current_user
from dashboard_api.app.routers.deps import get_db
from dashboard_api.app.schemas.application import ApplicationCreate, ApplicationResponse
from dashboard_api.app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service(db: Session = Depends(get_db)) -> ApplicationService:
    return ApplicationService(db)


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="애플리케이션 생성 및 API 키 발급",
    description="새로운 애플리케이션을 생성합니다.",
)
def create_application(
    application: ApplicationCreate,
    applicationService: ApplicationService = Depends(get_application_service),
    currentUser=Depends(get_current_user)
):
    return applicationService.create_application(currentUser.id, application)


@router.get(
    "/",
    response_model=List[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="내 애플리케이션 목록 조회",
    description="현재 인증된 사용자의 모든 애플리케이션 목록을 조회합니다.",
)
def get_applications(
    currentUser=Depends(get_current_user),
    applicationService: ApplicationService = Depends(get_application_service),

):
    return applicationService.get_applications_by_user_id(currentUser.id)
