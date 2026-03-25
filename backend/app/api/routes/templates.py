from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.content_template import ContentTemplateCreate, ContentTemplateRead, ContentTemplateUpdate
from app.services.templates import create_template, delete_template, get_template, list_templates, update_template

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[ContentTemplateRead])
def read_templates(
    brand_id: int | None = None,
    template_type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContentTemplateRead]:
    return list_templates(
        db,
        user=current_user,
        brand_id=brand_id,
        template_type=template_type,
        search=search,
    )


@router.post("", response_model=ContentTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template_route(
    payload: ContentTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentTemplateRead:
    try:
        return create_template(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{template_id}", response_model=ContentTemplateRead)
def read_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentTemplateRead:
    try:
        return get_template(db, template_id=template_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{template_id}", response_model=ContentTemplateRead)
def update_template_route(
    template_id: int,
    payload: ContentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentTemplateRead:
    try:
        return update_template(db, template_id=template_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template_route(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_template(db, template_id=template_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
