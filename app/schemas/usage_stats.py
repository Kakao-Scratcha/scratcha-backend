from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import List

# 기간별 통계 조회


class StatisticsData(BaseModel):
    """그래프용 사용량 통계"""
    date: str = Field(..., description="데이터 포인트의 날짜 또는 시간 (ISO 8601 형식)",
                      example="2025-08-26T10:00:00")
    totalRequests: int = Field(..., description="총 요청 수", example=150)
    successCount: int = Field(..., description="성공 수", example=120)
    failCount: int = Field(..., description="실패 수", example=20)
    timeoutCount: int = Field(..., description="타임아웃 수", example=10)


class StatisticsDataResponse(BaseModel):
    """데이터 응답(그래프)"""
    keyId: int | None = Field(...,
                              description="로그를 조회한 API 키의 ID. 미지정 시 사용자 전체 로그", example=17)
    periodType: str = Field(..., description="조회 기간 타입", example="daily")
    data: List[StatisticsData] = Field(...,
                                       description="기간별 사용량 데이터 배열")


# 기간별 로그 조회

class StatisticsLog(BaseModel):
    """로그용 사용량 통계"""
    id: int = Field(..., description="캡챠 로그의 고유 식별자", example=1)
    appName: str = Field(..., description="요청이 발생한 애플리케이션의 이름",
                         example="내 첫번째 애플리케이션")
    key: str = Field(..., description="사용된 API 키",
                     example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    date: str = Field(..., description="캡챠가 호출된 시간 (문제 생성 시간)",
                      example="2024-08-21")
    result: str = Field(..., description="캡챠 해결 결과 (예: 'success', 'fail', 'timeout')",
                        example="success")
    ratency: int = Field(..., description="응답 시간 (밀리초)", example=150)


class StatisticsLogResponse(BaseModel):
    """데이터 응답(로그)"""
    keyId: int | None = Field(...,
                              description="통계 기준 API 키 ID (전체 합산 시 null)", example=17)
    periodType: str = Field(..., description="조회 기간 타입", example="daily")
    data: List[StatisticsLog] = Field(..., description="기간별 로그 데이터 배열")
    total: int = Field(..., description="전체 로그 개수", example=100)
    page: int = Field(..., description="현재 페이지 번호", example=1)
    size: int = Field(..., description="페이지 당 항목 수", example=10)

# 기간별 캡챠 요청 수


class RequestCountSummary(BaseModel):
    """캡챠 요청 수 요약"""
    currentCount: int = Field(..., description="현재 기간 호출량", example=1234)
    previousCount: int = Field(..., description="이전 기간 호출량", example=1100)
    rate: float = Field(..., description="이전 기간 대비 증감률 (%)", example=12.18)


class RequestCountSummaryResponse(BaseModel):
    """캡챠 요청 수 요약 응답"""
    keyId: int | None = Field(...,
                              description="조회한 API 키의 ID. 미지정 시 사용자 전체 합산", example=17)
    periodType: str = Field(...,
                            description="조회 기간 타입 (daily, weekly, monthly)", example="daily")
    data: RequestCountSummary

#  전체 캡챠 요청 수


class RequestTotalResponse(BaseModel):
    """전체 캡챠 요청 수 응답"""
    keyId: int | None = Field(...,
                              description="조회한 API 키의 ID. 미지정 시 사용자 전체 합산", example=17)
    count: int = Field(..., description="총 요청 수", example=150)
