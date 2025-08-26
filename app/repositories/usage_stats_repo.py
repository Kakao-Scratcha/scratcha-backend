from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date, timedelta
from typing import Optional
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

    def incrementTotalRequests(self, keyId: int):
        """
        특정 API 키에 대한 오늘 날짜의 캡챠 총 요청 수를 1 증가시킵니다.

        오늘 날짜의 통계 데이터가 없으면 새로 생성하고, 있으면 카운트를 업데이트합니다.

        Args:
            keyId (int): API 키의 ID.
        """
        try:
            # 1. 오늘 날짜를 기준으로 해당 API 키의 통계 데이터를 조회합니다.
            today = date.today()
            usageStats = self.db.query(UsageStats).filter(
                UsageStats.keyId == keyId,
                UsageStats.date == today
            ).first()

            # 2. 통계 데이터가 존재하면 captchaTotalRequests를 1 증가시킵니다.
            if usageStats:
                usageStats.captchaTotalRequests += 1
            # 3. 통계 데이터가 없으면 새로 생성하고 captchaTotalRequests를 1로 설정합니다.
            else:
                usageStats = UsageStats(
                    keyId=keyId,
                    date=today,
                    captchaTotalRequests=1,
                    captchaSuccessCount=0,
                    captchaFailCount=0
                )
                self.db.add(usageStats)

            # 4. 변경사항을 데이터베이스 세션에 반영합니다. (커밋은 서비스 레이어에서 수행)
            self.db.flush([usageStats])

        except Exception as e:
            # 5. 데이터베이스 작업 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"캡챠 요청 수 업데이트 중 오류가 발생했습니다: {e}"
            )

    def incrementVerificationResult(self, keyId: int, result: str, latencyMs: int):
        """
        특정 API 키에 대한 오늘 날짜의 캡챠 검증 결과를(성공/실패/타임아웃) 1 증가시키고,
        평균 응답 시간 계산을 위한 총 지연 시간과 검증 횟수를 업데이트합니다.

        Args:
            keyId (int): API 키의 ID.
            result (str): 캡챠 검증 결과. ("success", "fail", "timeout")
            latencyMs (int): 해당 검증의 지연 시간 (밀리초).
        """
        try:
            today = date.today()
            usageStats = self.db.query(UsageStats).filter(
                UsageStats.keyId == keyId,
                UsageStats.date == today
            ).first()

            if not usageStats:
                usageStats = UsageStats(
                    keyId=keyId,
                    date=today,
                    captchaTotalRequests=0,
                    captchaSuccessCount=0,
                    captchaFailCount=0,
                    captchaTimeoutCount=0,
                    totalLatencyMs=0,
                    verificationCount=0
                )
                self.db.add(usageStats)

            if result == "success":
                usageStats.captchaSuccessCount += 1
            elif result == "fail":
                usageStats.captchaFailCount += 1
            elif result == "timeout":
                usageStats.captchaTimeoutCount += 1

            usageStats.totalLatencyMs += latencyMs
            usageStats.verificationCount += 1
            usageStats.avgResponseTimeMs = usageStats.totalLatencyMs / usageStats.verificationCount
            
            self.db.flush([usageStats])

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"캡챠 검증 결과 업데이트 중 오류가 발생했습니다: {e}"
            )

    def getUsageDataLogs(self, userId: int = None, keyId: int = None, startDate: Optional[date] = None, endDate: Optional[date] = None, skip: int = 0, limit: int = 100) -> tuple[list, int]:
        """
        사용자 또는 API 키별 캡챠 사용량 로그를 페이지네이션하여 조회합니다.

        Args:
            userId (int, optional): 필터링할 사용자의 ID. Defaults to None.
            keyId (int, optional): 필터링할 API 키의 ID. Defaults to None.
            startDate (Optional[date]): 조회 시작일. Defaults to None.
            endDate (Optional[date]): 조회 종료일. Defaults to None.
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

            # 4. 날짜 필터링을 적용합니다.
            if startDate:
                base_query = base_query.filter(CaptchaLog.created_at >= startDate)
            if endDate:
                # To include the entire end day, filter by less than the start of the next day
                base_query = base_query.filter(CaptchaLog.created_at < endDate + timedelta(days=1))

            # 5. 필터링된 전체 로그의 개수를 계산합니다.
            total_count = base_query.count()
            # 6. 페이지네이션(skip, limit)을 적용하여 실제 로그 데이터를 조회합니다.
            logs = base_query.offset(skip).limit(limit).all()

            # 7. 로그 리스트와 전체 개수를 튜플로 반환합니다.
            return logs, total_count
        except Exception as e:
            # 8. 데이터베이스 조회 중 오류 발생 시 서버 오류를 반환합니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"사용량 로그 데이터 조회 중 오류가 발생했습니다: {e}"
            )

    def getStatsFromLogs(self, startDate: date, endDate: date, userId: int = None, keyId: int = None):
        """
        captcha_log 테이블에서 직접 시간별 통계를 집계합니다. (daily period 용)
        """
        try:
            # 시간별로 그룹화하기 위한 DATE_FORMAT 함수 사용 (MySQL 호환)
            timePeriod = func.DATE_FORMAT(
                CaptchaLog.created_at, '%Y-%m-%dT%H:00:00').label('date')

            query = self.db.query(
                timePeriod,
                func.coalesce(func.count(CaptchaLog.id),
                              0).label('totalRequests'),
                func.coalesce(func.sum(
                    case((CaptchaLog.result == 'success', 1), else_=0)), 0).label('successCount'),
                func.coalesce(func.sum(
                    case((CaptchaLog.result == 'fail', 1), else_=0)), 0).label('failCount'),
                func.coalesce(func.sum(
                    case((CaptchaLog.result == 'timeout', 1), else_=0)), 0).label('timeoutCount')
            ).filter(CaptchaLog.created_at.between(f'{startDate} 00:00:00', f'{endDate} 23:59:59'))

            if keyId:
                query = query.filter(CaptchaLog.keyId == keyId)
            elif userId:
                query = query.join(ApiKey, CaptchaLog.keyId == ApiKey.id).join(
                    Application, ApiKey.appId == Application.id).filter(Application.userId == userId)

            return query.group_by(timePeriod).order_by(timePeriod).all()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"로그 기반 일일 통계 조회 중 오류: {e}"
            )

    def getAggregatedStats(self, startDate: date, endDate: date, period: str, userId: int = None, keyId: int = None):
        """
        usage_stats 테이블에서 기간별 통계를 집계합니다. (weekly, monthly, yearly 용)
        """
        try:
            # 기간별로 그룹화하기 위한 함수 설정 (MySQL 호환)
            if period == 'yearly':
                groupPeriod = func.DATE_FORMAT(
                    UsageStats.date, '%Y-%m-01').label('date')
            elif period == 'monthly' or period == 'weekly':
                groupPeriod = func.DATE(UsageStats.date).label('date')
            else:
                raise ValueError("Invalid period type")

            query = self.db.query(
                groupPeriod,
                func.coalesce(func.sum(UsageStats.captchaTotalRequests), 0).label(
                    'totalRequests'),
                func.coalesce(func.sum(UsageStats.captchaSuccessCount), 0).label(
                    'successCount'),
                func.coalesce(func.sum(UsageStats.captchaFailCount), 0).label(
                    'failCount'),
                func.coalesce(func.sum(UsageStats.captchaTimeoutCount), 0).label(
                    'timeoutCount')
            ).filter(UsageStats.date.between(startDate, endDate))

            if keyId:
                query = query.filter(UsageStats.keyId == keyId)
            elif userId:
                query = query.join(ApiKey, UsageStats.keyId == ApiKey.id).join(
                    Application, ApiKey.appId == Application.id).filter(Application.userId == userId)

            return query.group_by(groupPeriod).order_by(groupPeriod).all()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"집계 기반 통계 조회 중 오류: {e}"
            )