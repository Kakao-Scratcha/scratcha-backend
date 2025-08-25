# backend/schemas/token.py

from pydantic import BaseModel, Field


class Token(BaseModel):
    accessToken: str = Field(
        ...,
        description="인증을 위한 액세스 토큰",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ..."
    )
    tokenType: str = Field(
        "Bearer",
        description="토큰 유형",
        example="Bearer"
    )


class TokenData(BaseModel):
    email: str | None = Field(
        None,
        description="토큰에 포함된 사용자의 이메일 주소",
        example="user@example.com"
    )