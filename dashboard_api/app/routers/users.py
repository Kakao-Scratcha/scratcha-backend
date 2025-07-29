# backend/dashboard_api/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.user import UserCreate, UserResponse, UserUpdate
from services.user_service import UserService
from core.security import get_current_user
from models.user import User

router = APIRouter(
    prefix="/users",  # 이 라우터의 모든 경로에 자동으로 /users/ 가 붙음
    tags=["users"],
    responses={404: {"description": "Not found"}},

)

# get_user_service 의존성 함수 (서비스 객체 생성 및 주입)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

# 사용자 회원가입


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

#  현재 사용자 프로필 조회


@router.get(
    "/me",
    response_model=UserResponse,
    summary="내 정보 조회",
    description="현재 로그인된 사용자의 정보를 조회합니다."
)
def read_users_me(
    currnetUser: User = Depends(get_current_user),  # get_current_user 의존성 사용
):
    return currnetUser

# 현재 사용자 프로필 업데이트


@router.patch(
    "/me",  # PATCH: 부분 업데이트에 적합
    response_model=UserResponse,
    summary="내 정보 업데이트",
    description="현재 로그인된 사용자의 정보를 업데이트합니다."
)
def update_me(
    userUpdate: UserUpdate,
    currnetUser: User = Depends(get_current_user),
    userService: UserService = Depends(get_user_service)

):
    updatedUser = userService.update_user(currnetUser.id, userUpdate)

    if not updatedUser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    return updatedUser
