from sqladmin import Admin, ModelView
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.user import User
from app.models.api_key import ApiKey
from app.models.application import Application
from app.models.captcha_log import CaptchaLog
from app.models.captcha_problem import CaptchaProblem
from app.models.captcha_session import CaptchaSession
from app.models.usage_stats import UsageStats


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.email,
        User.userName,
        User.role,
        # User.plan,
        User.token,
        User.createdAt,
        User.updatedAt,
        User.deletedAt,
    ]
    column_details_list = column_list
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        User.id: "id",
        User.email: "email",
        User.userName: "user_name",
        User.role: "role",
        # User.plan: "plan",
        User.token: "token",
        User.createdAt: "created_at",
        User.updatedAt: "updated_at",
        User.deletedAt: "deleted_at",
    }


class ApplicationAdmin(ModelView, model=Application):
    column_list = [
        Application.id,
        Application.userId,
        Application.appName,
        Application.description,
        Application.createdAt,
        Application.updatedAt,
        Application.deletedAt,
    ]
    column_details_list = column_list
    name = "Application"
    name_plural = "Applications"
    icon = "fa-solid fa-cube"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        Application.id: "id",
        Application.userId: "user_id",
        Application.appName: "app_name",
        Application.description: "description",
        Application.createdAt: "created_at",
        Application.updatedAt: "updated_at",
        Application.deletedAt: "deleted_at",
    }


class ApiKeyAdmin(ModelView, model=ApiKey):
    column_list = [
        ApiKey.id,
        ApiKey.userId,
        ApiKey.appId,
        ApiKey.key,
        ApiKey.isActive,
        ApiKey.difficulty,
        ApiKey.expiresAt,
        ApiKey.createdAt,
        ApiKey.updatedAt,
        ApiKey.deletedAt,
    ]
    column_details_list = column_list
    name = "API Key"
    name_plural = "API Keys"
    icon = "fa-solid fa-key"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        ApiKey.id: "id",
        ApiKey.userId: "user_id",
        ApiKey.appId: "app_id",
        ApiKey.key: "key",
        ApiKey.isActive: "is_active",
        ApiKey.difficulty: "difficulty",
        ApiKey.expiresAt: "expires_at",
        ApiKey.createdAt: "created_at",
        ApiKey.updatedAt: "updated_at",
        ApiKey.deletedAt: "deleted_at",
    }


class CaptchaLogAdmin(ModelView, model=CaptchaLog):
    column_list = [
        CaptchaLog.id,
        CaptchaLog.keyId,
        CaptchaLog.sessionId,
        CaptchaLog.result,
        CaptchaLog.latency_ms,
        CaptchaLog.created_at,
    ]
    column_details_list = column_list
    name = "Captcha Log"
    name_plural = "Captcha Logs"
    icon = "fa-solid fa-clipboard-list"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        CaptchaLog.id: "id",
        CaptchaLog.keyId: "key_id",
        CaptchaLog.sessionId: "session_id",
        CaptchaLog.result: "result",
        CaptchaLog.latency_ms: "latency_ms",
        CaptchaLog.created_at: "created_at",
    }


class CaptchaProblemAdmin(ModelView, model=CaptchaProblem):
    column_list = [
        CaptchaProblem.id,
        CaptchaProblem.imageUrl,
        CaptchaProblem.answer,
        CaptchaProblem.wrongAnswer1,
        CaptchaProblem.wrongAnswer2,
        CaptchaProblem.wrongAnswer3,
        CaptchaProblem.prompt,
        CaptchaProblem.difficulty,
        CaptchaProblem.createdAt,
        CaptchaProblem.expiresAt,
    ]
    column_details_list = column_list
    name = "Captcha Problem"
    name_plural = "Captcha Problems"
    icon = "fa-solid fa-puzzle-piece"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        CaptchaProblem.id: "id",
        CaptchaProblem.imageUrl: "image_url",
        CaptchaProblem.answer: "answer",
        CaptchaProblem.wrongAnswer1: "wrong_answer_1",
        CaptchaProblem.wrongAnswer2: "wrong_answer_2",
        CaptchaProblem.wrongAnswer3: "wrong_answer_3",
        CaptchaProblem.prompt: "prompt",
        CaptchaProblem.difficulty: "difficulty",
        CaptchaProblem.createdAt: "created_at",
        CaptchaProblem.expiresAt: "expires_at",
    }


class CaptchaSessionAdmin(ModelView, model=CaptchaSession):
    column_list = [
        CaptchaSession.id,
        CaptchaSession.keyId,
        CaptchaSession.captchaProblemId,
        CaptchaSession.clientToken,
        CaptchaSession.ipAddress,
        CaptchaSession.userAgent,
        CaptchaSession.createdAt,
    ]
    column_details_list = column_list
    name = "Captcha Session"
    name_plural = "Captcha Sessions"
    icon = "fa-solid fa-hourglass-half"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        CaptchaSession.id: "id",
        CaptchaSession.keyId: "key_id",
        CaptchaSession.captchaProblemId: "captcha_problem_id",
        CaptchaSession.ipAddress: "ip_address",
        CaptchaSession.userAgent: "user_agnet",
        CaptchaSession.clientToken: "client_token",
        CaptchaSession.createdAt: "created_at",
    }


class UsageStatsAdmin(ModelView, model=UsageStats):
    column_list = [
        UsageStats.id,
        UsageStats.keyId,
        UsageStats.date,
        UsageStats.captchaTotalRequests,
        UsageStats.captchaSuccessCount,
        UsageStats.captchaFailCount,
        UsageStats.captchaTimeoutCount,
        UsageStats.totalLatencyMs,
        UsageStats.verificationCount,
        UsageStats.avgResponseTimeMs,
        UsageStats.created_at,
    ]
    column_details_list = column_list
    name = "Usage Stats"
    name_plural = "Usage Stats"
    icon = "fa-solid fa-chart-bar"
    # 기본 정렬을 'id' 컬럼 기준으로 내림차순(True)으로 설정합니다.
    column_default_sort = ("id", True)
    column_labels = {
        UsageStats.id: "id",
        UsageStats.keyId: "key_id",
        UsageStats.date: "date",
        UsageStats.captchaTotalRequests: "captcha_total_requests",
        UsageStats.captchaSuccessCount: "captcha_success_count",
        UsageStats.captchaFailCount: "captcha_fail_count",
        UsageStats.captchaTimeoutCount: "captcha_timeout_count",
        UsageStats.totalLatencyMs: "total_latency_ms",
        UsageStats.verificationCount: "verification_count",
        UsageStats.avgResponseTimeMs: "avg_response_time_ms",
        UsageStats.created_at: "created_at",
    }


def setup_admin(app, engine: AsyncEngine):
    admin = Admin(app, engine, base_url="/admin", static_url="/admin/static")
    admin.add_view(UserAdmin)
    admin.add_view(ApplicationAdmin)
    admin.add_view(ApiKeyAdmin)
    admin.add_view(CaptchaProblemAdmin)
    admin.add_view(CaptchaSessionAdmin)
    admin.add_view(CaptchaLogAdmin)
    admin.add_view(UsageStatsAdmin)
    return admin
