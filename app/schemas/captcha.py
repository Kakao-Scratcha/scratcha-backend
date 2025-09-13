# schemas/captcha.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any


class CaptchaProblemResponse(BaseModel):
    clientToken: str = Field(
        ...,
        description="캡챠 문제 해결을 위한 고유 클라이언트 토큰",
        example="48417c81-929b-4595-9c8f-7031819d27fc"
    )
    imageUrl: str = Field(
        ...,
        description="캡챠 이미지에 접근할 수 있는 API URL",
        example="https://objectstorage.kr-central-2.kakaocloud.com/v1/1bb3c9ceb1db43928600b93b2a2b1d50/team2-bucket/quiz_images/low/quiz_bf62f24d-7ec9-49af-8b45-002ee448370d.webp"
    )
    prompt: str = Field(
        ...,
        description="사용자에게 제시되는 캡챠 프롬프트 메시지",
        example="스크래치 후 정답을 선택하세요. 노이즈 59% 알파블랜드 28%"
    )
    options: List[str] = Field(
        ...,
        description="사용자가 선택할 수 있는 옵션 목록",
        example=["고양이", "강아지", "새", "물고기"]
    )

    class Config:
        from_attributes = True


class CaptchaVerificationRequest(BaseModel):
    answer: str = Field(
        ...,
        description="사용자가 선택한 정답",
        example="고양이"
    )
    meta: Optional[Dict[str, Any]] = Field(
        None,
        description="행동 데이터 메타 정보",
        example={
            "device": "mouse",
            "roi_map": {"canvas-container": {"left": 100, "top": 100, "w": 200, "h": 200}},
            "ts_resolution_ms": 1,
        }
    )
    events: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="사용자 행동 이벤트 데이터",
        example=[
            {"type": "pointerdown", "t": 0, "x_raw": 150, "y_raw": 150},
            {"type": "moves", "t": 0, "payload": {"base_t": 0, "dts": [
                10, 10, 10], "xrs": [150, 160, 180], "yrs": [150, 160, 170]}},
            {"type": "click", "t": 1000, "target_role": "answer-1"},
        ]
    )


class CaptchaVerificationResponse(BaseModel):
    result: Literal["success", "fail", "timeout"] = Field(
        ...,
        description="캡챠 검증 결과 (성공, 실패, 시간 초과)",
        example="success"
    )
    message: str = Field(
        ...,
        description="검증 결과에 대한 메시지",
        example="캡챠 검증에 성공했습니다."
    )
    confidence: Optional[float] = Field(
        None,
        description="봇 확률 또는 신뢰도 (0.0 ~ 1.0)",
        example=0.95
    )
    verdict: Optional[Literal["bot", "human", "unclear"]] = Field(
        None,
        description="행동 분석을 통한 봇/사람 판정",
        example="bot"
    )


class CaptchaTaskResponse(BaseModel):
    taskId: str = Field(
        ...,
        description="비동기 캡챠 검증 작업의 고유 ID",
        example="d91206cf-3392-4c36-901a-83feb9d10cde"
    )
