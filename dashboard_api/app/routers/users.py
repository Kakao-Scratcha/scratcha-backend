# backend/dashboard_api/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from dashboard_api.app.routers.deps import get_db
from dashboard_api.app.schemas.user import UserCreate, UserResponse, UserUpdate
from dashboard_api.app.services.user_service import UserService
from dashboard_api.app.core.security import get_current_user, get_current_admin_user
from dashboard_api.app.models.user import User

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
def get_user(
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


# --- 관리자 전용 API 엔드포인트 추가 ---
@router.get(
    "/admin/all",
    response_model=List[UserResponse],  # 여러 UserResponse 객체를 리스트로 반환
    summary="[관리자] 모든 사용자 조회",
    description="관리자 권한으로 모든 사용자 계정 목록을 조회합니다 (소프트 삭제된 사용자 포함 여부 선택 가능).",
)
def admin_get_all_users(
    include_deleted: bool = False,  # 쿼리 파라미터로 소프트 삭제 사용자 포함 여부 선택
    admin_user: User = Depends(get_current_admin_user),  # 관리자 권한 확인
    userService: UserService = Depends(get_user_service)
):
    users = userService.get_all_users_admin(include_deleted)
    return users


@router.get(
    "/admin/{user_id}",
    response_model=UserResponse,
    summary="[관리자] 특정 사용자 조회",
    description="관리자 권한으로 특정 사용자 계정 정보를 조회합니다 (소프트 삭제된 사용자 포함 여부 선택 가능).",
)
def admin_get_user_by_id(
    user_id: str,
    include_deleted: bool = False,
    admin_user: User = Depends(get_current_admin_user),
    userService: UserService = Depends(get_user_service)
):
    user = userService.get_user_admin(user_id, include_deleted)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


@router.post(
    "/admin/{user_id}/restore",
    response_model=UserResponse,
    summary="[관리자] 특정 사용자 계정 복구",
    description="관리자 권한으로 소프트 삭제된 사용자 계정을 복구합니다.",
)
def admin_restore_user(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user),
    userService: UserService = Depends(get_user_service)
):
    restoredUser = userService.restore_user_admin(user_id)
    if not restoredUser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="계정을 복구할 수 없습니다. 사용자를 찾을 수 없거나 삭제된 계정이 아닙니다."
        )
    return restoredUser

# 관리자가 다른 사용자의 계정을 소프트 삭제하는 기능도 추가 가능


@router.delete(
    "/admin/{user_id}",
    response_model=UserResponse,
    summary="[관리자] 특정 사용자 계정 소프트 삭제",
    description="관리자 권한으로 특정 사용자 계정을 소프트 삭제합니다.",
)
def admin_delete_user(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user),
    userService: UserService = Depends(get_user_service)
):
    deletedUser = userService.delete_user(user_id)
    if not deletedUser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자 계정을 삭제할 수 없습니다. 이미 삭제되었거나 사용자를 찾을 수 없습니다."
        )
    return deletedUser
