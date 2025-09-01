# schemas/api_key.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.api_key import Difficulty

# API 키 응답 스키마


class ApiKeyResponse(BaseModel):
    id: int = Field(..., description="API 키의 고유 식별자", example=1)
    key: str = Field(..., description="발급된 API 키 문자열",
                     example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    isActive: bool = Field(..., description="API 키의 활성 상태", example=True)
    difficulty: Difficulty = Field(...,
                                   description="캡챠 난이도", example=Difficulty.MIDDLE)
    expiresAt: Optional[datetime] = Field(
        None, description="API 키의 만료 일시", example="2025-12-31T23:59:59")
    createdAt: datetime = Field(..., description="API 키 생성 일시",
                                example="2024-01-01T12:00:00")
    updatedAt: datetime = Field(..., description="API 키 마지막 수정 일시",
                                example="2024-01-01T12:00:00")
    deletedAt: Optional[datetime] = Field(
        None, description="API 키 삭제 일시", example=None)

    class Config:
        from_attributes = True


class ApiKeyUpdate(BaseModel):
    # 만료 정책 업데이트
    expiresPolicy: Optional[int] = Field(
        None, description="새로운 API 키 만료 정책(일 단위, 0은 무제한)", example=30)
    difficulty: Optional[Difficulty] = Field(
        None, description="캡챠 난이도", example=Difficulty.HIGH)

    class Config:
        from_attributes = True
