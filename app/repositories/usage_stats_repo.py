# app/repositories/usage_stats_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from fastapi import HTTPException, status

from app.models.usage_stats import UsageStats
from app.models.api_key import ApiKey
from app.models.application import Application
from app.models.captcha_log import CaptchaLog


class UsageStatsRepository:
    """
    사용량 통계 관련 데이터베이스 작업을 처리하는 리포지토리입니다.
    """

    def __init__(self, db: Session):
        """
        UsageStatsRepository의 생성자입니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션.
        """
        self.db = db

    def getDailyUsageByUserId(self, userId: int, startDate: date, endDate: date) -> list:
        """
        주어진 사용자와 날짜 범위에 대해 일별 사용량 통계를 조회합니다.

        Args:
            userId (int): 사용자의 ID.
            startDate (date): 통계를 조회할 시작 날짜.
            endDate (date): 통계를 조회할 종료 날짜.

        Returns:
            list: 조회된 일별 사용량 통계 객체의 리스트.
        """
        try:
            # 1. `UsageStats` 테이블을 기준으로 `ApiKey`, `Application` 테이블과 조인합니다.
            query = self.db.query(
                UsageStats.date,
                func.sum(UsageStats.captchaTotalRequests).label('captchaTotalRequests'),
                func.sum(UsageStats.captchaSuccessCount).label('captchaSuccessCount'),
                func.sum(UsageStats.captchaFailCount).label('captchaFailCount'),
            ).join(
                ApiKey, UsageStats.keyId == ApiKey.id
            ).join(
                Application, ApiKey.appId == Application.id
            ).filter(
                # 2. 특정 사용자의 ID와 주어진 날짜 범위로 필터링합니다.
                Application.userId == userId,
                UsageStats.date >= startDate,
                UsageStats.date <= endDate
            ).group_by(
                # 3. 날짜별로 그룹화하여 통계를 집계합니다.
                UsageStats.date
            ).order_by(
                # 4. 날짜순으로 정렬합니다.
                UsageStats.date
            )
            # 5. 쿼리를 실행하고 모든 결과를 반환합니다.
            return query.all()
        except Exception as e:
            # 6. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"일별 사용량 통계 조회 중 오류가 발생했습니다: {e}"
            )

    def getSummaryForPeriod(self, userId: int, startDate: date, endDate: date) -> tuple[int, int, int]:
        """
        특정 사용자와 날짜 범위에 대한 총 요청 수, 성공 수, 실패 수를 요약하여 반환합니다.

        Args:
            userId (int): 사용자의 ID.
            startDate (date): 조회 시작 날짜.
            endDate (date): 조회 종료 날짜.

        Returns:
            tuple[int, int, int]: (총 요청 수, 성공 수, 실패 수) 튜플.
        """
        try:
            # 1. 특정 사용자의 주어진 기간 동안의 총 요청, 성공, 실패 수를 합산하는 쿼리를 작성합니다.
            result = self.db.query(
                func.sum(UsageStats.captchaTotalRequests),
                func.sum(UsageStats.captchaSuccessCount),
                func.sum(UsageStats.captchaFailCount)
            ).join(
                ApiKey, UsageStats.keyId == ApiKey.id
            ).join(
                Application, ApiKey.appId == Application.id
            ).filter(
                Application.userId == userId,
                UsageStats.date >= startDate,
                UsageStats.date <= endDate
            ).first()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"기간별 사용량 요약 조회 중 오류가 발생했습니다: {e}"
            )

        # 3. 쿼리 결과가 비어있거나 값이 None일 경우 0으로 처리합니다.
        total = result[0] if result and result[0] is not None else 0
        success = result[1] if result and result[1] is not None else 0
        fail = result[2] if result and result[2] is not None else 0

        # 4. 집계된 값을 튜플로 반환합니다.
        return total, success, fail

    def getTotalRequests(self, userId: int) -> int:
        """
        특정 사용자의 전체 기간에 대한 총 캡챠 요청 수를 반환합니다.

        Args:
            userId (int): 사용자의 ID.

        Returns:
            int: 전체 기간 동안의 총 캡챠 요청 수.
        """
        try:
            # 1. 특정 사용자의 전체 캡챠 요청 수를 합산하는 쿼리를 작성합니다.
            result = self.db.query(
                func.sum(UsageStats.captchaTotalRequests)
            ).join(
                ApiKey, UsageStats.keyId == ApiKey.id
            ).join(
                Application, ApiKey.appId == Application.id
            ).filter(
                Application.userId == userId
            ).scalar()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"총 요청 수 조회 중 오류가 발생했습니다: {e}"
            )
        
        # 3. 결과가 None이면 0을, 아니면 해당 값을 반환합니다.
        return result if result is not None else 0

    def getResultsCounts(self, userId: int) -> tuple[int, int]:
        """
        특정 사용자의 전체 기간에 대한 성공 및 실패한 캡챠 요청 수를 반환합니다.

        Args:
            userId (int): 사용자의 ID.

        Returns:
            tuple[int, int]: (성공 수, 실패 수) 튜플.
        """
        try:
            # 1. 특정 사용자의 전체 성공 및 실패 캡챠 요청 수를 합산하는 쿼리를 작성합니다.
            result = self.db.query(
                func.sum(UsageStats.captchaSuccessCount),
                func.sum(UsageStats.captchaFailCount)
            ).join(
                ApiKey, UsageStats.keyId == ApiKey.id
            ).join(
                Application, ApiKey.appId == Application.id
            ).filter(
                Application.userId == userId
            ).first()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"성공/실패 수 조회 중 오류가 발생했습니다: {e}"
            )

        # 3. 쿼리 결과가 비어있거나 값이 None일 경우 0으로 처리합니다.
        success_count = result[0] if result and result[0] is not None else 0
        fail_count = result[1] if result and result[1] is not None else 0

        # 4. 집계된 값을 튜플로 반환합니다.
        return success_count, fail_count

    # --- API 키 기준 통계 --- #

    def getSummaryForPeriodByApiKey(self, keyId: int, startDate: date, endDate: date) -> tuple[int, int, int]:
        """
        특정 API 키와 날짜 범위에 대한 총 요청 수, 성공 수, 실패 수를 요약하여 반환합니다.

        Args:
            keyId (int): API 키의 ID.
            startDate (date): 조회 시작 날짜.
            endDate (date): 조회 종료 날짜.

        Returns:
            tuple[int, int, int]: (총 요청 수, 성공 수, 실패 수) 튜플.
        """
        try:
            # 1. 특정 API 키의 주어진 기간 동안의 총 요청, 성공, 실패 수를 합산하는 쿼리를 작성합니다.
            result = self.db.query(
                func.sum(UsageStats.captchaTotalRequests),
                func.sum(UsageStats.captchaSuccessCount),
                func.sum(UsageStats.captchaFailCount)
            ).filter(
                UsageStats.keyId == keyId,
                UsageStats.date >= startDate,
                UsageStats.date <= endDate
            ).first()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키별 기간 사용량 요약 조회 중 오류가 발생했습니다: {e}"
            )

        # 3. 쿼리 결과가 비어있거나 값이 None일 경우 0으로 처리합니다.
        total = result[0] if result and result[0] is not None else 0
        success = result[1] if result and result[1] is not None else 0
        fail = result[2] if result and result[2] is not None else 0

        # 4. 집계된 값을 튜플로 반환합니다.
        return total, success, fail

    def getTotalRequestsByApiKey(self, keyId: int) -> int:
        """
        특정 API 키의 전체 기간에 대한 총 캡챠 요청 수를 반환합니다.

        Args:
            keyId (int): API 키의 ID.

        Returns:
            int: 전체 기간 동안의 총 캡챠 요청 수.
        """
        try:
            # 1. 특정 API 키의 전체 캡챠 요청 수를 합산하는 쿼리를 작성합니다.
            result = self.db.query(
                func.sum(UsageStats.captchaTotalRequests)
            ).filter(
                UsageStats.keyId == keyId
            ).scalar()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키별 총 요청 수 조회 중 오류가 발생했습니다: {e}"
            )

        # 3. 결과가 None이면 0을, 아니면 해당 값을 반환합니다.
        return result if result is not None else 0

    def getResultsCountsByApiKey(self, keyId: int) -> tuple[int, int]:
        """
        특정 API 키의 전체 기간에 대한 성공 및 실패한 캡챠 요청 수를 반환합니다.

        Args:
            keyId (int): API 키의 ID.

        Returns:
            tuple[int, int]: (성공 수, 실패 수) 튜플.
        """
        try:
            # 1. 특정 API 키의 전체 성공 및 실패 캡챠 요청 수를 합산하는 쿼리를 작성합니다.
            result = self.db.query(
                func.sum(UsageStats.captchaSuccessCount),
                func.sum(UsageStats.captchaFailCount)
            ).filter(
                UsageStats.keyId == keyId
            ).first()
        except Exception as e:
            # 2. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"API 키별 성공/실패 수 조회 중 오류가 발생했습니다: {e}"
            )

        # 3. 쿼리 결과가 비어있거나 값이 None일 경우 0으로 처리합니다.
        success_count = result[0] if result and result[0] is not None else 0
        fail_count = result[1] if result and result[1] is not None else 0

        # 4. 집계된 값을 튜플로 반환합니다.
        return success_count, fail_count

    def getUsageDataLogs(self, userId: int = None, keyId: int = None, skip: int = 0, limit: int = 100) -> tuple[list, int]:
        """
        사용자 또는 API 키별 캡챠 사용량 로그를 페이지네이션하여 조회합니다.

        Args:
            userId (int, optional): 필터링할 사용자의 ID. Defaults to None.
            keyId (int, optional): 필터링할 API 키의 ID. Defaults to None.
            skip (int): 건너뛸 레코드 수 (페이지네이션용). Defaults to 0.
            limit (int): 가져올 최대 레코드 수 (페이지네이션용). Defaults to 100.

        Returns:
            tuple[list, int]: 조회된 사용량 로그 객체 리스트와 전체 개수.
        """
        try:
            # 1. `CaptchaLog`를 기준으로 필요한 정보를 포함하는 기본 쿼리를 작성합니다.
            base_query = self.db.query(
                CaptchaLog.id,
                Application.appName,
                ApiKey.key,
                CaptchaLog.created_at,
                CaptchaLog.result,
                CaptchaLog.latency_ms
            ).join(
                ApiKey, CaptchaLog.keyId == ApiKey.id
            ).join(
                Application, ApiKey.appId == Application.id
            )

            # 2. 사용자 ID가 제공되면, 해당 사용자로 쿼리를 필터링합니다.
            if userId:
                base_query = base_query.filter(Application.userId == userId)
            # 3. API 키 ID가 제공되면, 해당 키로 쿼리를 필터링합니다.
            if keyId:
                base_query = base_query.filter(ApiKey.id == keyId)

            # 4. 필터링된 전체 로그의 개수를 계산합니다.
            total_count = base_query.count()
            # 5. 페이지네이션(skip, limit)을 적용하여 실제 로그 데이터를 조회합니다.
            logs = base_query.offset(skip).limit(limit).all()

            # 6. 로그 리스트와 전체 개수를 튜플로 반환합니다.
            return logs, total_count
        except Exception as e:
            # 7. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용량 로그 데이터 조회 중 오류가 발생했습니다: {e}"
            )