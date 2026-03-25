from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate
from app.schemas.membership import MembershipInviteRequest, MembershipRead, MembershipUpdate
from app.services.audit import list_brand_audit_logs
from app.services.brands import (
    create_brand,
    delete_brand,
    get_brand,
    invite_membership,
    list_brands,
    list_memberships,
    update_brand,
    update_membership,
)

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[BrandRead])
def read_brands(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BrandRead]:
    return list_brands(db, user=current_user)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand_route(
    payload: BrandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandRead:
    try:
        return create_brand(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{brand_id}", response_model=BrandRead)
def read_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandRead:
    try:
        return get_brand(db, brand_id=brand_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{brand_id}", response_model=BrandRead)
def update_brand_route(
    brand_id: int,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandRead:
    try:
        return update_brand(db, brand_id=brand_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand_route(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_brand(db, brand_id=brand_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{brand_id}/memberships", response_model=list[MembershipRead])
def read_brand_memberships(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MembershipRead]:
    try:
        return list_memberships(db, brand_id=brand_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{brand_id}/memberships", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
def invite_brand_member(
    brand_id: int,
    payload: MembershipInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MembershipRead:
    try:
        return invite_membership(db, brand_id=brand_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{brand_id}/memberships/{membership_id}", response_model=MembershipRead)
def update_brand_member(
    brand_id: int,
    membership_id: int,
    payload: MembershipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MembershipRead:
    try:
        return update_membership(
            db,
            brand_id=brand_id,
            membership_id=membership_id,
            payload=payload,
            user=current_user,
        )
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{brand_id}/audit-logs", response_model=list[AuditLogRead])
def read_brand_audit_logs(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLogRead]:
    try:
        return list_brand_audit_logs(db, brand_id=brand_id, user_id=current_user.id)
    except Exception as exc:
        _raise_service_error(exc)
