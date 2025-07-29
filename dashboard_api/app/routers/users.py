# backend/dashboard_api/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.user import UserCreate, UserResponse
from services.user_service import UserService

router = APIRouter(
    prefix="/users",  # 이 라우터의 모든 경로에 자동으로 /users/ 가 붙음
    tags=["users"],
    responses={404: {"description": "Not found"}},

)

# get_user_service 의존성 함수 (서비스 객체 생성 및 주입)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="이메일, 비밀번호, 이름으로 새로운 사용자 계정을 생성합니다.",
)
def signup_user(
    user: UserCreate,
    userService: UserService = Depends(get_user_service)
):
    newUser = userService.create_user(user)

    if newUser is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 이메일입니다."
        )

    return newUser
