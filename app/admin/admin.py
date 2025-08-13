from typing import Any
from sqladmin import ModelView
from starlette.requests import Request

from ..models.user import User
from ..models.application import Application
from ..models.api_key import ApiKey
from ..core.security import get_password_hash


class UserAdmin(ModelView, model=User):

    def is_accessible(self, request: Request) -> bool:
        # Check incoming request
        # For example request.session if using AuthenticationBackend
        return True

    def is_visible(self, request: Request) -> bool:
        # Check incoming request
        # For example request.session if using AuthenticationBackend
        return True

    column_list = (
        User.id,
        User.email,
        User.passwordHash,
        User.role,
        User.plan,
        User.token,
        User.createdAt,
        User.updatedAt,
        User.deletedAt,
    )

    column_sortable_list = (
        User.id,
        User.email,
        User.passwordHash,
        User.role,
        User.plan,
        User.token,
        User.createdAt,
        User.updatedAt,
        User.deletedAt,
    )
    column_default_sort = (User.id, False)

    column_searchable_list = (
        User.id,
        User.email,
        User.passwordHash,
        User.role,
        User.plan,
    )

    column_labels = {
        User.id: "ID",
        User.email: "Email",
        User.passwordHash: "Password Hash",
        User.role: "Role",
        User.plan: "plan",
        User.token: "Token",
        User.createdAt: "Created At",
        User.updatedAt: "Updated At",
        User.deletedAt: "Deleted At",
    }

    page_size = 50

    async def insert_model(self, request: Request, data: dict) -> Any:
        if _password := data.get("passwordHash"):
            data["passwordHash"] = get_password_hash(_password)
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        if _password := data.get("passwordHash"):
            data["passwordHash"] = get_password_hash(_password)
        return await super().update_model(request, pk, data)


class ApplicationAdmin(ModelView, model=Application):
    def is_accessible(self, request: Request) -> bool:
        return True

    def is_visible(self, request: Request) -> bool:
        return True

    column_list = [
        Application.id,
        Application.appName,
        Application.user,
        Application.createdAt,
        Application.updatedAt,
        Application.deletedAt,
    ]
    column_sortable_list = [
        Application.id,
        Application.user,
        Application.appName,
        Application.createdAt,
        Application.updatedAt,
        Application.deletedAt,
    ]
    column_default_sort = (Application.id, False)

    column_searchable_list = [
        Application.id,
        Application.appName,
        Application.user,
    ]

    column_labels = {
        Application.id: "App ID",
        Application.appName: "App Name",
        Application.user: "User Email",
        Application.createdAt: "Created At",
        Application.updatedAt: "Updated At",
        Application.deletedAt: "Deleted At",
    }
    column_formatters = {
        Application.user: lambda m, a: m.user.email if m.user else ""
    }

    form_columns = [
        Application.appName,
        Application.description,
        Application.user
    ]
    page_size = 50

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        if user := data.get("user"):
            data["userId"] = user.id
        return await super().update_model(request, pk, data)


class ApiKeyAdmin(ModelView, model=ApiKey):
    def is_accessible(self, request: Request) -> bool:
        return True

    def is_visible(self, request: Request) -> bool:
        return True

    column_list = [
        ApiKey.id,
        ApiKey.appId,
        ApiKey.key,
        ApiKey.isActive,
        ApiKey.createdAt,
        ApiKey.updatedAt,
        ApiKey.expiresAt,
    ]
    column_sortable_list = [
        ApiKey.id,
        ApiKey.appId,
        ApiKey.key,
        ApiKey.isActive,
        ApiKey.createdAt,
        ApiKey.updatedAt,
        ApiKey.expiresAt,
    ]
    column_default_sort = (ApiKey.id, False)

    column_searchable_list = [
        ApiKey.appId,
        ApiKey.userId
    ]

    column_labels = {
        ApiKey.id: "Key ID",
        ApiKey.appId: "App ID",
        ApiKey.key: "API Key",
        ApiKey.isActive: "Active",
        ApiKey.createdAt: "Created At",
        ApiKey.updatedAt: "Updated At",
        ApiKey.expiresAt: "Expires At",
    }
    page_size = 50
