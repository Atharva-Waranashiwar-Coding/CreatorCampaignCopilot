from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import BrandRole, MembershipStatus
from app.core.permissions import BRAND_MANAGEMENT_ROLES, BRAND_OWNER_ONLY_ROLES, require_role
from app.models.brand import Brand
from app.models.brand_membership import BrandMembership
from app.models.project import Project
from app.models.user import User
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate
from app.schemas.membership import MembershipInviteRequest, MembershipRead, MembershipUpdate
from app.schemas.user import UserRead
from app.services.audit import record_audit_log
from app.services.auth import get_user_by_email


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "brand"


def _unique_slug(db: Session, slug: str, *, exclude_brand_id: int | None = None) -> str:
    candidate = slug
    suffix = 2

    while True:
        query = select(Brand.id).where(Brand.slug == candidate)
        if exclude_brand_id is not None:
            query = query.where(Brand.id != exclude_brand_id)

        if db.scalar(query) is None:
            return candidate

        candidate = f"{slug}-{suffix}"
        suffix += 1


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _serialize_brand(brand: Brand, role: BrandRole) -> BrandRead:
    campaign_count = sum(len(project.campaigns) for project in brand.projects)
    return BrandRead(
        id=brand.id,
        name=brand.name,
        slug=brand.slug,
        description=brand.description,
        industry=brand.industry,
        tone_of_voice=brand.tone_of_voice,
        target_audience=brand.target_audience,
        preferred_channels=brand.preferred_channels,
        guidelines_summary=brand.guidelines_summary,
        created_by=brand.created_by,
        created_at=brand.created_at,
        updated_at=brand.updated_at,
        current_user_role=role,
        membership_count=len(brand.memberships),
        project_count=len(brand.projects),
        campaign_count=campaign_count,
    )


def _serialize_membership(membership: BrandMembership) -> MembershipRead:
    return MembershipRead(
        id=membership.id,
        brand_id=membership.brand_id,
        user_id=membership.user_id,
        invite_email=membership.invite_email,
        invited_by_id=membership.invited_by_id,
        role=membership.role,
        status=membership.status,
        invited_at=membership.invited_at,
        joined_at=membership.joined_at,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user=UserRead.model_validate(membership.user) if membership.user else None,
    )


def get_membership_for_brand(db: Session, *, brand_id: int, user_id: int) -> BrandMembership:
    membership = db.scalar(
        select(BrandMembership)
        .options(
            selectinload(BrandMembership.brand).selectinload(Brand.projects).selectinload(Project.campaigns),
            selectinload(BrandMembership.brand).selectinload(Brand.memberships),
        )
        .where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise PermissionError("You do not have access to this brand.")

    return membership


def list_brands(db: Session, *, user: User) -> list[BrandRead]:
    memberships = db.scalars(
        select(BrandMembership)
        .options(
            selectinload(BrandMembership.brand).selectinload(Brand.projects).selectinload(Project.campaigns),
            selectinload(BrandMembership.brand).selectinload(Brand.memberships),
        )
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()

    memberships = sorted(memberships, key=lambda item: item.brand.name.lower())
    return [_serialize_brand(membership.brand, membership.role) for membership in memberships]


def get_brand(db: Session, *, brand_id: int, user: User) -> BrandRead:
    membership = get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)
    return _serialize_brand(membership.brand, membership.role)


def create_brand(db: Session, *, payload: BrandCreate, user: User) -> BrandRead:
    brand = Brand(
        name=payload.name.strip(),
        slug=_unique_slug(db, _slugify(payload.slug or payload.name)),
        description=payload.description,
        industry=payload.industry,
        tone_of_voice=payload.tone_of_voice,
        target_audience=payload.target_audience,
        preferred_channels=payload.preferred_channels,
        guidelines_summary=payload.guidelines_summary,
        created_by=user.id,
    )
    db.add(brand)
    db.flush()

    membership = BrandMembership(
        brand_id=brand.id,
        user_id=user.id,
        invite_email=_normalize_email(user.email),
        invited_by_id=user.id,
        role=BrandRole.OWNER,
        status=MembershipStatus.ACTIVE,
        joined_at=datetime.now(UTC),
    )
    db.add(membership)
    db.flush()

    record_audit_log(
        db,
        brand_id=brand.id,
        actor_user_id=user.id,
        entity_type="brand",
        entity_id=brand.id,
        action="brand.created",
        metadata={"name": brand.name, "slug": brand.slug},
    )

    db.commit()
    db.refresh(membership)
    return get_brand(db, brand_id=brand.id, user=user)


def update_brand(db: Session, *, brand_id: int, payload: BrandUpdate, user: User) -> BrandRead:
    membership = get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)
    require_role(membership.role, BRAND_MANAGEMENT_ROLES, "You do not have permission to update this brand.")

    brand = membership.brand
    changes: dict[str, object] = {}
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        brand.name = str(data["name"]).strip()
        changes["name"] = brand.name
    if "slug" in data:
        desired_slug = _slugify(str(data["slug"] or brand.name))
        brand.slug = _unique_slug(db, desired_slug, exclude_brand_id=brand.id)
        changes["slug"] = brand.slug
    for field in [
        "description",
        "industry",
        "tone_of_voice",
        "target_audience",
        "preferred_channels",
        "guidelines_summary",
    ]:
        if field in data:
            setattr(brand, field, data[field])
            changes[field] = data[field]

    record_audit_log(
        db,
        brand_id=brand.id,
        actor_user_id=user.id,
        entity_type="brand",
        entity_id=brand.id,
        action="brand.updated",
        metadata={"changes": changes},
    )
    db.commit()
    db.refresh(brand)
    return _serialize_brand(brand, membership.role)


def delete_brand(db: Session, *, brand_id: int, user: User) -> None:
    membership = get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)
    require_role(membership.role, BRAND_OWNER_ONLY_ROLES, "Only the brand owner can delete a brand.")
    db.delete(membership.brand)
    db.commit()


def list_memberships(db: Session, *, brand_id: int, user: User) -> list[MembershipRead]:
    membership = get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)
    require_role(membership.role, BRAND_MANAGEMENT_ROLES, "You do not have permission to view memberships.")

    memberships = db.scalars(
        select(BrandMembership)
        .options(joinedload(BrandMembership.user))
        .where(BrandMembership.brand_id == brand_id)
        .order_by(BrandMembership.invited_at.desc())
    ).all()
    return [_serialize_membership(item) for item in memberships]


def invite_membership(
    db: Session,
    *,
    brand_id: int,
    payload: MembershipInviteRequest,
    user: User,
) -> MembershipRead:
    membership = get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)
    require_role(membership.role, BRAND_MANAGEMENT_ROLES, "You do not have permission to invite members.")

    email = _normalize_email(str(payload.email))
    existing = db.scalar(
        select(BrandMembership).where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.invite_email == email,
        )
    )
    if existing is not None:
        raise ValueError("That email already has a membership or pending invite for this brand.")

    invited_user = get_user_by_email(db, email)
    invited_membership = BrandMembership(
        brand_id=brand_id,
        user_id=invited_user.id if invited_user else None,
        invite_email=email,
        invited_by_id=user.id,
        role=payload.role,
        status=MembershipStatus.ACTIVE if invited_user else MembershipStatus.INVITED,
        joined_at=datetime.now(UTC) if invited_user else None,
    )
    db.add(invited_membership)
    db.flush()

    record_audit_log(
        db,
        brand_id=brand_id,
        actor_user_id=user.id,
        entity_type="brand_membership",
        entity_id=invited_membership.id,
        action="membership.invited",
        metadata={"email": email, "role": payload.role.value},
    )

    db.commit()
    db.refresh(invited_membership)
    return _serialize_membership(invited_membership)


def update_membership(
    db: Session,
    *,
    brand_id: int,
    membership_id: int,
    payload: MembershipUpdate,
    user: User,
) -> MembershipRead:
    acting_membership = get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)
    require_role(acting_membership.role, BRAND_MANAGEMENT_ROLES, "You do not have permission to manage memberships.")

    membership = db.scalar(
        select(BrandMembership)
        .options(joinedload(BrandMembership.user))
        .where(
            BrandMembership.id == membership_id,
            BrandMembership.brand_id == brand_id,
        )
    )
    if membership is None:
        raise LookupError("Membership not found.")
    if membership.role == BrandRole.OWNER:
        raise ValueError("Owner membership updates are not supported in phase 1.")

    changes = payload.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] is not None:
        membership.role = changes["role"]
    if "status" in changes and changes["status"] is not None:
        membership.status = changes["status"]
        if changes["status"] == MembershipStatus.ACTIVE and membership.joined_at is None:
            membership.joined_at = datetime.now(UTC)

    record_audit_log(
        db,
        brand_id=brand_id,
        actor_user_id=user.id,
        entity_type="brand_membership",
        entity_id=membership.id,
        action="membership.updated",
        metadata={"changes": {key: str(value) for key, value in changes.items()}},
    )
    db.commit()
    db.refresh(membership)
    return _serialize_membership(membership)
