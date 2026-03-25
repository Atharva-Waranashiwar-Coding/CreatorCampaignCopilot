from collections.abc import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import DraftStatus, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.draft_review import DraftReview
from app.models.draft_version import DraftVersion
from app.models.project import Project
from app.models.user import User
from app.schemas.content_draft import ContentDraftCreate, ContentDraftRead, ContentDraftUpdate
from app.schemas.draft_version import DraftVersionRead
from app.services.audit import record_audit_log

EDITORIAL_CREATE_STATUSES = {DraftStatus.IDEA, DraftStatus.DRAFT, DraftStatus.IN_REVIEW}
EDITORIAL_STATUS_TRANSITIONS = {
    DraftStatus.IDEA: {DraftStatus.DRAFT},
    DraftStatus.DRAFT: {DraftStatus.IDEA},
    DraftStatus.APPROVED: {DraftStatus.SCHEDULED, DraftStatus.PUBLISHED},
    DraftStatus.SCHEDULED: {DraftStatus.PUBLISHED},
}
VERSION_TRACKED_FIELDS = {
    "title",
    "platform",
    "content_type",
    "content_body",
    "planned_publish_at",
    "status",
}
CALENDAR_SYNC_FIELDS = {"title", "platform", "planned_publish_at", "status"}
DRAFT_FIELD_LABELS = {
    "title": "title",
    "platform": "platform",
    "content_type": "content type",
    "content_body": "body copy",
    "planned_publish_at": "scheduled publish date",
    "status": "status",
}


def _coerce_status(value: DraftStatus | str) -> DraftStatus:
    return value if isinstance(value, DraftStatus) else DraftStatus(value)


def _serialize_draft(draft: ContentDraft) -> ContentDraftRead:
    status = _coerce_status(draft.status)
    latest_review = draft.reviews[0] if draft.reviews else None
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
        review_count=len(draft.reviews),
        latest_review_action=latest_review.action if latest_review else None,
        latest_reviewed_at=latest_review.created_at if latest_review else None,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _serialize_draft_version(version: DraftVersion) -> DraftVersionRead:
    draft = version.draft
    campaign = draft.campaign
    project = campaign.project
    return DraftVersionRead(
        id=version.id,
        draft_id=version.draft_id,
        draft_title=draft.title,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        project_id=project.id,
        project_name=project.name,
        brand_id=project.brand_id,
        brand_name=project.brand.name,
        version_number=version.version_number,
        title=version.title,
        platform=version.platform,
        content_type=version.content_type,
        content_body=version.content_body,
        status=_coerce_status(version.status),
        planned_publish_at=version.planned_publish_at,
        change_summary=version.change_summary,
        created_by=version.created_by,
        creator_name=version.creator.full_name if version.creator else None,
        created_at=version.created_at,
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
            selectinload(ContentDraft.reviews).joinedload(DraftReview.actor),
            selectinload(ContentDraft.versions).joinedload(DraftVersion.creator),
            selectinload(ContentDraft.calendar_item),
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
            selectinload(ContentDraft.reviews),
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


def list_draft_versions(db: Session, *, draft_id: int, user: User) -> list[DraftVersionRead]:
    draft, _ = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    return [_serialize_draft_version(version) for version in draft.versions]


def _format_changed_fields(fields: Iterable[str]) -> str:
    labels = [DRAFT_FIELD_LABELS[field] for field in fields if field in DRAFT_FIELD_LABELS]
    if not labels:
        return "draft content"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _create_version_snapshot(
    db: Session,
    *,
    draft: ContentDraft,
    actor_user_id: int,
    change_summary: str,
) -> DraftVersion:
    version = DraftVersion(
        draft_id=draft.id,
        version_number=draft.current_version_number,
        title=draft.title,
        platform=draft.platform,
        content_type=draft.content_type,
        content_body=draft.content_body,
        status=_coerce_status(draft.status),
        planned_publish_at=draft.planned_publish_at,
        change_summary=change_summary,
        created_by=actor_user_id,
    )
    db.add(version)
    db.flush()

    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=actor_user_id,
        entity_type="draft_version",
        entity_id=version.id,
        action="draft.version_snapshot_created",
        metadata={
            "campaign_id": draft.campaign_id,
            "draft_id": draft.id,
            "version_number": version.version_number,
            "change_summary": change_summary,
        },
    )
    return version


def _sync_draft_calendar_item(db: Session, *, draft: ContentDraft, actor_user_id: int) -> None:
    calendar_item = draft.calendar_item
    if draft.planned_publish_at is None:
        if calendar_item is not None:
            db.delete(calendar_item)
        return

    status_value = _coerce_status(draft.status).value
    if calendar_item is None:
        calendar_item = CalendarItem(
            brand_id=draft.campaign.project.brand_id,
            campaign_id=draft.campaign_id,
            draft_id=draft.id,
            title=draft.title,
            platform=draft.platform,
            item_type="draft_publish",
            scheduled_for=draft.planned_publish_at,
            status=status_value,
            notes=None,
            created_by=actor_user_id,
        )
        db.add(calendar_item)
        db.flush()
        draft.calendar_item = calendar_item
        return

    calendar_item.title = draft.title
    calendar_item.platform = draft.platform
    calendar_item.scheduled_for = draft.planned_publish_at
    calendar_item.status = status_value


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
    if payload.status not in EDITORIAL_CREATE_STATUSES:
        raise ValueError("New drafts can only start as idea, draft, or in review.")

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

    _create_version_snapshot(
        db,
        draft=draft,
        actor_user_id=user.id,
        change_summary="Initial draft created",
    )
    _sync_draft_calendar_item(db, draft=draft, actor_user_id=user.id)

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="content_draft",
        entity_id=draft.id,
        action="draft.created",
        metadata={
            "campaign_id": campaign.id,
            "status": _coerce_status(draft.status).value,
            "version_number": draft.current_version_number,
        },
    )
    db.commit()
    db.refresh(draft)
    return get_draft(db, draft_id=draft.id, user=user)


def _validate_editorial_status_transition(current_status: DraftStatus, next_status: DraftStatus) -> None:
    if current_status == next_status:
        return

    if next_status in EDITORIAL_STATUS_TRANSITIONS.get(current_status, set()):
        return

    raise ValueError("Use the review workflow actions for this draft status transition.")


def update_draft(db: Session, *, draft_id: int, payload: ContentDraftUpdate, user: User) -> ContentDraftRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update drafts.",
    )

    data = payload.model_dump(exclude_unset=True)
    previous_status = _coerce_status(draft.status)
    changed_fields: list[str] = []
    draft_changes: dict[str, str] = {}

    next_status = None
    if "status" in data and data["status"] is not None:
        next_status = _coerce_status(data.pop("status"))
        _validate_editorial_status_transition(previous_status, next_status)
        if next_status != previous_status:
            changed_fields.append("status")
            draft_changes["status"] = next_status.value

    for field, value in data.items():
        normalized = value.strip() if isinstance(value, str) else value
        if getattr(draft, field) == normalized:
            continue
        setattr(draft, field, normalized)
        changed_fields.append(field)
        draft_changes[field] = str(normalized)

    if next_status is not None:
        draft.status = next_status

    current_status = _coerce_status(draft.status)
    version_fields = [field for field in changed_fields if field in VERSION_TRACKED_FIELDS]
    if version_fields:
        draft.current_version_number += 1
        _create_version_snapshot(
            db,
            draft=draft,
            actor_user_id=user.id,
            change_summary=f"Updated {_format_changed_fields(version_fields)}",
        )

    if next_status is not None and current_status != previous_status:
        record_audit_log(
            db,
            brand_id=draft.campaign.project.brand_id,
            actor_user_id=user.id,
            entity_type="content_draft",
            entity_id=draft.id,
            action="draft.status_changed",
            metadata={
                "campaign_id": draft.campaign_id,
                "from": previous_status.value,
                "to": current_status.value,
            },
        )

    non_status_changes = {key: value for key, value in draft_changes.items() if key != "status"}
    if non_status_changes:
        record_audit_log(
            db,
            brand_id=draft.campaign.project.brand_id,
            actor_user_id=user.id,
            entity_type="content_draft",
            entity_id=draft.id,
            action="draft.updated",
            metadata={
                "campaign_id": draft.campaign_id,
                "changes": non_status_changes,
            },
        )

    if any(field in CALENDAR_SYNC_FIELDS for field in changed_fields):
        _sync_draft_calendar_item(db, draft=draft, actor_user_id=user.id)

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
