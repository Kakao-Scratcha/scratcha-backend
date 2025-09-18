# app/services/rule_check_service.py

import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.captcha_repo import CaptchaRepository
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.schemas.captcha import CaptchaVerificationResponse
from app.models.captcha_log import CaptchaResult
from app.models.captcha_session import CaptchaSession

logger = logging.getLogger(__name__)


class RuleCheckService:
    def __init__(self, db: Session, captcha_repo: CaptchaRepository, usage_stats_repo: UsageStatsRepository):
        self.db = db
        self.captchaRepo = captcha_repo
        self.usageStatsRepo = usage_stats_repo

    def check_time_constraint(self, session: CaptchaSession, latency: timedelta) -> Optional[CaptchaVerificationResponse]:
        if latency < timedelta(seconds=0.5):
            logger.info(
                f"[디버그] 너무 빠른 캡챠 시도 감지. clientToken: {session.clientToken}, latency: {latency}")
            self.captchaRepo.createCaptchaLog(
                session=session,
                result=CaptchaResult.FAIL,
                latency_ms=int(latency.total_seconds() * 1000),
                is_correct=False,
                ml_confidence=None,
                ml_is_bot=None
            )
            self.usageStatsRepo.incrementVerificationResult(
                session.keyId, CaptchaResult.FAIL.value, int(latency.total_seconds() * 1000))
            self.db.commit()
            return CaptchaVerificationResponse(result="fail", message="너무 빠르게 캡챠를 시도했습니다.")
        return None

    def check_no_scratching(self, session: CaptchaSession, latency: timedelta, behavior_result: Dict[str, Any], confidence: Optional[float]) -> Optional[CaptchaVerificationResponse]:
        n_events = behavior_result.get("stats", {}).get("n_events", 0)
        total_distance = behavior_result.get(
            "stats", {}).get("total_distance", 0)
        oob_rate_canvas = behavior_result.get(
            "stats", {}).get("oob_rate_canvas", 0.0)

        # Pattern 3: 긁지 않고 바로 정답 선택 (oob 비율 100%)
        # Pattern 1: scratch 위를 move하고 바로 정답클릭 (oob비율 100%안나옴)
        if oob_rate_canvas == 1:
            logger.info(
                f"[디버그] 스크래치 없이 정답 클릭 감지. clientToken: {session.clientToken}, n_events: {n_events}, total_distance: {total_distance}, oob_rate_canvas: {oob_rate_canvas}")
            result = CaptchaResult.FAIL
            message = "스크래치 없이 정답을 클릭했습니다."
            self.captchaRepo.createCaptchaLog(
                session=session,
                result=result,
                latency_ms=int(latency.total_seconds() * 1000),
                is_correct=False,
                ml_confidence=confidence,
                ml_is_bot=True
            )
            self.usageStatsRepo.incrementVerificationResult(
                session.keyId, result.value, int(latency.total_seconds() * 1000))
            self.db.commit()
            return CaptchaVerificationResponse(result=result.value, message=message, confidence=confidence, verdict="bot")
        return None

    def check_no_mouse_movement(self, session: CaptchaSession, latency: timedelta, behavior_result: Dict[str, Any], confidence: Optional[float]) -> Optional[CaptchaVerificationResponse]:
        n_events = behavior_result.get("stats", {}).get("n_events", 0)
        mean_speed = behavior_result.get("stats", {}).get("speed_mean")
        if mean_speed is not None and mean_speed == 0 and n_events > 1:
            logger.info(
                f"[디버그] 마우스 움직임 없이 정답 클릭 감지. clientToken: {session.clientToken}, mean_speed: {mean_speed}")
            result = CaptchaResult.FAIL
            message = "마우스 움직임 없이 정답을 클릭했습니다."
            self.captchaRepo.createCaptchaLog(
                session=session,
                result=result,
                latency_ms=int(latency.total_seconds() * 1000),
                is_correct=False,
                ml_confidence=confidence,
                ml_is_bot=True
            )
            self.usageStatsRepo.incrementVerificationResult(
                session.keyId, result.value, int(latency.total_seconds() * 1000))
            self.db.commit()
            return CaptchaVerificationResponse(result=result.value, message=message, confidence=confidence, verdict="bot")
        return None

    def check_device_type(self, session_meta: Dict[str, Any]) -> Optional[CaptchaVerificationResponse]:
        if session_meta and session_meta.get("device") == "touch":
            logger.info(f"[디버그] 터치 디바이스 감지. ML 모델 결과 무시하고 human으로 간주합니다.")
            # For touch devices, we consider it human if it passes other rule checks
            # The verdict and confidence will be set later in captcha_service.py
            return CaptchaVerificationResponse(result="success", message="터치 디바이스로 확인되었습니다.", confidence=0.5, verdict="human")
        return None
