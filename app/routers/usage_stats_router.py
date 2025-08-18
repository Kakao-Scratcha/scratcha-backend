from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from db.session import get_db
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.services.usage_stats_service import UsageStatsService
from app.schemas.usage_stats import (
    UsageStatsResponse,
    WeeklyUsageSummary,
    MonthlyUsageSummary,
    DailyUsageSummary
)
from app.core.security import get_current_user
from app.models.user import User

# APIRouter 인스턴스 생성
router = APIRouter(
    prefix="/usage-stats",
    tags=["usage-stats"],
    responses={404: {"description": "Not found"}},
)

# UsageStatsService 의존성 주입


def getUsageStatsService(db: Session = Depends(get_db)) -> UsageStatsService:
    """
    사용량 통계 서비스 인스턴스를 생성하고, 데이터베이스 세션을 주입합니다.
    """
    return UsageStatsService(UsageStatsRepository(db))


@router.get(
    "/summary/daily",
    response_model=DailyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="일간 사용량 요약",
    description="오늘과 어제의 사용량 및 그 추이를 조회합니다."
)
def getDailySummary(
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    오늘과 어제의 총 사용량 및 증감률을 요약하여 제공하는 엔드포인트입니다.

    Args:
        currentUser (User): 현재 인증된 사용자 정보.
        service (UsageStatsService): 사용량 통계 서비스 객체.

    Returns:
        DailyUsageSummary: 일간 사용량 요약 객체.
    """
    return service.getDailySummary(currentUser.id)


@router.get(
    "/summary/weekly",
    response_model=WeeklyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="주간 사용량 요약",
    description="이번 주와 지난주의 사용량 및 그 추이를 조회합니다."
)
def getWeeklySummary(
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    이번 주와 지난주의 총 사용량 및 증감률을 요약하여 제공하는 엔드포인트입니다.

    Args:
        currentUser (User): 현재 인증된 사용자 정보.
        service (UsageStatsService): 사용량 통계 서비스 객체.

    Returns:
        WeeklyUsageSummary: 주간 사용량 요약 객체.
    """
    return service.getWeeklySummary(currentUser.id)


@router.get(
    "/summary/monthly",
    response_model=MonthlyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="월간 사용량 요약",
    description="이번 달과 지난달의 사용량 및 그 추이를 조회합니다."
)
def getMonthlySummary(
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    이번 달과 지난달의 총 사용량 및 증감률을 요약하여 제공하는 엔드포인트입니다.

    Args:
        currentUser (User): 현재 인증된 사용자 정보.
        service (UsageStatsService): 사용량 통계 서비스 객체.

    Returns:
        MonthlyUsageSummary: 월간 사용량 요약 객체.
    """
    return service.getMonthlySummary(currentUser.id)