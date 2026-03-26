from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.project import Project
from app.models.user import User
from app.schemas.calendar_item import CalendarItemCreate, CalendarItemRead, CalendarItemUpdate
from app.services.audit import record_audit_log


def _serialize_calendar_item(item: CalendarItem) -> CalendarItemRead:
    return CalendarItemRead(
        id=item.id,
        brand_id=item.brand_id,
        brand_name=item.campaign.project.brand.name,
        campaign_id=item.campaign_id,
        campaign_name=item.campaign.name,
        draft_id=item.draft_id,
        draft_title=item.draft.title if item.draft else None,
        title=item.title,
        platform=item.platform,
        item_type=item.item_type,
        scheduled_for=item.scheduled_for,
        status=item.status,
        notes=item.notes,
        created_by=item.created_by,
        creator_name=item.creator.full_name if item.creator else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Campaign.project).selectinload(Project.brand))
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")
    return row[0], row[1]


def _get_calendar_item_with_role(db: Session, *, item_id: int, user_id: int) -> tuple[CalendarItem, BrandMembership]:
    row = db.execute(
        select(CalendarItem, BrandMembership)
        .join(Campaign, Campaign.id == CalendarItem.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(CalendarItem.creator),
            joinedload(CalendarItem.draft),
            joinedload(CalendarItem.campaign).joinedload(Campaign.project).joinedload(Project.brand),
        )
        .where(
            CalendarItem.id == item_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise LookupError("Calendar item not found.")
    return row[0], row[1]


def list_calendar_items(
    db: Session,
    *,
    user: User,
    campaign_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[CalendarItemRead]:
    query = (
        select(CalendarItem)
        .join(Campaign, Campaign.id == CalendarItem.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(CalendarItem.creator),
            joinedload(CalendarItem.draft),
            joinedload(CalendarItem.campaign).joinedload(Campaign.project).joinedload(Project.brand),
        )
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(CalendarItem.scheduled_for.asc(), CalendarItem.created_at.asc())
    )
    if campaign_id is not None:
        query = query.where(CalendarItem.campaign_id == campaign_id)
    if start is not None:
        query = query.where(CalendarItem.scheduled_for >= start)
    if end is not None:
        query = query.where(CalendarItem.scheduled_for <= end)

    items = db.scalars(query).all()
    return [_serialize_calendar_item(item) for item in items]


def create_calendar_item(db: Session, *, payload: CalendarItemCreate, user: User) -> CalendarItemRead:
    campaign, membership = _get_campaign_with_role(db, campaign_id=payload.campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign calendar items.",
    )

    item = CalendarItem(
        brand_id=campaign.project.brand_id,
        campaign_id=campaign.id,
        title=payload.title.strip(),
        platform=payload.platform.strip() if payload.platform else None,
        item_type=payload.item_type.strip(),
        scheduled_for=payload.scheduled_for,
        status=payload.status.strip() if payload.status else None,
        notes=payload.notes.strip() if payload.notes else None,
        created_by=user.id,
    )
    db.add(item)
    db.flush()

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="calendar_item",
        entity_id=item.id,
        action="calendar.created",
        metadata={"campaign_id": campaign.id, "item_type": item.item_type},
    )
    db.commit()
    return get_calendar_item(db, item_id=item.id, user=user)


def get_calendar_item(db: Session, *, item_id: int, user: User) -> CalendarItemRead:
    item, _ = _get_calendar_item_with_role(db, item_id=item_id, user_id=user.id)
    return _serialize_calendar_item(item)


def update_calendar_item(db: Session, *, item_id: int, payload: CalendarItemUpdate, user: User) -> CalendarItemRead:
    item, membership = _get_calendar_item_with_role(db, item_id=item_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign calendar items.",
    )
    if item.draft_id is not None:
        raise ValueError("Draft-linked schedule items are managed from the draft detail screen.")

    changes: dict[str, str] = {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        normalized = value.strip() if isinstance(value, str) else value
        if getattr(item, field) == normalized:
            continue
        setattr(item, field, normalized)
        changes[field] = str(normalized)

    if changes:
        record_audit_log(
            db,
            brand_id=item.brand_id,
            actor_user_id=user.id,
            entity_type="calendar_item",
            entity_id=item.id,
            action="calendar.updated",
            metadata={"campaign_id": item.campaign_id, "changes": changes},
        )

    db.commit()
    db.refresh(item)
    return _serialize_calendar_item(item)


def delete_calendar_item(db: Session, *, item_id: int, user: User) -> None:
    item, membership = _get_calendar_item_with_role(db, item_id=item_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign calendar items.",
    )
    if item.draft_id is not None:
        raise ValueError("Draft-linked schedule items are managed from the draft detail screen.")

    record_audit_log(
        db,
        brand_id=item.brand_id,
        actor_user_id=user.id,
        entity_type="calendar_item",
        entity_id=item.id,
        action="calendar.deleted",
        metadata={"campaign_id": item.campaign_id, "item_type": item.item_type},
    )
    db.delete(item)
    db.commit()
