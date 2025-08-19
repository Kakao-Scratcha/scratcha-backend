# app/routers/users_router.py

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserPlanUpdate
from app.services.user_service import UserService
from app.core.security import getCurrentUser
from app.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# get_user_service 의존성 함수 (서비스 객체 생성 및 주입)


def getUserService(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post(  # 사용자 회원가입
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원 가입",
    description="이메일, 비밀번호, 이름으로 새로운 사용자 계정을 생성합니다.",
)
def signupUser(
    user: UserCreate,
    userService: UserService = Depends(getUserService)
):
    newUser = userService.createUser(user)

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
def getUser(
    currnetUser: User = Depends(getCurrentUser),  # getCurrentUser 의존성 사용
):
    return currnetUser


@router.patch(  # 사용자 정보 업데이트
    "/me",  # PATCH: 부분 업데이트에 적합
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="내 정보 업데이트",
    description="현재 로그인된 사용자의 정보를 업데이트합니다."
)
def updateUser(
    userUpdate: UserUpdate,
    currnetUser: User = Depends(getCurrentUser),
    userService: UserService = Depends(getUserService)

):
    updatedUser = userService.updateUser(currnetUser.id, userUpdate)
    return updatedUser


@router.delete(  # 사용자 삭제
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="회원 탈퇴 (계정 소프트 삭제)",
    description="현재 로그인된 사용자 계정을 소프트 삭제합니다. 계정은 비활성화 됩니다."
)
def deleteUser(
    currentUser: User = Depends(getCurrentUser),  # 인증된(JWT) 사용자인지 확인
    userService: UserService = Depends(getUserService)
):
    deletedUser = userService.deleteUser(currentUser.id)

    if not deletedUser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    return deletedUser


@router.patch(
    "/{userId}/plan",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="사용자 플랜 업데이트",
    description="특정 사용자의 구독 플랜을 업데이트합니다. (관리자 또는 해당 사용자만 가능)",
)
def updateUserPlan(
    userId: int,
    planUpdate: UserPlanUpdate,
    currentUser: User = Depends(getCurrentUser),
    userService: UserService = Depends(getUserService)
):
    updatedUser = userService.updateUserPlan(userId, planUpdate, currentUser)
    return updatedUser
