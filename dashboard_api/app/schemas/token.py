# backend/dashboard_api/app/schemas/token.py

from pydantic import BaseModel


class Token(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"


class TokenData(BaseModel):
    email: str | None = None




