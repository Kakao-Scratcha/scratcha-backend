# app/services/rule_check_service.py

import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.captcha_repo import CaptchaRepository
from app.repositories.usage_stats_repo import UsageStatsRepository
from app.schemas.captcha import CaptchaVerificationResponse
from app.models.captcha_log import CaptchaResult
from app.models.captcha_session import CaptchaSession
from datetime import datetime, timezone
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class RuleCheckService:
    def __init__(self, db: Session, captcha_repo: CaptchaRepository, usage_stats_repo: UsageStatsRepository):
        self.db = db
        self.captchaRepo = captcha_repo
        self.usageStatsRepo = usage_stats_repo

    def check_captcha_scratch_rules(self, scratch_percent: int, scratch_time: int):
        # scratch_time은 밀리초 단위로 가정 (0.5초 = 500ms)
        if scratch_time < 500:
            # logger.info(f"CAPTCHA 규칙 위반: 스크래치 시간 너무 짧음 ({scratch_time}ms)")
            return "스크래치 시간이 너무 짧습니다. 최소 0.5초(500ms) 이상이어야 합니다."
        # scratch_percent는 정수 퍼센트 단위로 가정 (1%)
        if scratch_percent < 2:
            # logger.info(f"CAPTCHA 규칙 위반: 스크래치 퍼센트 너무 낮음 ({scratch_percent}%)")
            return "스크래치 퍼센트가 너무 낮습니다. 최소 1% 이상이어야 합니다."
        logger.info(
            f"CAPTCHA 스크래치 규칙 통과: 시간={scratch_time}ms, 퍼센트={scratch_percent}%)")
        return None

    def check_device_type(self, session_meta: Dict[str, Any]) -> Optional[CaptchaVerificationResponse]:
        if session_meta and session_meta.get("device") == "touch":
            logger.info(f"[디버그] 터치 디바이스 감지. ML 모델 결과 무시하고 human으로 간주합니다.")
            # For touch devices, we consider it human if it passes other rule checks
            # The verdict and confidence will be set later in captcha_service.py
            return CaptchaVerificationResponse(result="success", message="터치 디바이스로 확인되었습니다.", confidence=0.5, verdict="human")
        return None

    def check_captcha_timeout(self, created_at: datetime, timeout_seconds: int):
        if (datetime.now(timezone.utc) - created_at).total_seconds() > timeout_seconds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha session timed out")
