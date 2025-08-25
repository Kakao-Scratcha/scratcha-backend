# schemas/captcha.py

from pydantic import BaseModel, Field
from typing import List, Literal


class CaptchaProblemResponse(BaseModel):
    clientToken: str = Field(
        ...,
        description="캡챠 문제 해결을 위한 고유 클라이언트 토큰",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ..."
    )
    imageUrl: str = Field(
        ...,
        description="캡챠 이미지의 URL",
        example="https://example.com/captcha/images/12345.png"
    )
    prompt: str = Field(
        ...,
        description="사용자에게 제시되는 캡챠 프롬프트 메시지",
        example="사진속의 동물 혹은 물건은?."
    )
    options: List[str] = Field(
        ...,
        description="사용자가 선택할 수 있는 옵션 목록",
        example=["고양이", "강아지", "새", "물고기"]
    )

    class Config:
        from_attributes = True


class CaptchaVerificationRequest(BaseModel):
    clientToken: str = Field(
        ...,
        description="캡챠 문제 해결을 위해 발급받은 고유 클라이언트 토큰",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ..."
    )
    answer: str = Field(
        ...,
        description="사용자가 선택한 정답",
        example="고양이"
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
