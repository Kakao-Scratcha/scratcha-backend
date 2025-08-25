from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import List, Annotated


class UsageStatsResponse(BaseModel):
    """일별 API 사용량 통계 데이터 스키마"""
    date: Annotated[date,
                    Field(..., description="통계 날짜", example="2024-08-21")]
    captchaTotalRequests: int = Field(...,
                                      description="총 캡챠 요청 수", example=1500)
    captchaSuccessCount: int = Field(..., description="캡챠 성공 수", example=1400)
    captchaFailCount: int = Field(..., description="캡챠 실패 수", example=100)
    captchaTimeoutCount: int = Field(..., description="캡챠 타임아웃 수", example=50)
    avgResponseTimeMs: float = Field(...,
                                     description="평균 응답 시간 (ms)", example=120.5)


class DailyUsageSummary(BaseModel):
    """일간 사용량 요약 스키마"""
    todayRequests: int = Field(..., description="오늘의 총 요청 수", example=120)
    yesterdayRequests: int = Field(..., description="어제의 총 요청 수", example=100)
    ratioVsYesterday: float = Field(...,
                                    description="어제 대비 요청 수 증감 비율 (%)", example=20.0)
    captchaSuccessCount: int = Field(...,
                                     description="오늘의 캡챠 성공 수", example=110)
    captchaFailCount: int = Field(..., description="오늘의 캡챠 실패 수", example=10)


class WeeklyUsageSummary(BaseModel):
    """주간 사용량 요약 스키마"""
    thisWeekRequests: int = Field(..., description="이번 주 총 요청 수", example=840)
    lastWeekRequests: int = Field(..., description="지난주 총 요청 수", example=700)
    ratioVsLastWeek: float = Field(...,
                                   description="지난주 대비 요청 수 증감 비율 (%)", example=20.0)
    captchaSuccessCount: int = Field(...,
                                     description="이번 주 캡챠 성공 수", example=800)
    captchaFailCount: int = Field(..., description="이번 주 캡챠 실패 수", example=40)


class MonthlyUsageSummary(BaseModel):
    """월간 사용량 요약 스키마"""
    thisMonthRequests: int = Field(...,
                                   description="이번 달 총 요청 수", example=3600)
    lastMonthRequests: int = Field(..., description="지난달 총 요청 수", example=3000)
    ratioVsLastMonth: float = Field(...,
                                    description="지난달 대비 요청 수 증감 비율 (%)", example=20.0)
    captchaSuccessCount: int = Field(...,
                                     description="이번 달 캡챠 성공 수", example=3400)
    captchaFailCount: int = Field(..., description="이번 달 캡챠 실패 수", example=200)


class TotalRequests(BaseModel):
    """유저의 전체 캡챠 요청 수"""
    totalRequests: int = Field(...,
                               description="지금까지의 총 캡챠 요청 수", example=15000)


class ResultsCounts(BaseModel):
    """성공 수, 실패 수 스키마"""
    captchaSuccessCount: int = Field(...,
                                     description="총 캡챠 성공 수", example=14000)
    captchaFailCount: int = Field(..., description="총 캡챠 실패 수", example=1000)


class UsageDataLog(BaseModel):
    """사용량 데이터 로그"""
    id: int = Field(..., description="캡챠 로그의 고유 식별자", example=1)
    appName: str = Field(..., description="요청이 발생한 애플리케이션의 이름",
                         example="내 첫번째 애플리케이션")
    key: str = Field(..., description="사용된 API 키",
                     example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    date: datetime = Field(..., description="캡챠가 호출된 시간 (문제 생성 시간)",
                           example="2024-08-21T10:00:00")
    result: str = Field(..., description="캡챠 해결 결과 (예: 'success', 'fail', 'timeout')",
                        example="success")
    ratency: int = Field(..., description="응답 시간 (밀리초)", example=150)


class PaginatedUsageDataLog(BaseModel):
    """페이지네이션된 사용량 데이터 로그"""
    items: List[UsageDataLog] = Field(..., description="현재 페이지의 사용량 데이터 로그 목록")
    total: int = Field(..., description="전체 로그 개수", example=100)
    page: int = Field(..., description="현재 페이지 번호", example=1)
    size: int = Field(..., description="페이지 당 항목 수", example=10)
