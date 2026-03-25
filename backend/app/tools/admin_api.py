from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tool_usage_log import ToolUsageLogRead
from app.tools.catalog import get_helper_tool_catalog
from app.tools.schemas import HelperToolCatalogResponse
from app.tools.usage import list_recent_tool_usage

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/catalog", response_model=HelperToolCatalogResponse)
def read_helper_tool_catalog(
    current_user: User = Depends(get_current_user),
) -> HelperToolCatalogResponse:
    del current_user
    return get_helper_tool_catalog()


@router.get("/usage", response_model=list[ToolUsageLogRead])
def read_recent_tool_usage(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ToolUsageLogRead]:
    try:
        return list_recent_tool_usage(db, user=current_user, limit=limit)
    except Exception as exc:
        _raise_service_error(exc)
