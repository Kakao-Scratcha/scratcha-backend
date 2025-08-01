# dashboard_api/app/schemas/api_key.py

from pydantic import BaseModel, Field
from datetime import datetime

# API 키 응답 스키마


class ApiKeyResponse(BaseModel):
    id: str
    key: str = Field(..., description="발급된 API 키 문자열")
    isActive: bool
    createdAt: datetime
    expiresAt: int  # 0=무제한, 1=1일, 7=7일 등

    class Config:
        from_attributes = True
