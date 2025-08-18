from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from db.session import get_db
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.services.usage_stats_service import UsageStatsService
from app.schemas.usage_stats import (
    WeeklyUsageSummary,
    MonthlyUsageSummary,
    DailyUsageSummary,
    TotalRequests,
    ResultsCounts
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

    return UsageStatsService(UsageStatsRepository(db), ApiKeyRepository(db))


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

    return service.getMonthlySummary(currentUser.id)


@router.get(
    "/total-counts",
    response_model=TotalRequests,
    status_code=status.HTTP_200_OK,
    summary="사용자의 전체 캡챠 요청 수 조회",
    description="현재 인증된 사용자의 모든 API 키에 대한 전체 캡챠 요청 수를 합산하여 반환합니다.",
)
def get_total_requests(
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService),
):

    return service.getTotalRequests(userId=currentUser.id)


@router.get(
    "/results-counts",
    response_model=ResultsCounts,
    status_code=status.HTTP_200_OK,
    summary="사용자의 전체 캡챠 성공/실패 수 조회",
    description="현재 인증된 사용자의 모든 API 키에 대한 전체 캡챠 성공 및 실패 수를 합산하여 반환합니다.",
)
def get_results_counts(
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService),
):

    return service.getResultsCounts(userId=currentUser.id)


@router.get(
    "/api-keys/{keyId}/summary/daily",
    response_model=DailyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="API 키별 일간 사용량 요약",
    description="특정 API 키의 오늘과 어제의 사용량 및 그 추이를 조회합니다."
)
def get_daily_summary_by_api_key(
    keyId: int,
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    return service.getDailySummaryByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/summary/weekly",
    response_model=WeeklyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="API 키별 주간 사용량 요약",
    description="특정 API 키의 이번 주와 지난주의 사용량 및 그 추이를 조회합니다."
)
def get_weekly_summary_by_api_key(
    keyId: int,
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    return service.getWeeklySummaryByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/summary/monthly",
    response_model=MonthlyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="API 키별 월간 사용량 요약",
    description="특정 API 키의 이번 달과 지난달의 사용량 및 그 추이를 조회합니다."
)
def get_monthly_summary_by_api_key(
    keyId: int,
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    return service.getMonthlySummaryByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/total-counts",
    response_model=TotalRequests,
    status_code=status.HTTP_200_OK,
    summary="API 키별 전체 캡챠 요청 수 조회",
    description="특정 API 키의 전체 캡챠 요청 수를 반환합니다.",
)
def get_total_requests_by_api_key(
    keyId: int,
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    return service.getTotalRequestsByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/results-counts",
    response_model=ResultsCounts,
    status_code=status.HTTP_200_OK,
    summary="API 키별 전체 캡챠 성공/실패 수 조회",
    description="특정 API 키의 전체 캡챠 성공 및 실패 수를 합산하여 반환합니다.",
)
def get_results_counts_by_api_key(
    keyId: int,
    currentUser: User = Depends(get_current_user),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    return service.getResultsCountsByApiKey(keyId, currentUser)
