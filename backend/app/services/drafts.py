from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import DraftStatus, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.project import Project
from app.models.user import User
from app.schemas.content_draft import ContentDraftCreate, ContentDraftRead, ContentDraftUpdate
from app.services.audit import record_audit_log


def _coerce_status(value: DraftStatus | str) -> DraftStatus:
    return value if isinstance(value, DraftStatus) else DraftStatus(value)


def _serialize_draft(draft: ContentDraft) -> ContentDraftRead:
    status = _coerce_status(draft.status)
    return ContentDraftRead(
        id=draft.id,
        campaign_id=draft.campaign_id,
        campaign_name=draft.campaign.name,
        project_id=draft.campaign.project_id,
        project_name=draft.campaign.project.name,
        brand_id=draft.campaign.project.brand_id,
        brand_name=draft.campaign.project.brand.name,
        title=draft.title,
        platform=draft.platform,
        content_type=draft.content_type,
        content_body=draft.content_body,
        status=status,
        planned_publish_at=draft.planned_publish_at,
        current_version_number=draft.current_version_number,
        created_by=draft.created_by,
        creator_name=draft.creator.full_name if draft.creator else None,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _get_draft_with_role(db: Session, *, draft_id: int, user_id: int) -> tuple[ContentDraft, BrandMembership]:
    row = db.execute(
        select(ContentDraft, BrandMembership)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(ContentDraft.campaign).selectinload(Campaign.project).selectinload(Project.brand),
            joinedload(ContentDraft.creator),
        )
        .where(
            ContentDraft.id == draft_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this draft.")

    return row[0], row[1]


def list_drafts(
    db: Session,
    *,
    user: User,
    campaign_id: int | None = None,
    platform: str | None = None,
    status: DraftStatus | None = None,
    search: str | None = None,
) -> list[ContentDraftRead]:
    query = (
        select(ContentDraft)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(ContentDraft.campaign).selectinload(Campaign.project).selectinload(Project.brand),
            joinedload(ContentDraft.creator),
        )
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(ContentDraft.updated_at.desc())
    )
    if campaign_id is not None:
        query = query.where(ContentDraft.campaign_id == campaign_id)
    if platform:
        query = query.where(ContentDraft.platform.ilike(platform.strip()))
    if status is not None:
        query = query.where(ContentDraft.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                ContentDraft.title.ilike(term),
                ContentDraft.content_body.ilike(term),
                ContentDraft.content_type.ilike(term),
            )
        )

    drafts = db.scalars(query).all()
    return [_serialize_draft(draft) for draft in drafts]


def get_draft(db: Session, *, draft_id: int, user: User) -> ContentDraftRead:
    draft, _ = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    return _serialize_draft(draft)


def create_draft(db: Session, *, payload: ContentDraftCreate, user: User) -> ContentDraftRead:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Campaign.project).selectinload(Project.brand))
        .where(
            Campaign.id == payload.campaign_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")

    campaign, membership = row[0], row[1]
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to create drafts.",
    )

    draft = ContentDraft(
        campaign_id=campaign.id,
        title=payload.title.strip(),
        platform=payload.platform.strip(),
        content_type=payload.content_type.strip(),
        content_body=payload.content_body,
        status=_coerce_status(payload.status),
        planned_publish_at=payload.planned_publish_at,
        created_by=user.id,
    )
    db.add(draft)
    db.flush()

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="content_draft",
        entity_id=draft.id,
        action="draft.created",
        metadata={"campaign_id": campaign.id, "status": _coerce_status(draft.status).value},
    )
    db.commit()
    db.refresh(draft)
    return get_draft(db, draft_id=draft.id, user=user)


def update_draft(db: Session, *, draft_id: int, payload: ContentDraftUpdate, user: User) -> ContentDraftRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update drafts.",
    )

    data = payload.model_dump(exclude_unset=True)
    previous_status = _coerce_status(draft.status)
    for field, value in data.items():
        if field == "status" and value is not None:
            setattr(draft, field, _coerce_status(value))
        else:
            setattr(draft, field, value.strip() if isinstance(value, str) else value)

    current_status = _coerce_status(draft.status)
    if "status" in data and current_status != previous_status:
        record_audit_log(
            db,
            brand_id=draft.campaign.project.brand_id,
            actor_user_id=user.id,
            entity_type="content_draft",
            entity_id=draft.id,
            action="draft.status_changed",
            metadata={"from": previous_status.value, "to": current_status.value},
        )

    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)


def delete_draft(db: Session, *, draft_id: int, user: User) -> None:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to delete drafts.",
    )
    db.delete(draft)
    db.commit()
