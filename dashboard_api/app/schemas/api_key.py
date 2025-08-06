# dashboard_api/app/schemas/api_key.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# API 키 응답 스키마


class ApiKeyResponse(BaseModel):
    id: int
    key: str = Field(..., description="발급된 API 키 문자열")
    isActive: bool
    expiresAt: Optional[datetime]
    createdAt: datetime
    updatedAt: datetime
    deletedAt: Optional[datetime]

    class Config:
        from_attributes = True
