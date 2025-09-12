# app/routers/users_router.py

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.core.security import getAuthenticatedUser # Updated import
from app.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 사용자 회원가입",
    description="이메일, 비밀번호, 이름으로 새로운 사용자 계정을 생성합니다.",
)
def signupUser(
    userCreate: UserCreate,
    db: Session = Depends(get_db) # Direct DB session injection
):
    """
    새로운 사용자 계정을 생성합니다.

    Args:
        userCreate (UserCreate): 생성할 사용자의 데이터 (이메일, 비밀번호, 이름).
        userService (UserService): 의존성으로 주입된 사용자 서비스 객체.

    Returns:
        UserResponse: 생성된 사용자의 상세 정보.
    """
    # 1. UserService 인스턴스 생성
    userService = UserService(db)
    # 2. 사용자 서비스의 계정 생성 메서드를 호출합니다.
    newUser = userService.createUser(userCreate)

    # 3. 사용자 생성에 실패(예: 이미 존재하는 이메일)한 경우, 409 Conflict 오류를 발생시킵니다.
    if newUser is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 이메일입니다."
        )

    # 4. 생성된 사용자 정보를 반환합니다。
    return newUser


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="현재 로그인된 사용자 정보 조회",
    description="현재 인증된(로그인된) 사용자의 상세 정보를 조회합니다."
)
def getUser(
    authenticatedUser: User = Depends(getAuthenticatedUser),
):
    """
    현재 인증된 사용자의 정보를 조회합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.

    Returns:
        UserResponse: 현재 사용자의 상세 정보.
    """
    # 1. `getAuthenticatedUser` 의존성을 통해 이미 인증된 사용자 객체가 주입되므로, 해당 객체를 바로 반환합니다.
    return authenticatedUser


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="현재 로그인된 사용자 정보 업데이트",
    description="현재 인증된(로그인된) 사용자의 정보를 부분적으로 업데이트합니다."
)
def updateUser(
    userUpdate: UserUpdate,
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db) # Direct DB session injection

):
    """
    현재 인증된 사용자의 정보를 업데이트합니다.

    Args:
        userUpdate (UserUpdate): 업데이트할 사용자 정보 (스키마).
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        userService (UserService): 의존성으로 주입된 사용자 서비스 객체.

    Returns:
        UserResponse: 업데이트된 사용자의 상세 정보.
    """
    # 1. UserService 인스턴스 생성
    userService = UserService(db)
    # 2. 사용자 서비스의 정보 업데이트 메서드를 호출합니다.
    updatedUser = userService.updateUser(authenticatedUser.id, userUpdate)
    # 3. 업데이트된 사용자 정보를 반환합니다.
    return updatedUser


@router.delete(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="회원 탈퇴 (계정 소프트 삭제)",
    description="현재 로그인된 사용자 계정을 소프트 삭제(비활성화) 처리합니다."
)
def deleteUser(
    authenticatedUser: User = Depends(getAuthenticatedUser),
    db: Session = Depends(get_db) # Direct DB session injection
):
    """
    현재 인증된 사용자 계정을 소프트 삭제합니다.

    Args:
        currentUser (User): `getCurrentUser` 의존성으로 주입된 현재 인증된 사용자 객체.
        userService (UserService): 의존성으로 주입된 사용자 서비스 객체.

    Returns:
        UserResponse: 소프트 삭제 처리된 사용자의 상세 정보.
    """
    # 1. UserService 인스턴스 생성
    userService = UserService(db)
    # 2. 사용자 서비스의 계정 삭제 메서드를 호출합니다.
    deletedUser = userService.deleteUser(authenticatedUser.id)

    # 3. 삭제할 사용자를 찾을 수 없는 경우 (예: 이미 삭제되었거나 존재하지 않는 경우), 404 Not Found 오류를 발생시킵니다.
    if not deletedUser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 4. 삭제 처리된 사용자 정보를 반환합니다.
    return deletedUser


# @router.patch(
#     "/{userId}/plan",
#     response_model=UserResponse,
#     status_code=status.HTTP_200_OK,
#     summary="사용자 플랜 업데이트",
#     description="특정 사용자의 구독 플랜을 업데이트합니다. (관리자 또는 해당 사용자만 가능)",
# )
# def updateUserPlan(
#     userId: int,
#     planUpdate: UserPlanUpdate,
#     currentUser: User = Depends(getAuthenticatedUser),
#     userService: UserService = Depends(getUserService)
# ):
#     """
#     특정 사용자의 구독 플랜을 업데이트합니다.

#     Args:
#         userId (int): 플랜을 업데이트할 사용자의 ID.
#         planUpdate (UserPlanUpdate): 업데이트할 구독 플랜 정보 (스키마).
#         currentUser (User): `getAuthenticatedUser` 의존성으로 주입된 현재 인증된 사용자 객체.

#     Returns:
#         UserResponse: 플랜이 업데이트된 사용자의 상세 정보.
#     """
#     # 1. 사용자 서비스의 구독 플랜 업데이트 메서드를 호출합니다.
#     updatedUser = userService.updateUserPlan(userId, planUpdate, authenticatedUser)
#     # 2. 업데이트된 사용자 정보를 반환합니다.
#     return updatedUser