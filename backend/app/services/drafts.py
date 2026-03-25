from collections.abc import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import DraftStageType, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.draft_review import DraftReview
from app.models.draft_version import DraftVersion
from app.models.mention import Mention
from app.models.project import Project
from app.models.user import User
from app.schemas.content_draft import ContentDraftCreate, ContentDraftRead, ContentDraftUpdate
from app.schemas.draft_version import DraftVersionRead
from app.services.access import assert_brand_limit_available
from app.services.audit import record_audit_log
from app.services.draft_workflows import (
    get_brand_draft_workflow,
    get_workflow_stage_or_raise,
    is_workflow_transition_allowed,
)

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


def _coerce_status(value: str | None) -> str | None:
    return str(value) if value is not None else None


def _get_draft_workflow(draft: ContentDraft):
    return get_brand_draft_workflow(draft.campaign.project.brand)


def _stage_metadata(*, status_key: str, draft: ContentDraft):
    workflow = _get_draft_workflow(draft)
    return get_workflow_stage_or_raise(workflow, status_key)


def _serialize_draft(draft: ContentDraft) -> ContentDraftRead:
    stage = _stage_metadata(status_key=draft.status, draft=draft)
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
        status=stage.key,
        status_label=stage.label,
        status_type=stage.stage_type,
        status_color=stage.color,
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
    stage = _stage_metadata(status_key=version.status, draft=draft)
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
        status=stage.key,
        status_label=stage.label,
        status_type=stage.stage_type,
        status_color=stage.color,
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
            selectinload(ContentDraft.reviews).selectinload(DraftReview.mentions).joinedload(Mention.mentioned_user),
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
    status: str | None = None,
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
        status=draft.status,
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

    status_value = draft.status
    if calendar_item is None:
        assert_brand_limit_available(
            db,
            brand_id=draft.campaign.project.brand_id,
            user_id=actor_user_id,
            metric_key="scheduled_items",
            message="Scheduling this draft would exceed the current plan limit.",
        )
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
    workflow = get_brand_draft_workflow(campaign.project.brand)
    requested_status = payload.status or workflow.initial_stage_keys[0]
    initial_stage = get_workflow_stage_or_raise(
        workflow,
        requested_status,
        message_prefix="Draft creation status",
    )
    if not initial_stage.is_initial:
        raise ValueError("New drafts can only start in workflow stages marked as initial.")

    draft = ContentDraft(
        campaign_id=campaign.id,
        title=payload.title.strip(),
        platform=payload.platform.strip(),
        content_type=payload.content_type.strip(),
        content_body=payload.content_body,
        status=initial_stage.key,
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
            "status": draft.status,
            "version_number": draft.current_version_number,
        },
    )
    db.commit()
    db.refresh(draft)
    return get_draft(db, draft_id=draft.id, user=user)


def _validate_editorial_status_transition(*, draft: ContentDraft, next_status: str) -> None:
    workflow = _get_draft_workflow(draft)
    current_status = draft.status
    if current_status == next_status:
        return

    current_stage = get_workflow_stage_or_raise(workflow, current_status)
    next_stage = get_workflow_stage_or_raise(workflow, next_status)

    if not is_workflow_transition_allowed(workflow, current_status, next_status):
        raise ValueError("This draft stage move is not allowed by the brand workflow.")

    if next_stage.stage_type == DraftStageType.REVIEW:
        raise ValueError("Use the submit-for-review action for this draft stage change.")
    if current_stage.stage_type == DraftStageType.REVIEW:
        if next_stage.stage_type == DraftStageType.APPROVED:
            raise ValueError("Use the approve action for this draft stage change.")
        if next_stage.stage_type == DraftStageType.CHANGES_REQUESTED:
            raise ValueError("Use the reject action for this draft stage change so feedback is captured.")
        raise ValueError("Use the review workflow actions for this draft stage transition.")
    if next_stage.stage_type == DraftStageType.APPROVED:
        raise ValueError("Use the approve action for this draft stage change.")
    if next_stage.stage_type == DraftStageType.CHANGES_REQUESTED:
        raise ValueError("Use the reject action for this draft stage change so feedback is captured.")


def update_draft(db: Session, *, draft_id: int, payload: ContentDraftUpdate, user: User) -> ContentDraftRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update drafts.",
    )

    data = payload.model_dump(exclude_unset=True)
    previous_status = draft.status
    changed_fields: list[str] = []
    draft_changes: dict[str, str] = {}

    next_status: str | None = None
    if "status" in data and data["status"] is not None:
        next_status = str(data.pop("status"))
        _validate_editorial_status_transition(draft=draft, next_status=next_status)
        if next_status != previous_status:
            changed_fields.append("status")
            draft_changes["status"] = next_status

    for field, value in data.items():
        normalized = value.strip() if isinstance(value, str) else value
        if getattr(draft, field) == normalized:
            continue
        setattr(draft, field, normalized)
        changed_fields.append(field)
        draft_changes[field] = str(normalized)

    if next_status is not None:
        draft.status = next_status

    current_status = draft.status
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
                "from": previous_status,
                "to": current_status,
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
