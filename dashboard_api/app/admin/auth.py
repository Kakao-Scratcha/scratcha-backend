from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from sqlalchemy.orm import Session
from dashboard_api.app.models.user import User, UserRole
from dashboard_api.app.core.security import verify_password
from db.session import SessionLocal

class AdminAuth(AuthenticationBackend):
    """
    SQLAdmin 관리자 페이지를 위한 커스텀 인증 백엔드 클래스입니다.
    사용자 로그인, 로그아웃, 그리고 인증 상태 확인 로직을 구현합니다.
    """
    async def login(self, request: Request) -> bool:
        """
        로그인 폼에서 받은 사용자 이름과 비밀번호를 검증합니다.
        사용자가 존재하고, 역할이 'admin'이며, 비밀번호가 일치하는 경우에만 로그인을 승인하고
        세션에 사용자 정보를 저장합니다.
        """
        form = await request.form()
        username, password = form["username"], form["password"]

        # 데이터베이스 세션을 생성하여 사용자 정보를 조회합니다.
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.email == username).first()
        finally:
            db.close() # 세션 사용 후 반드시 닫아줍니다.

        # 사용자 존재 여부, 역할, 비밀번호를 확인합니다.
        if user and user.role == UserRole.ADMIN and verify_password(password, user.passwordHash):
            # 인증 성공 시, 세션에 사용자 ID와 이메일을 저장합니다.
            request.session.update({"user_id": user.id, "user_email": user.email})
            return True

        # 인증 실패 시, False를 반환합니다.
        return False

    async def logout(self, request: Request) -> bool:
        """
        사용자 로그아웃을 처리하고, 세션을 완전히 초기화합니다.
        """
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """
        각 요청에 대해 사용자가 인증된 상태인지 확인합니다.
        세션에 저장된 사용자 ID를 바탕으로 데이터베이스에서 사용자를 조회하고,
        해당 사용자가 'admin' 역할을 가지고 있는지 확인합니다.
        """
        user_id = request.session.get("user_id")

        if not user_id:
            return False

        # 세션에 저장된 ID로 사용자를 다시 조회하여 유효성을 검증합니다.
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()

        # 사용자가 존재하고 여전히 'admin' 역할일 경우에만 인증을 유지합니다.
        if user and user.role == UserRole.ADMIN:
            return True
        
        return False
