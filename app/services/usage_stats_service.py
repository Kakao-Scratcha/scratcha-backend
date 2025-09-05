from datetime import date, timedelta
import math
from fastapi import HTTPException, status
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.usage_stats import StatisticsDataResponse, StatisticsData, StatisticsLog, StatisticsLogResponse, RequestCountSummary, RequestCountSummaryResponse, RequestTotalResponse
from app.models.user import User
from typing import Optional, List
from datetime import datetime
from dateutil.relativedelta import relativedelta


class UsageStatsService:
    """
    사용량 통계 관련 비즈니스 로직을 처리하는 서비스 클래스입니다.
    이 클래스는 리포지토리를 통해 데이터베이스와 상호작용하고, 
    조회된 데이터를 비즈니스 요구사항에 맞게 가공하여 컨트롤러(라우터)에 반환합니다.
    """

    def __init__(self, repo: UsageStatsRepository, api_key_repo: ApiKeyRepository):
        """
        UsageStatsService의 생성자입니다.

        Args:
            repo (UsageStatsRepository): 사용량 통계 리포지토리 객체. 의존성 주입을 통해 제공됩니다.
            api_key_repo (ApiKeyRepository): API 키 리포지토리 객체. 의존성 주입을 통해 제공됩니다.
        """
        self.repo = repo
        self.api_key_repo = api_key_repo

    def _checkApiKeyOwner(self, keyId: int, currentUser: User):
        """
        API 키의 소유권을 확인하는 private 헬퍼 메소드입니다.
        요청한 사용자가 해당 API 키의 실제 소유자인지 확인하여, 권한이 없는 경우 예외를 발생시킵니다.

        Args:
            keyId (int): 확인할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Raises:
            HTTPException: API 키가 존재하지 않거나 사용자에게 소유권이 없는 경우 403 Forbidden 예외 발생.
        """
        # 1. API 키 ID를 사용하여 API 키 정보를 조회합니다.
        api_key = self.api_key_repo.getKeyByKeyId(keyId)
        # 2. API 키가 존재하지 않거나, 해당 키의 애플리케이션 소유자와 현재 사용자가 다를 경우 예외를 발생시킵니다.
        if not api_key or api_key.application.userId != currentUser.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 API 키에 접근할 권한이 없습니다."
            )

    def getSummary(self, currentUser: User, keyId: Optional[int], periodType: str, startDate: Optional[date], endDate: Optional[date]) -> StatisticsDataResponse:
        """
        기간별 통계 요약 데이터를 조회하여 그래프 등에 사용될 형태로 반환합니다.

        Args:
            currentUser (User): 현재 인증된 사용자.
            keyId (Optional[int]): 조회할 API 키 ID. None이면 사용자 전체 키 합산.
            periodType (str): 조회 기간 타입 (yearly, monthly, weekly, daily).
            startDate (Optional[date]): 조회 시작일.
            endDate (Optional[date]): 조회 종료일.

        Returns:
            StatisticsDataResponse: 기간별 통계 데이터가 담긴 응답 객체.
        """
        try:
            # 1. 조회할 API 키 ID 목록을 결정합니다.
            if keyId:
                # 특정 keyId가 주어지면, 해당 키의 소유권을 확인합니다.
                self._checkApiKeyOwner(keyId, currentUser)
                keyIds = [keyId]
            else:
                # keyId가 없으면, 현재 사용자가 소유한 모든 API 키를 조회합니다.
                userKeys = self.api_key_repo.getKeysByUserId(currentUser.id)
                keyIds = [key.id for key in userKeys] if userKeys else []

            # 2. 조회 기간(startDate, endDate)을 설정합니다.
            today = date.today()
            if not endDate:
                endDate = today
            if not startDate:
                if periodType == 'yearly':
                    startDate = today - relativedelta(years=1)
                    startDate = startDate.replace(day=1)
                elif periodType == 'monthly':
                    startDate = today - timedelta(days=30)
                elif periodType == 'weekly':
                    startDate = today - timedelta(days=7)
                elif periodType == 'daily':
                    startDate = today

            # 3. 기간 타입에 따라 적절한 리포지토리 메소드를 호출하여 데이터를 조회합니다.
            if periodType == 'daily':
                # 일간 통계는 실시간 성이 중요하므로, 집계된 `usage_stats`가 아닌 원본 `captcha_log`에서 직접 조회합니다.
                rawData = self.repo.getStatsFromLogs(
                    keyIds=keyIds,
                    startDate=startDate,
                    endDate=endDate
                )
            else:
                # 주간, 월간, 연간 통계는 미리 집계된 `usage_stats` 테이블을 사용하여 성능을 확보합니다.
                rawData = self.repo.getAggregatedStats(
                    keyIds=keyIds,
                    startDate=startDate,
                    endDate=endDate,
                    period=periodType
                )

            # 4. 조회된 데이터를 API 응답 스키마(DTO) 형태로 가공합니다.
            dataPoints = []
            for row in rawData:
                date_val = row.date
                if isinstance(date_val, (datetime, date)):
                    date_str = date_val.isoformat()
                else:
                    date_str = str(date_val)

                if periodType != 'daily':
                    date_str = date_str.split('T')[0]

                dataPoints.append(StatisticsData(
                    date=date_str,
                    totalRequests=row.totalRequests,
                    successCount=row.successCount,
                    failCount=row.failCount,
                    timeoutCount=row.timeoutCount
                ))

            # 5. 최종 응답 객체를 생성하여 반환합니다.
            return StatisticsDataResponse(
                keyId=keyId,
                periodType=periodType,
                data=dataPoints
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용량 요약 조회 중 오류가 발생했습니다: {e}"
            )

    def getUsageData(self, currentUser: User, keyId: int = None, periodType: str = 'daily', startDate: Optional[date] = None, endDate: Optional[date] = None, skip: int = 0, limit: int = 100) -> StatisticsLogResponse:
        """
        기간별 캡챠 사용 로그를 페이지네이션하여 상세 내역으로 반환합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.
            keyId (int, optional): API 키의 ID. None이면 사용자 전체 로그를 조회합니다.
            periodType (str): 조회 기간 타입 (yearly, monthly, weekly, daily).
            startDate (Optional[date]): 조회 시작일.
            endDate (Optional[date]): 조회 종료일.
            skip (int): 건너뛸 레코드 수 (페이지네이션 오프셋).
            limit (int): 가져올 최대 레코드 수.

        Returns:
            StatisticsLogResponse: 페이지네이션된 사용량 로그 객체.
        """
        try:
            # 1. 조회할 API 키 ID 목록을 결정합니다.
            if keyId:
                self._checkApiKeyOwner(keyId, currentUser)
                keyIds = [keyId]
            else:
                userKeys = self.api_key_repo.getKeysByUserId(currentUser.id)
                keyIds = [key.id for key in userKeys] if userKeys else []

            # 2. 조회 기간을 설정합니다.
            today = date.today()
            if not endDate:
                endDate = today
            if not startDate:
                if periodType == 'yearly':
                    startDate = today - relativedelta(years=1)
                elif periodType == 'monthly':
                    startDate = today - timedelta(days=30)
                elif periodType == 'weekly':
                    startDate = today - timedelta(days=7)
                elif periodType == 'daily':
                    startDate = today

            # 3. 리포지토리를 통해 페이지네이션된 로그 데이터를 조회합니다.
            logs, total_count = self.repo.getUsageDataLogs(
                keyIds=keyIds,
                startDate=startDate,
                endDate=endDate,
                skip=skip,
                limit=limit
            )

            # 4. 조회된 로그 데이터를 응답 스키마 형태로 변환합니다.
            items = []
            for log in logs:
                log_date = log[3].strftime('%Y-%m-%d %H:%M:%S')

                items.append(
                    StatisticsLog(
                        id=log[0],
                        appName=log[1],
                        key=log[2],
                        date=log_date,
                        result=log[4],
                        ratency=log[5]
                    )
                )

            # 5. 최종 페이지네이션 응답 객체를 생성하여 반환합니다.
            return StatisticsLogResponse(
                keyId=keyId,
                periodType=periodType,
                data=items,
                total=total_count,
                page=skip // limit + 1,
                size=len(items)
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용량 데이터 조회 중 오류가 발생했습니다: {e}"
            )

    def getRequestCountSummary(self, currentUser: User, keyId: Optional[int], periodType: str) -> RequestCountSummaryResponse:
        """
        캡챠 요청 수를 현재 기간과 이전 기간으로 나누어 비교 요약 데이터를 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자.
            keyId (Optional[int]): 조회할 API 키 ID. None이면 사용자 전체 키 합산.
            periodType (str): 조회 기간 타입 (daily, weekly, monthly).

        Returns:
            RequestCountSummaryResponse: 비교 요약 데이터가 담긴 응답 객체.
        """
        try:
            # 1. 조회할 API 키 ID 목록을 결정합니다.
            if keyId:
                self._checkApiKeyOwner(keyId, currentUser)
                keyIds = [keyId]
            else:
                userKeys = self.api_key_repo.getKeysByUserId(currentUser.id)
                keyIds = [key.id for key in userKeys] if userKeys else []

            # 2. `periodType`에 따라 현재와 이전 기간의 날짜 범위를 계산합니다.
            today = date.today()
            if periodType == 'daily':
                currentStart = today
                currentEnd = today
                previousStart = today - timedelta(days=1)
                previousEnd = today - timedelta(days=1)
            elif periodType == 'weekly':
                currentStart = today - timedelta(days=today.weekday())
                currentEnd = currentStart + timedelta(days=6)
                previousStart = currentStart - timedelta(weeks=1)
                previousEnd = currentStart - timedelta(days=1)
            elif periodType == 'monthly':
                currentStart = today.replace(day=1)
                nextMonth = currentStart.replace(day=28) + timedelta(days=4)
                currentEnd = nextMonth - timedelta(days=nextMonth.day)
                previousEnd = currentStart - timedelta(days=1)
                previousStart = previousEnd.replace(day=1)
            else:
                raise HTTPException(
                    status_code=400, detail="Invalid periodType")

            # 3. 리포지토리를 통해 각 기간의 요청 수를 조회합니다.
            currentCount = self.repo.getTotalRequestsForPeriod(
                keyIds, currentStart, currentEnd)
            previousCount = self.repo.getTotalRequestsForPeriod(
                keyIds, previousStart, previousEnd)

            # 4. 이전 기간 대비 증감률(%)을 계산합니다.
            if previousCount > 0:
                rate = ((currentCount - previousCount) / previousCount) * 100
            elif currentCount > 0:
                # 이전 기간 요청이 0일 때, 현재 요청이 있으면 100% 증가로 처리합니다.
                rate = 100.0
            else:
                # 이전 기간과 현재 기간 모두 요청이 0이면 변화 없음(0%)으로 처리합니다.
                rate = 0.0

            # 5. 응답 스키마에 맞게 데이터를 조립합니다.
            summaryData = RequestCountSummary(
                currentCount=currentCount,
                previousCount=previousCount,
                rate=round(rate, 2)
            )

            # 6. 최종 응답 객체를 생성하여 반환합니다.
            return RequestCountSummaryResponse(
                keyId=keyId,
                periodType=periodType,
                data=summaryData
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"요청 수 요약 조회 중 오류가 발생했습니다: {e}"
            )

    def getTotalRequestCount(self, currentUser: User, keyId: Optional[int]) -> RequestTotalResponse:
        """
        사용자 또는 특정 API 키의 전체 캡챠 요청 수를 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자.
            keyId (Optional[int]): 조회할 API 키 ID. None이면 사용자 전체 키 합산.

        Returns:
            RequestTotalResponse: 전체 요청 수가 담긴 응답 객체.
        """
        try:
            # 1. 조회할 API 키 ID 목록을 결정합니다.
            if keyId:
                self._checkApiKeyOwner(keyId, currentUser)
                keyIds = [keyId]
            else:
                userKeys = self.api_key_repo.getKeysByUserId(currentUser.id)
                keyIds = [key.id for key in userKeys] if userKeys else []

            # 2. 리포지토리를 통해 전체 요청 수를 조회합니다.
            count = self.repo.getTotalRequests(keyIds)

            # 3. 최종 응답 객체를 생성하여 반환합니다.
            return RequestTotalResponse(
                keyId=keyId,
                count=count
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"전체 요청 수 조회 중 오류가 발생했습니다: {e}"
            )
