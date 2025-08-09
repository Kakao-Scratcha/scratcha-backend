from typing import Any
from sqladmin import ModelView
from starlette.requests import Request

from ..models.user import User
from ..models.application import Application
from ..models.api_key import AppApiKey
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
        User.createdAt,
        User.deletedAt,
    )

    column_sortable_list = (
        User.id,
        User.email,
        User.passwordHash,
        User.role,
        User.createdAt,
        User.deletedAt,
    )
    column_default_sort = (User.id, False)

    column_searchable_list = (User.email, User.role)

    column_labels = {
        User.id: "ID",
        User.email: "Email",
        User.passwordHash: "Password Hash",
        User.role: "Role",
        User.createdAt: "Created At",
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
        Application.deletedAt,
    ]
    column_sortable_list = [
        Application.id,
        Application.user,
        Application.appName,
        Application.createdAt,
        Application.deletedAt,
    ]
    column_default_sort = (Application.id, False)

    column_searchable_list = [
        Application.appName,
        Application.user
    ]

    column_labels = {
        Application.id: "App ID",
        Application.appName: "App Name",
        Application.user: "User Email",
        Application.createdAt: "Created At",
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


class AppApiKeyAdmin(ModelView, model=AppApiKey):
    def is_accessible(self, request: Request) -> bool:
        return True

    def is_visible(self, request: Request) -> bool:
        return True

    column_list = [
        AppApiKey.id,
        AppApiKey.appId,
        AppApiKey.key,
        AppApiKey.isActive,
        AppApiKey.createdAt,
        AppApiKey.expiresAt,
    ]
    column_sortable_list = [
        AppApiKey.id,
        AppApiKey.appId,
        AppApiKey.key,
        AppApiKey.isActive,
        AppApiKey.createdAt,
        AppApiKey.expiresAt,
    ]
    column_default_sort = (AppApiKey.id, False)

    column_searchable_list = [
        AppApiKey.appId,
        AppApiKey.userId
    ]

    column_labels = {
        AppApiKey.id: "Api Key ID",
        AppApiKey.appId: "App ID",
        AppApiKey.key: "API Key",
        AppApiKey.isActive: "Active",
        AppApiKey.createdAt: "Created At",
        AppApiKey.expiresAt: "Expires At",
    }
    page_size = 50
