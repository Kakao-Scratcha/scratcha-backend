# dashboard_api/app/schemas/application.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from dashboard_api.app.schemas.api_key import ApiKeyResponse

# 애플리케이션 생성 요청 스키마


class ApplicationCreate(BaseModel):
    appName: str = Field(..., min_length=1,
                         max_length=100, example="애플리케이션 이름")
    description: Optional[str] = Field(
        None, max_length=500, example="애플리케이션 설명")

# 애플리케이션 업데이트 요청 스키마


class ApplicationUpdate(BaseModel):
    appName: Optional[str] = Field(
        None, min_length=1, max_length=100, example="애플리케이션 이름")
    description: Optional[str] = Field(
        None, max_length=500, example="애플리케이션 설명")

# 애플리케이션 응답 스키마 (데이터베이스 모델을 Pydantic으로 변환)


class ApplicationResponse(BaseModel):
    id: str
    userId: str
    appName: str
    description: Optional[str]
    createdAt: datetime
    deletedAt: Optional[datetime]

    class Config:
        from_attributes = True  # Pydantic v2: orm_mode 대신 from_attributes 사용
