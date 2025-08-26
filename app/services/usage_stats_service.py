from datetime import date, timedelta
from fastapi import HTTPException, status
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.usage_stats import StatisticsDataResponse, StatisticsData, StatisticsLog, StatisticsLogResponse
from app.models.user import User
from typing import Optional, List
from datetime import datetime
from dateutil.relativedelta import relativedelta


class UsageStatsService:
    """
    사용량 통계 관련 비즈니스 로직을 처리하는 서비스 클래스입니다.
    """

    def __init__(self, repo: UsageStatsRepository, api_key_repo: ApiKeyRepository):
        """
        UsageStatsService의 생성자입니다.

        Args:
            repo (UsageStatsRepository): 사용량 통계 리포지토리 객체.
            api_key_repo (ApiKeyRepository): API 키 리포지토리 객체.
        """
        self.repo = repo
        self.api_key_repo = api_key_repo

    def _checkApiKeyOwner(self, keyId: int, currentUser: User):
        """
        API 키의 소유권을 확인합니다.

        요청한 사용자가 해당 API 키의 실제 소유자인지 확인하여, 권한이 없는 경우
        HTTP 403 Forbidden 예외를 발생시킵니다.

        Args:
            keyId (int): 확인할 API 키의 ID.
            currentUser (User): 현재 인증된 사용자 객체.

        Raises:
            HTTPException: API 키가 존재하지 않거나 사용자에게 소유권이 없는 경우.
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
        기간별 통계 요약 데이터를 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자.
            keyId (Optional[int]): 조회할 API 키 ID. None이면 사용자 전체 키 합산.
            periodType (str): 조회 기간 타입 (yearly, monthly, weekly, daily).
            startDate (Optional[date]): 조회 시작일.
            endDate (Optional[date]): 조회 종료일.

        Returns:
            StatisticsDataResponse: 기간별 통계 데이터.
        """
        # 1. API 키 소유권 확인 (keyId가 지정된 경우)
        if keyId:
            self._checkApiKeyOwner(keyId, currentUser)

        # 2. 날짜 범위 설정
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

        # 3. 데이터 조회
        if periodType == 'daily':
            # 'daily'는 captcha_log에서 직접 시간별로 집계
            rawData = self.repo.getStatsFromLogs(
                userId=currentUser.id if not keyId else None,
                keyId=keyId,
                startDate=startDate,
                endDate=endDate
            )
        else:
            # 나머지는 usage_stats에서 집계
            rawData = self.repo.getAggregatedStats(
                userId=currentUser.id if not keyId else None,
                keyId=keyId,
                startDate=startDate,
                endDate=endDate,
                period=periodType
            )

        # 4. 데이터 포맷팅
        dataPoints = []
        for row in rawData:
            date_val = row.date
            # date나 datetime 객체이면 isoformat()을 사용, 아니면 그대로 문자열로 취급
            if isinstance(date_val, (datetime, date)):
                date_str = date_val.isoformat()
            else:
                date_str = str(date_val)

            # daily가 아닐 경우, 시간 정보 제거
            if periodType != 'daily':
                date_str = date_str.split('T')[0]

            dataPoints.append(StatisticsData(
                date=date_str,
                totalRequests=row.totalRequests,
                successCount=row.successCount,
                failCount=row.failCount,
                timeoutCount=row.timeoutCount
            ))

        return StatisticsDataResponse(
            keyId=keyId,
            periodType=periodType,
            data=dataPoints
        )

    def getUsageData(self, currentUser: User, keyId: int = None, periodType: str = 'daily', startDate: Optional[date] = None, endDate: Optional[date] = None, skip: int = 0, limit: int = 100) -> StatisticsLogResponse:
        """
        기간별 집계된 사용량 로그 데이터를 페이지네이션하여 조회합니다.

        Args:
            currentUser (User): 현재 인증된 사용자 객체.
            keyId (int, optional): API 키의 ID. None이면 사용자 전체 로그를 조회합니다. Defaults to None.
            periodType (str): 조회 기간 타입 (yearly, monthly, weekly, daily). Defaults to 'daily'.
            startDate (Optional[date]): 조회 시작일. Defaults to None.
            endDate (Optional[date]): 조회 종료일. Defaults to None.
            skip (int): 건너뛸 레코드 수. Defaults to 0.
            limit (int): 가져올 최대 레코드 수. Defaults to 100.

        Returns:
            StatisticsLogResponse: 페이지네이션된 사용량 로그 객체.
        """
        # 1. API 키 소유권 확인 (keyId가 지정된 경우)
        if keyId:
            self._checkApiKeyOwner(keyId, currentUser)

        # 2. 날짜 범위 설정 (getSummary와 동일한 로직 사용)
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

        # 3. 데이터 조회 (getUsageDataLogs를 사용하여 개별 로그 조회)
        logs, total_count = self.repo.getUsageDataLogs(
            userId=currentUser.id if not keyId else None,
            keyId=keyId,
            startDate=startDate,
            endDate=endDate,
            skip=skip,
            limit=limit
        )

        # 4. 조회된 로그 데이터를 StatisticsLog 스키마에 맞게 변환합니다.
        items = []
        for log in logs:
            log_date = log[3]
            if periodType != 'daily':
                # Format to YYYY-MM-DD if not daily
                log_date = log_date.strftime('%Y-%m-%d')
            else:
                # Format to YYYY-MM-DD HH:MM:SS for daily
                log_date = log_date.strftime('%Y-%m-%d %H:%M:%S')

            items.append(
                StatisticsLog(
                    id=log[0],
                    appName=log[1],
                    key=log[2],
                    date=log_date, # Use the formatted string
                    result=log[4],
                    ratency=log[5]
                )
            )

        # 5. 페이지네이션된 데이터를 반환합니다.
        paginated_data = items

        return StatisticsLogResponse(
            keyId=keyId,
            periodType=periodType,
            data=paginated_data, # paginated_data is now items
            total=total_count,
            page=skip // limit + 1,
            size=len(paginated_data) # len(items)
        )
