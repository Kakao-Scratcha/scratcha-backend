from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from db.session import get_db
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.services.usage_stats_service import UsageStatsService
from app.schemas.usage_stats import (
    WeeklyUsageSummary,
    MonthlyUsageSummary,
    DailyUsageSummary,
    TotalRequests,
    ResultsCounts,
    UsageDataLog,
    PaginatedUsageDataLog
)
from app.core.security import getCurrentUser
from app.models.user import User

# APIRouter 인스턴스 생성
router = APIRouter(
    prefix="/usage-stats",
    tags=["Usage Stats"],
    responses={404: {"description": "Not found"}},
)


def getUsageStatsService(db: Session = Depends(get_db)) -> UsageStatsService:
    """
    FastAPI 의존성 주입을 통해 UsageStatsService 인스턴스를 생성하고 반환합니다.

    Args:
        db (Session, optional): `get_db` 의존성에서 제공하는 데이터베이스 세션.

    Returns:
        UsageStatsService: UsageStatsService의 인스턴스.
    """
    return UsageStatsService(UsageStatsRepository(db), ApiKeyRepository(db))


@router.get(
    "/summary/daily",
    response_model=DailyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="일간 사용량 요약 조회",
    description="현재 인증된 사용자의 오늘과 어제의 캡챠 사용량 및 그 추이를 조회합니다."
)
def getDailySummary(
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    현재 인증된 사용자의 일간 캡챠 사용량 요약을 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        DailyUsageSummary: 오늘과 어제의 사용량 및 추이 요약.
    """
    # 1. 사용량 통계 서비스의 일간 요약 조회 메서드를 호출합니다.
    return service.getDailySummary(currentUser.id)


@router.get(
    "/summary/weekly",
    response_model=WeeklyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="주간 사용량 요약 조회",
    description="현재 인증된 사용자의 이번 주와 지난주의 캡챠 사용량 및 그 추이를 조회합니다."
)
def getWeeklySummary(
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    현재 인증된 사용자의 주간 캡챠 사용량 요약을 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        WeeklyUsageSummary: 이번 주와 지난주의 사용량 및 추이 요약.
    """
    # 1. 사용량 통계 서비스의 주간 요약 조회 메서드를 호출합니다.
    return service.getWeeklySummary(currentUser.id)


@router.get(
    "/summary/monthly",
    response_model=MonthlyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="월간 사용량 요약 조회",
    description="현재 인증된 사용자의 이번 달과 지난달의 캡챠 사용량 및 그 추이를 조회합니다."
)
def getMonthlySummary(
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    현재 인증된 사용자의 월간 캡챠 사용량 요약을 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        MonthlyUsageSummary: 이번 달과 지난달의 사용량 및 추이 요약.
    """
    # 1. 사용량 통계 서비스의 월간 요약 조회 메서드를 호출합니다.
    return service.getMonthlySummary(currentUser.id)


@router.get(
    "/total-counts",
    response_model=TotalRequests,
    status_code=status.HTTP_200_OK,
    summary="사용자의 총 캡챠 요청 수 조회",
    description="현재 인증된 사용자의 모든 API 키에 대한 전체 기간 동안의 총 캡챠 요청 수를 합산하여 반환합니다.",
)
def getTotalRequests(
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    """
    현재 인증된 사용자의 전체 기간 동안의 총 캡챠 요청 수를 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        TotalRequests: 총 캡챠 요청 수를 포함하는 응답.
    """
    # 1. 사용량 통계 서비스의 총 요청 수 조회 메서드를 호출합니다.
    return service.getTotalRequests(userId=currentUser.id)


@router.get(
    "/results-counts",
    response_model=ResultsCounts,
    status_code=status.HTTP_200_OK,
    summary="사용자의 캡챠 성공/실패 수 조회",
    description="현재 인증된 사용자의 모든 API 키에 대한 전체 기간 동안의 캡챠 성공 및 실패 수를 합산하여 반환합니다.",
)
def getResultsCounts(
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    """
    현재 인증된 사용자의 전체 기간 동안의 캡챠 성공 및 실패 수를 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        ResultsCounts: 캡챠 성공 및 실패 수를 포함하는 응답.
    """
    # 1. 사용량 통계 서비스의 성공/실패 수 조회 메서드를 호출합니다.
    return service.getResultsCounts(userId=currentUser.id)


@router.get(
    "/api-keys/{keyId}/summary/daily",
    response_model=DailyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="API 키별 일간 사용량 요약 조회",
    description="특정 API 키의 오늘과 어제의 캡챠 사용량 및 그 추이를 조회합니다."
)
def getDailySummaryByApiKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    특정 API 키의 일간 캡챠 사용량 요약을 조회합니다.

    Args:
        keyId (int): 조회할 API 키의 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        DailyUsageSummary: 오늘과 어제의 사용량 및 추이 요약.
    """
    # 1. 사용량 통계 서비스의 API 키별 일간 요약 조회 메서드를 호출합니다.
    return service.getDailySummaryByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/summary/weekly",
    response_model=WeeklyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="API 키별 주간 사용량 요약 조회",
    description="특정 API 키의 이번 주와 지난주의 캡챠 사용량 및 그 추이를 조회합니다."
)
def getWeeklySummaryByApiKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    특정 API 키의 주간 캡챠 사용량 요약을 조회합니다.

    Args:
        keyId (int): 조회할 API 키의 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        WeeklyUsageSummary: 이번 주와 지난주의 사용량 및 추이 요약.
    """
    # 1. 사용량 통계 서비스의 API 키별 주간 요약 조회 메서드를 호출합니다.
    return service.getWeeklySummaryByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/summary/monthly",
    response_model=MonthlyUsageSummary,
    status_code=status.HTTP_200_OK,
    summary="API 키별 월간 사용량 요약 조회",
    description="특정 API 키의 이번 달과 지난달의 캡챠 사용량 및 그 추이를 조회합니다."
)
def getMonthlySummaryByApiKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService)
):
    """
    특정 API 키의 월간 캡챠 사용량 요약을 조회합니다.

    Args:
        keyId (int): 조회할 API 키의 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        MonthlyUsageSummary: 이번 달과 지난달의 사용량 및 추이 요약.
    """
    # 1. 사용량 통계 서비스의 API 키별 월간 요약 조회 메서드를 호출합니다.
    return service.getMonthlySummaryByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/total-counts",
    response_model=TotalRequests,
    status_code=status.HTTP_200_OK,
    summary="API 키별 총 캡챠 요청 수 조회",
    description="특정 API 키의 전체 기간 동안의 총 캡챠 요청 수를 반환합니다.",
)
def getTotalRequestsByApiKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    """
    특정 API 키의 전체 기간 동안의 총 캡챠 요청 수를 조회합니다.

    Args:
        keyId (int): 조회할 API 키의 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        TotalRequests: 총 캡챠 요청 수를 포함하는 응답.
    """
    # 1. 사용량 통계 서비스의 API 키별 총 요청 수 조회 메서드를 호출합니다.
    return service.getTotalRequestsByApiKey(keyId, currentUser)


@router.get(
    "/api-keys/{keyId}/results-counts",
    response_model=ResultsCounts,
    status_code=status.HTTP_200_OK,
    summary="API 키별 캡챠 성공/실패 수 조회",
    description="특정 API 키의 전체 기간 동안의 캡챠 성공 및 실패 수를 합산하여 반환합니다.",
)
def getResultsCountsByApiKey(
    keyId: int,
    currentUser: User = Depends(getCurrentUser),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    """
    특정 API 키의 전체 기간 동안의 캡챠 성공 및 실패 수를 조회합니다.

    Args:
        keyId (int): 조회할 API 키의 ID.
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        ResultsCounts: 캡챠 성공 및 실패 수를 포함하는 응답.
    """
    # 1. 사용량 통계 서비스의 API 키별 성공/실패 수 조회 메서드를 호출합니다.
    return service.getResultsCountsByApiKey(keyId, currentUser)


@router.get(
    "/logs",
    response_model=PaginatedUsageDataLog,
    status_code=status.HTTP_200_OK,
    summary="사용량 데이터 로그 조회",
    description="현재 인증된 사용자 또는 특정 API 키에 대한 캡챠 사용량 로그를 페이지네이션하여 조회합니다.",
)
def getUsageDataLogs(
    currentUser: User = Depends(getCurrentUser),
    keyId: int = Query(None, description="특정 API 키의 로그만 조회할 경우 사용 (없으면 전체 로그 조회)"),
    skip: int = Query(0, ge=0, description="건너뛸 레코드(항목)의 수, 페이지네이션에서 현재 페이지의 시작 오프셋을 지정"),
    limit: int = Query(100, ge=1, le=100, description="한 번에 가져올 최대 레코드의 수"),
    service: UsageStatsService = Depends(getUsageStatsService),
):
    """
    사용자 또는 API 키별 캡챠 사용량 로그를 페이지네이션하여 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        keyId (int, optional): 필터링할 API 키의 ID. None이면 사용자 전체 로그 조회. Defaults to None.
        skip (int, optional): 건너뛸 레코드 수 (페이지네이션용). Defaults to 0.
        limit (int, optional): 가져올 최대 레코드 수 (페이지네이션용). Defaults to 100.
        service (UsageStatsService): 의존성으로 주입된 사용량 통계 서비스 객체.

    Returns:
        PaginatedUsageDataLog: 조회된 사용량 로그 리스트와 페이지네이션 정보를 포함하는 응답.
    """
    # 1. 사용량 통계 서비스의 사용량 로그 조회 메서드를 호출합니다.
    return service.getUsageData(currentUser, keyId, skip, limit)