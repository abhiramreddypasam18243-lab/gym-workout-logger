"""Data controls API routes for data export and account deletion (spec §6, FR-15, AC-88, AC-89)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_session, verify_csrf
from app.database import get_db
from app.models.user import Session, User
from app.services.data_controls import DataControlsService

router = APIRouter(prefix="/api", tags=["data-controls"])


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Current account password for confirmation")


@router.get("/export")
@router.get("/me/export")
async def export_data(
    response: Response,
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Download complete JSON export of all user-owned data matching published JSON schema (AC-88)."""
    user, _session = auth
    service = DataControlsService(db)
    data = await service.export_user_data(user.id)

    response.headers["Content-Disposition"] = f'attachment; filename="titan_data_export_{user.id}.json"'
    response.headers["Content-Type"] = "application/json"
    return data


@router.delete("/account", status_code=status.HTTP_200_OK)
@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Delete account and all personal data, requiring current password (AC-89)."""
    user, _session = auth
    service = DataControlsService(db)
    return await service.delete_user_account(user.id, payload.password, response)
