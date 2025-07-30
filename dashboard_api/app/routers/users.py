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


@router.post(  # 사용자 회원가입
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원 가입",
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


@router.get(  # 사용자 정보 조회

    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="내 정보 조회",
    description="현재 로그인된 사용자의 정보를 조회합니다."
)
def read_user(
    currnetUser: User = Depends(get_current_user),  # get_current_user 의존성 사용
):
    return currnetUser


@router.patch(  # 사용자 정보 업데이트
    "/me",  # PATCH: 부분 업데이트에 적합
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="내 정보 업데이트",
    description="현재 로그인된 사용자의 정보를 업데이트합니다."
)
def update_user(
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


@router.delete(  # 사용자 삭제
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="회원 탈퇴 (계정 소프트 삭제)",
    description="현재 로그인된 사용자 계정을 소프트 삭제합니다. 계정은 비활성화 됩니다."
)
def delete_user(
    currentUser: User = Depends(get_current_user),  # 인증된(JWT) 사용자인지 확인
    userService: UserService = Depends(get_user_service)
):
    deletedUser = userService.delete_user(currentUser.id)

    if not deletedUser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    return deletedUser
