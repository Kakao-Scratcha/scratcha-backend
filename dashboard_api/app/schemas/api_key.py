# dashboard_api/app/schemas/api_key.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# API 키 응답 스키마


class ApiKeyResponse(BaseModel):
    id: str
    key: str = Field(..., description="발급된 API 키 문자열")
    isActive: bool
    createdAt: datetime
    expiresAt: Optional[datetime] = Field(None, description="API 키 만료 시점. null이면 무기한")

    class Config:
        from_attributes = True
