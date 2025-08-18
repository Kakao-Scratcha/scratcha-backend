from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.models.usage_stats import UsageStats
from app.models.api_key import ApiKey
from app.models.application import Application


class UsageStatsRepository:
    """
    사용량 통계 관련 데이터베이스 작업을 처리하는 리포지토리입니다.
    """

    def __init__(self, db: Session):
        self.db = db

    def getDailyUsageByUserId(self, userId: int, startDate: date, endDate: date):
        """
        주어진 사용자와 날짜 범위에 대해 일별 사용량 통계를 조회합니다.

        Args:
            userId (int): 사용자의 ID.
            startDate (date): 통계를 조회할 시작 날짜.
            endDate (date): 통계를 조회할 종료 날짜.

        Returns:
            list: 조회된 사용량 통계 객체의 리스트.
        """
        # `UsageStats` 테이블과 `ApiKey`, `Application` 테이블을 JOIN하여
        # 특정 사용자의 모든 API 키에 대한 사용량 데이터를 집계합니다.
        query = self.db.query(
            UsageStats.date,
            func.sum(UsageStats.captchaTotalRequests).label(
                'captchaTotalRequests'),
            func.sum(UsageStats.captchaSuccessCount).label(
                'captchaSuccessCount'),
            func.sum(UsageStats.captchaFailCount).label(
                'captchaFailCount'),
        ).join(
            ApiKey, UsageStats.apiKeyId == ApiKey.id
        ).join(
            Application, ApiKey.appId == Application.id
        ).filter(
            Application.userId == userId,
            UsageStats.date >= startDate,
            UsageStats.date <= endDate
        ).group_by(
            UsageStats.date
        ).order_by(
            UsageStats.date
        )

        return query.all()

    def getSummaryForPeriod(self, userId: int, startDate: date, endDate: date) -> tuple[int, int, int]:
        """
        특정 사용자와 날짜 범위에 대한 총 요청 수, 성공 수, 실패 수를 반환합니다.

        Args:
            userId (int): 사용자의 ID.
            startDate (date): 조회 시작 날짜.
            endDate (date): 조회 종료 날짜.

        Returns:
            tuple[int, int, int]: 총 요청 수, 성공 수, 실패 수의 튜플.
        """
        result = self.db.query(
            func.sum(UsageStats.captchaTotalRequests),
            func.sum(UsageStats.captchaSuccessCount),
            func.sum(UsageStats.captchaFailCount)
        ).join(
            ApiKey, UsageStats.apiKeyId == ApiKey.id
        ).join(
            Application, ApiKey.appId == Application.id
        ).filter(
            Application.userId == userId,
            UsageStats.date >= startDate,
            UsageStats.date <= endDate
        ).first()

        total = result[0] if result and result[0] is not None else 0
        success = result[1] if result and result[1] is not None else 0
        fail = result[2] if result and result[2] is not None else 0

        return total, success, fail

    def getTotalRequests(self, userId: int) -> int:
        """
        특정 사용자의 전체 기간에 대한 총 캡챠 요청 수를 반환합니다.

        Args:
            userId (int): 사용자의 ID.

        Returns:
            int: 전체 기간 동안의 총 캡챠 요청 수.
        """
        result = self.db.query(
            func.sum(UsageStats.captchaTotalRequests)
        ).join(
            ApiKey, UsageStats.apiKeyId == ApiKey.id
        ).join(
            Application, ApiKey.appId == Application.id
        ).filter(
            Application.userId == userId
        ).scalar()

        return result if result is not None else 0

    def getResultsCounts(self, userId: int) -> tuple[int, int]:
        """
        특정 사용자의 전체 기간에 대한 성공 및 실패한 캡챠 요청 수를 반환합니다.

        Args:
            userId (int): 사용자의 ID.

        Returns:
            tuple[int, int]: 성공 및 실패한 캡챠 요청 수의 튜플.
        """
        result = self.db.query(
            func.sum(UsageStats.captchaSuccessCount),
            func.sum(UsageStats.captchaFailCount)
        ).join(
            ApiKey, UsageStats.apiKeyId == ApiKey.id
        ).join(
            Application, ApiKey.appId == Application.id
        ).filter(
            Application.userId == userId
        ).first()

        success_count = result[0] if result and result[0] is not None else 0
        fail_count = result[1] if result and result[1] is not None else 0

        return success_count, fail_count

    def getSummaryForPeriodByApiKey(self, apiKeyId: int, startDate: date, endDate: date) -> tuple[int, int, int]:
        """
        특정 API 키와 날짜 범위에 대한 총 요청 수, 성공 수, 실패 수를 반환합니다.

        Args:
            apiKeyId (int): API 키의 ID.
            startDate (date): 조회 시작 날짜.
            endDate (date): 조회 종료 날짜.

        Returns:
            tuple[int, int, int]: 총 요청 수, 성공 수, 실패 수의 튜플.
        """
        result = self.db.query(
            func.sum(UsageStats.captchaTotalRequests),
            func.sum(UsageStats.captchaSuccessCount),
            func.sum(UsageStats.captchaFailCount)
        ).filter(
            UsageStats.apiKeyId == apiKeyId,
            UsageStats.date >= startDate,
            UsageStats.date <= endDate
        ).first()

        total = result[0] if result and result[0] is not None else 0
        success = result[1] if result and result[1] is not None else 0
        fail = result[2] if result and result[2] is not None else 0

        return total, success, fail

    def getTotalRequestsByApiKey(self, keyId: int) -> int:
        """
        특정 API 키의 전체 기간에 대한 총 캡챠 요청 수를 반환합니다.

        Args:
            keyId (int): API 키의 ID.

        Returns:
            int: 전체 기간 동안의 총 캡챠 요청 수.
        """
        result = self.db.query(
            func.sum(UsageStats.captchaTotalRequests)
        ).filter(
            UsageStats.apiKeyId == keyId
        ).scalar()

        return result if result is not None else 0

    def getResultsCountsByApiKey(self, keyId: int) -> tuple[int, int]:
        """
        특정 API 키의 전체 기간에 대한 성공 및 실패한 캡챠 요청 수를 반환합니다.

        Args:
            keyId (int): API 키의 ID.

        Returns:
            tuple[int, int]: 성공 및 실패한 캡챠 요청 수의 튜플.
        """
        result = self.db.query(
            func.sum(UsageStats.captchaSuccessCount),
            func.sum(UsageStats.captchaFailCount)
        ).filter(
            UsageStats.apiKeyId == keyId
        ).first()

        success_count = result[0] if result and result[0] is not None else 0
        fail_count = result[1] if result and result[1] is not None else 0

        return success_count, fail_count
