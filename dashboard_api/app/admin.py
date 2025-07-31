from typing import Any
from sqladmin import ModelView
from starlette.requests import Request

from dashboard_api.app.models.user import User
from dashboard_api.app.core.security import get_password_hash


class UserAdmin(ModelView, model=User):
    column_list = (
        User.id,
        User.email,
        User.passwordHash,
        User.role,
        User.createdAt,
        User.deletedAt,
    )
    column_searchable_list = (
        User.userName,
    )
    column_sortable_list = (User.id, User.email,)
    column_default_sort = (User.email, False)
    page_size = 50

    async def insert_model(self, request: Request, data: dict) -> Any:
        if _password := data.get("passwordHash"):
            data["passwordHash"] = get_password_hash(_password)
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        if _password := data.get("passwordHash"):
            data["passwordHash"] = get_password_hash(_password)
        return await super().update_model(request, pk, data)
