# schemas/captcha.py

from pydantic import BaseModel
from typing import List


class CaptchaProblemResponse(BaseModel):
    clientToken: str
    imageUrl: str
    prompt: str
    options: List[str]

    class Config:
        orm_mode = True
