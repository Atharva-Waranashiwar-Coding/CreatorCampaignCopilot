from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    AssignmentEntityType,
    BrandRole,
    CampaignDependencyNodeType,
    CampaignMilestoneKey,
    CampaignStatus,
    CommentEntityType,
    DraftStatus,
    HelperArtifactStatus,
    HelperArtifactType,
    MembershipStatus,
    NotificationType,
    PlanInterval,
)
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal
from app.models.assignment import Assignment
from app.models.brand import Brand
from app.models.brand_membership import BrandMembership
from app.models.brand_subscription import BrandSubscription
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.campaign_asset import CampaignAsset
from app.models.campaign_dependency import CampaignDependency
from app.models.campaign_milestone import CampaignMilestone
from app.models.collaboration_comment import CollaborationComment
from app.models.content_brief import ContentBrief
from app.models.content_draft import ContentDraft
from app.models.content_template import ContentTemplate
from app.models.draft_review import DraftReview
from app.models.draft_helper_artifact import DraftHelperArtifact
from app.models.draft_version import DraftVersion
from app.models.mention import Mention
from app.models.project import Project
from app.models.tool_usage_log import ToolUsageLog
from app.models.user import User
from app.schemas.assignment import AssignmentCreate
from app.schemas.billing import BrandSubscriptionUpdate
from app.schemas.brand import BrandCreate
from app.schemas.campaign import CampaignCreate
from app.schemas.content_draft import ContentDraftCreate, ContentDraftUpdate
from app.schemas.content_template import ContentTemplateCreate
from app.schemas.draft_review import DraftReviewCreate, DraftReviewDecision
from app.schemas.project import ProjectCreate
from app.services.access import get_brand_billing_snapshot, update_brand_subscription
from app.services.assignments import create_campaign_assignment, create_draft_assignment
from app.services.brands import create_brand
from app.services.campaigns import create_campaign
from app.services.campaign_milestones import ensure_campaign_milestones
from app.services.drafts import create_draft, update_draft
from app.services.notifications import notify_users
from app.services.projects import create_project
from app.services.reviews import add_review_comment, approve_draft, reject_draft, submit_draft_for_review
from app.services.templates import create_template

OWNER_PROFILE = {
    "email": "waranashiwaratharva@gmail.com",
    "full_name": "Atharva Waranashiwar",
}

DEMO_USERS = (
    {
        "email": "maya.chen.demo@example.com",
        "legacy_emails": ("maya.chen.demo@creatorcopilot.local",),
        "full_name": "Maya Chen",
    },
    {
        "email": "jordan.patel.demo@example.com",
        "legacy_emails": ("jordan.patel.demo@creatorcopilot.local",),
        "full_name": "Jordan Patel",
    },
    {
        "email": "leo.morgan.demo@example.com",
        "legacy_emails": ("leo.morgan.demo@creatorcopilot.local",),
        "full_name": "Leo Morgan",
    },
    {
        "email": "sofia.alvarez.demo@example.com",
        "legacy_emails": ("sofia.alvarez.demo@creatorcopilot.local",),
        "full_name": "Sofia Alvarez",
    },
)


def ensure_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str | None = None,
    legacy_emails: tuple[str, ...] = (),
) -> User:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        for legacy_email in legacy_emails:
            user = db.scalar(select(User).where(User.email == legacy_email.strip().lower()))
            if user is not None:
                break
    if user is not None:
        user.email = normalized_email
        user.full_name = full_name
        if password:
            user.password_hash = hash_password(password)
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=normalized_email,
        full_name=full_name,
        password_hash=hash_password(password or "demo-pass-1234"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_application_data(db: Session, *, preserve_user_email: str | None = None) -> None:
    preserved_email = preserve_user_email.strip().lower() if preserve_user_email else None

    for table in reversed(Base.metadata.sorted_tables):
        if table.name in {"plans", "users"}:
            continue
        db.execute(table.delete())

    if preserved_email:
        db.execute(User.__table__.delete().where(User.email != preserved_email))
    else:
        db.execute(User.__table__.delete())

    db.commit()


def offset_datetime(anchor: datetime, days: int, *, hour: int = 9, minute: int = 0) -> datetime:
    return (anchor + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def offset_date(anchor: datetime, days: int) -> date:
    return offset_datetime(anchor, days).date()


def at_date(value: date, *, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(value.year, value.month, value.day, hour, minute, tzinfo=UTC)


def evenly_spaced_datetimes(start: datetime, end: datetime, count: int) -> list[datetime]:
    if count <= 0:
        return []
    if count == 1 or end <= start:
        return [end]

    step = (end - start) / count
    return [start + step * (index + 1) for index in range(count)]


def stamp_record(record: object, *, created_at: datetime | None = None, updated_at: datetime | None = None) -> None:
    if created_at is not None and hasattr(record, "created_at"):
        setattr(record, "created_at", created_at)
    if updated_at is not None and hasattr(record, "updated_at"):
        setattr(record, "updated_at", updated_at)


def stamp_draft_timeline(
    draft: ContentDraft,
    *,
    created_at: datetime,
    updated_at: datetime,
) -> None:
    stamp_record(draft, created_at=created_at, updated_at=updated_at)

    versions = sorted(draft.versions, key=lambda item: item.version_number)
    version_end = max(created_at + timedelta(hours=2), updated_at - timedelta(hours=max(2, len(draft.reviews) * 4)))
    for version, version_time in zip(versions, evenly_spaced_datetimes(created_at, version_end, len(versions)), strict=False):
        version.created_at = version_time

    reviews = sorted(draft.reviews, key=lambda item: item.created_at)
    review_start = max(created_at + timedelta(hours=4), updated_at - timedelta(hours=max(6, len(reviews) * 4)))
    for review, review_time in zip(reviews, evenly_spaced_datetimes(review_start, updated_at, len(reviews)), strict=False):
        review.created_at = review_time

    if draft.calendar_item is not None:
        calendar_created_at = created_at + timedelta(hours=3)
        if draft.planned_publish_at is not None:
            calendar_created_at = min(calendar_created_at, draft.planned_publish_at - timedelta(days=1))
        if calendar_created_at < created_at:
            calendar_created_at = created_at + timedelta(hours=3)
        stamp_record(draft.calendar_item, created_at=calendar_created_at, updated_at=max(calendar_created_at, updated_at))


def create_campaign_asset_record(
    db: Session,
    *,
    campaign: Campaign,
    owner: User,
    name: str,
    asset_type: str,
    file_url: str,
    notes: str,
    created_at: datetime,
    thumbnail_url: str | None = None,
    mime_type: str | None = None,
    file_size_bytes: int | None = None,
) -> CampaignAsset:
    asset = CampaignAsset(
        campaign_id=campaign.id,
        name=name,
        asset_type=asset_type,
        file_url=file_url,
        thumbnail_url=thumbnail_url,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        notes=notes,
        created_by=owner.id,
    )
    db.add(asset)
    db.flush()
    stamp_record(asset, created_at=created_at, updated_at=created_at)
    return asset


def create_manual_calendar_item(
    db: Session,
    *,
    brand: Brand,
    campaign: Campaign,
    owner: User,
    title: str,
    platform: str | None,
    item_type: str,
    scheduled_for: datetime,
    status: str,
    notes: str,
) -> CalendarItem:
    item = CalendarItem(
        brand_id=brand.id,
        campaign_id=campaign.id,
        draft_id=None,
        title=title,
        platform=platform,
        item_type=item_type,
        scheduled_for=scheduled_for,
        status=status,
        notes=notes,
        created_by=owner.id,
    )
    db.add(item)
    db.flush()
    stamp_record(item, created_at=scheduled_for - timedelta(days=1), updated_at=scheduled_for - timedelta(hours=2))
    return item


def create_comment_record(
    db: Session,
    *,
    brand: Brand,
    campaign: Campaign | None,
    draft: ContentDraft | None,
    author: User,
    body: str,
    created_at: datetime,
    mentioned_user: User | None = None,
    parent_comment: CollaborationComment | None = None,
) -> CollaborationComment:
    entity_type = CommentEntityType.DRAFT if draft is not None else CommentEntityType.CAMPAIGN
    entity_id = draft.id if draft is not None else campaign.id
    if entity_id is None:
        raise ValueError("Comment record requires either a draft or campaign target.")

    comment = CollaborationComment(
        brand_id=brand.id,
        entity_type=entity_type,
        entity_id=entity_id,
        campaign_id=campaign.id if campaign is not None else None,
        draft_id=draft.id if draft is not None else None,
        parent_comment_id=parent_comment.id if parent_comment is not None else None,
        author_user_id=author.id,
        body=body,
    )
    db.add(comment)
    db.flush()
    stamp_record(comment, created_at=created_at, updated_at=created_at)

    if mentioned_user is not None:
        mention = Mention(
            brand_id=brand.id,
            author_user_id=author.id,
            mentioned_user_id=mentioned_user.id,
            identifier=f"@{mentioned_user.full_name.split()[0].lower()}",
            comment_id=comment.id,
            draft_review_id=None,
        )
        mention.created_at = created_at + timedelta(minutes=1)
        db.add(mention)

    return comment


def create_tool_usage_entry(
    db: Session,
    *,
    tool_name: str,
    actor: User,
    brand: Brand,
    campaign: Campaign | None,
    draft: ContentDraft | None,
    target_entity_type: str,
    target_entity_id: int | None,
    created_at: datetime,
    request_payload: dict[str, object],
    result_summary: dict[str, object],
    was_successful: bool = True,
    error_detail: str | None = None,
) -> ToolUsageLog:
    entry = ToolUsageLog(
        tool_name=tool_name,
        actor_user_id=actor.id,
        brand_id=brand.id,
        campaign_id=campaign.id if campaign is not None else None,
        draft_id=draft.id if draft is not None else None,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        invocation_source="seed",
        was_successful=was_successful,
        error_detail=error_detail,
        request_payload=request_payload,
        result_summary=result_summary,
        request_trace=request_payload,
        result_trace=result_summary,
        created_at=created_at,
    )
    db.add(entry)
    db.flush()
    return entry


def create_helper_artifact_record(
    db: Session,
    *,
    draft: ContentDraft,
    creator: User,
    tool_name: str,
    artifact_type: HelperArtifactType,
    title: str,
    summary: str,
    payload: dict[str, object],
    created_at: datetime,
    status: HelperArtifactStatus = HelperArtifactStatus.SAVED,
    source_log: ToolUsageLog | None = None,
) -> DraftHelperArtifact:
    artifact = DraftHelperArtifact(
        draft_id=draft.id,
        tool_name=tool_name,
        artifact_type=artifact_type,
        title=title,
        summary=summary,
        payload=payload,
        status=status,
        source_tool_usage_log_id=source_log.id if source_log is not None else None,
        created_by=creator.id,
    )
    db.add(artifact)
    db.flush()
    stamp_record(artifact, created_at=created_at, updated_at=created_at)
    return artifact


def repair_legacy_draft_statuses(db: Session) -> None:
    legacy_status_map = {status.name: status.value for status in DraftStatus}

    drafts = db.scalars(
        select(ContentDraft).where(ContentDraft.status.in_(legacy_status_map))
    ).all()
    for draft in drafts:
        draft.status = legacy_status_map.get(draft.status, draft.status)

    versions = db.scalars(
        select(DraftVersion).where(DraftVersion.status.in_(legacy_status_map))
    ).all()
    for version in versions:
        version.status = legacy_status_map.get(version.status, version.status)

    reviews = db.scalars(
        select(DraftReview).where(
            DraftReview.from_status.in_(legacy_status_map) | DraftReview.to_status.in_(legacy_status_map)
        )
    ).all()
    for review in reviews:
        if review.from_status in legacy_status_map:
            review.from_status = legacy_status_map[review.from_status]
        if review.to_status in legacy_status_map:
            review.to_status = legacy_status_map[review.to_status]

    if drafts or versions or reviews:
        db.commit()


def ensure_membership(
    db: Session,
    *,
    brand_id: int,
    invite_email: str,
    user_id: int,
    invited_by_id: int,
    role: BrandRole,
) -> BrandMembership:
    membership = db.scalar(
        select(BrandMembership).where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.invite_email == invite_email,
        )
    )
    if membership is None:
        membership = db.scalar(
            select(BrandMembership).where(
                BrandMembership.brand_id == brand_id,
                BrandMembership.user_id == user_id,
            )
        )
    if membership is None:
        membership = BrandMembership(
            brand_id=brand_id,
            user_id=user_id,
            invite_email=invite_email,
            invited_by_id=invited_by_id,
            role=role,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )
        db.add(membership)
    else:
        membership.user_id = user_id
        membership.invite_email = invite_email
        membership.invited_by_id = invited_by_id
        membership.role = role
        membership.status = MembershipStatus.ACTIVE
        membership.joined_at = membership.joined_at or datetime.now(UTC)

    db.commit()
    db.refresh(membership)
    return membership


def ensure_brand(
    db: Session,
    *,
    owner: User,
    name: str,
    slug: str,
    description: str,
    industry: str,
    tone_of_voice: str,
    target_audience: str,
    preferred_channels: list[str],
    guidelines_summary: str,
) -> Brand:
    brand = db.scalar(select(Brand).where(Brand.slug == slug))
    if brand is None:
        create_brand(
            db,
            payload=BrandCreate(
                name=name,
                slug=slug,
                description=description,
                industry=industry,
                tone_of_voice=tone_of_voice,
                target_audience=target_audience,
                preferred_channels=preferred_channels,
                guidelines_summary=guidelines_summary,
            ),
            user=owner,
        )
        brand = db.scalar(select(Brand).where(Brand.slug == slug))

    if brand is None:
        raise RuntimeError(f"Unable to create brand '{name}'.")
    return brand


def ensure_project(db: Session, *, owner: User, brand_id: int, name: str, description: str) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.brand_id == brand_id,
            Project.name == name,
        )
    )
    if project is None:
        create_project(
            db,
            payload=ProjectCreate(
                brand_id=brand_id,
                name=name,
                description=description,
            ),
            user=owner,
        )
        project = db.scalar(
            select(Project).where(
                Project.brand_id == brand_id,
                Project.name == name,
            )
        )

    if project is None:
        raise RuntimeError(f"Unable to create project '{name}'.")
    return project


def ensure_campaign(
    db: Session,
    *,
    owner: User,
    project_id: int,
    name: str,
    objective: str,
    audience: str,
    campaign_type: str,
    start_date: date,
    end_date: date,
    status: CampaignStatus,
) -> Campaign:
    campaign = db.scalar(
        select(Campaign).where(
            Campaign.project_id == project_id,
            Campaign.name == name,
        )
    )
    if campaign is None:
        create_campaign(
            db,
            payload=CampaignCreate(
                project_id=project_id,
                name=name,
                objective=objective,
                audience=audience,
                campaign_type=campaign_type,
                start_date=start_date,
                end_date=end_date,
                status=status,
            ),
            user=owner,
        )
        campaign = db.scalar(
            select(Campaign).where(
                Campaign.project_id == project_id,
                Campaign.name == name,
            )
        )

    if campaign is None:
        raise RuntimeError(f"Unable to create campaign '{name}'.")
    return campaign


def ensure_brief(
    db: Session,
    *,
    campaign_id: int,
    key_message: str,
    call_to_action: str,
    tone: str,
    channels: list[str],
    themes: list[str],
    references: str,
) -> None:
    brief = db.scalar(select(ContentBrief).where(ContentBrief.campaign_id == campaign_id))
    if brief is None:
        brief = ContentBrief(
            campaign_id=campaign_id,
            key_message=key_message,
            call_to_action=call_to_action,
            tone=tone,
            channels=channels,
            themes=themes,
            reference_materials=references,
        )
        db.add(brief)
    else:
        brief.key_message = key_message
        brief.call_to_action = call_to_action
        brief.tone = tone
        brief.channels = channels
        brief.themes = themes
        brief.reference_materials = references
    db.commit()


def ensure_template(
    db: Session,
    *,
    owner: User,
    brand_id: int,
    name: str,
    description: str,
    template_type: str,
    platform: str | None,
    content_type: str | None,
    body: str,
) -> ContentTemplate:
    template = db.scalar(
        select(ContentTemplate).where(
            ContentTemplate.brand_id == brand_id,
            ContentTemplate.name == name,
        )
    )
    if template is None:
        create_template(
            db,
            payload=ContentTemplateCreate(
                brand_id=brand_id,
                name=name,
                description=description,
                template_type=template_type,
                platform=platform,
                content_type=content_type,
                body=body,
            ),
            user=owner,
        )
        template = db.scalar(
            select(ContentTemplate).where(
                ContentTemplate.brand_id == brand_id,
                ContentTemplate.name == name,
            )
        )

    if template is None:
        raise RuntimeError(f"Unable to create template '{name}'.")
    return template


def ensure_draft_assignment(
    db: Session,
    *,
    actor: User,
    draft_id: int,
    assignee_user_id: int,
    assignment_type: AssignmentEntityType,
    note: str,
    due_at: datetime | None,
) -> None:
    existing = db.scalar(
        select(Assignment.id).where(
            Assignment.draft_id == draft_id,
            Assignment.assignee_user_id == assignee_user_id,
            Assignment.assignment_type == assignment_type,
        )
    )
    if existing is not None:
        return

    create_draft_assignment(
        db,
        draft_id=draft_id,
        payload=AssignmentCreate(
            assignment_type=assignment_type,
            assignee_user_id=assignee_user_id,
            note=note,
            due_at=due_at,
        ),
        user=actor,
    )


def ensure_campaign_assignment(
    db: Session,
    *,
    actor: User,
    campaign_id: int,
    assignee_user_id: int,
    note: str,
    due_at: datetime | None,
) -> None:
    existing = db.scalar(
        select(Assignment.id).where(
            Assignment.campaign_id == campaign_id,
            Assignment.assignee_user_id == assignee_user_id,
            Assignment.assignment_type == AssignmentEntityType.CAMPAIGN,
        )
    )
    if existing is not None:
        return

    create_campaign_assignment(
        db,
        campaign_id=campaign_id,
        payload=AssignmentCreate(
            assignee_user_id=assignee_user_id,
            note=note,
            due_at=due_at,
        ),
        user=actor,
    )


def seed_reviewed_draft(
    db: Session,
    *,
    owner: User,
    reviewer: User,
    campaign_id: int,
    title: str,
    platform: str,
    content_type: str,
    body: str,
    planned_publish_at: datetime,
    final_status: str,
    review_comment: str,
    rejection_comment: str | None = None,
) -> ContentDraft:
    draft = db.scalar(
        select(ContentDraft).where(
            ContentDraft.campaign_id == campaign_id,
            ContentDraft.title == title,
        )
    )
    if draft is None:
        created = create_draft(
            db,
            payload=ContentDraftCreate(
                campaign_id=campaign_id,
                title=title,
                platform=platform,
                content_type=content_type,
                content_body=body,
                planned_publish_at=planned_publish_at,
            ),
            user=owner,
        )
        draft_id = created.id
    else:
        draft_id = draft.id

    draft = db.get(ContentDraft, draft_id)
    if draft is None:
        raise RuntimeError(f"Unable to create draft '{title}'.")

    if draft.status == "idea":
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(
                content_body=body,
                planned_publish_at=planned_publish_at,
                status="draft",
            ),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "draft":
        submit_draft_for_review(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment="Ready for a review pass."),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "in_review" and rejection_comment:
        reject_draft(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment=rejection_comment),
            user=reviewer,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "rejected":
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(
                content_body=f"{body}\n\nUpdated after feedback: tightened hook, clearer CTA, stronger proof.",
            ),
            user=owner,
        )
        submit_draft_for_review(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment="Adjusted the hook and CTA."),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "in_review":
        add_review_comment(
            db,
            draft_id=draft_id,
            payload=DraftReviewCreate(comment=review_comment),
            user=reviewer,
        )
        approve_draft(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment="Good to ship."),
            user=reviewer,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "approved" and final_status in {"scheduled", "published"}:
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(
                status="scheduled",
                planned_publish_at=planned_publish_at,
            ),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "scheduled" and final_status == "published":
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(status="published"),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is None:
        raise RuntimeError(f"Unable to create draft '{title}'.")
    return draft


def seed_open_draft(
    db: Session,
    *,
    owner: User,
    campaign_id: int,
    title: str,
    platform: str,
    content_type: str,
    body: str,
    planned_publish_at: datetime | None,
    status: str,
) -> ContentDraft:
    draft = db.scalar(
        select(ContentDraft).where(
            ContentDraft.campaign_id == campaign_id,
            ContentDraft.title == title,
        )
    )
    if draft is None:
        draft = db.get(
            ContentDraft,
            create_draft(
                db,
                payload=ContentDraftCreate(
                    campaign_id=campaign_id,
                    title=title,
                    platform=platform,
                    content_type=content_type,
                    content_body=body,
                    status=status,
                    planned_publish_at=planned_publish_at,
                ),
                user=owner,
            ).id,
        )

    if draft is not None and status != draft.status:
        update_draft(
            db,
            draft_id=draft.id,
            payload=ContentDraftUpdate(
                content_body=body,
                planned_publish_at=planned_publish_at,
                status=status,
            ),
            user=owner,
        )
        draft = db.get(ContentDraft, draft.id)

    if draft is None:
        raise RuntimeError(f"Unable to create draft '{title}'.")
    return draft


def maybe_upgrade_brand_plan(db: Session, *, owner: User, brand_id: int, plan_code: str, interval: PlanInterval) -> None:
    snapshot = get_brand_billing_snapshot(db, brand_id=brand_id, user=owner)
    if snapshot.current_plan.code == plan_code and snapshot.subscription.billing_interval == interval:
        return

    update_brand_subscription(
        db,
        brand_id=brand_id,
        payload=BrandSubscriptionUpdate(plan_code=plan_code, billing_interval=interval),
        user=owner,
    )


def seed_workspace(
    db: Session,
    *,
    email: str,
    password: str,
    reset_all: bool = False,
) -> None:
    normalized_email = email.strip().lower()
    if reset_all:
        reset_application_data(db, preserve_user_email=normalized_email)

    owner = ensure_user(
        db,
        email=normalized_email,
        full_name=OWNER_PROFILE["full_name"] if normalized_email == OWNER_PROFILE["email"] else "Workspace Owner",
        password=password,
    )

    repair_legacy_draft_statuses(db)

    maya = ensure_user(
        db,
        email=DEMO_USERS[0]["email"],
        full_name=DEMO_USERS[0]["full_name"],
        password="demo-pass-1234",
        legacy_emails=DEMO_USERS[0]["legacy_emails"],
    )
    jordan = ensure_user(
        db,
        email=DEMO_USERS[1]["email"],
        full_name=DEMO_USERS[1]["full_name"],
        password="demo-pass-1234",
        legacy_emails=DEMO_USERS[1]["legacy_emails"],
    )
    leo = ensure_user(
        db,
        email=DEMO_USERS[2]["email"],
        full_name=DEMO_USERS[2]["full_name"],
        password="demo-pass-1234",
        legacy_emails=DEMO_USERS[2]["legacy_emails"],
    )
    sofia = ensure_user(
        db,
        email=DEMO_USERS[3]["email"],
        full_name=DEMO_USERS[3]["full_name"],
        password="demo-pass-1234",
        legacy_emails=DEMO_USERS[3]["legacy_emails"],
    )

    team = {
        "owner": owner,
        "maya": maya,
        "jordan": jordan,
        "leo": leo,
        "sofia": sofia,
    }

    anchor = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    brand_specs = [
        {
            "key": "asteron",
            "name": "Asteron Media",
            "slug": "asteron-media-demo",
            "description": "Operator-led growth content brand packaging product launches, lifecycle messaging, and creator funnels.",
            "industry": "Creator software",
            "tone_of_voice": "Direct, strategic, founder-led, and concrete. Sound sharp without sounding inflated.",
            "target_audience": "Solo operators, small content teams, and creator founders shipping revenue-focused launches.",
            "preferred_channels": ["LinkedIn", "Email", "Instagram", "Web"],
            "guidelines_summary": "Lead with operating clarity, proof before hype, and a single CTA per asset.",
            "plan_code": "growth",
            "plan_interval": PlanInterval.YEARLY,
            "created_offset": -88,
            "updated_offset": -1,
            "members": {
                "maya": BrandRole.ADMIN,
                "jordan": BrandRole.REVIEWER,
                "leo": BrandRole.EDITOR,
                "sofia": BrandRole.EDITOR,
            },
            "templates": [
                {
                    "name": "Launch narrative post",
                    "description": "Founder-led LinkedIn launch post with result, proof, and CTA structure.",
                    "template_type": "social",
                    "platform": "LinkedIn",
                    "content_type": "organic post",
                    "body": "Open with the market tension, add proof from users, then invite one next step.",
                    "created_offset": -60,
                },
                {
                    "name": "Conversion cleanup email",
                    "description": "Email template for objection handling before a pricing or launch push.",
                    "template_type": "email",
                    "platform": "Email",
                    "content_type": "newsletter",
                    "body": "State the objection, show one proof block, remove friction, then close with the ask.",
                    "created_offset": -42,
                },
                {
                    "name": "Webinar follow-up sequence",
                    "description": "Follow-up framework for post-event conversion sequences.",
                    "template_type": "email",
                    "platform": "Email",
                    "content_type": "sequence",
                    "body": "Recap the moment, isolate the missed value, then drive the replay or offer bridge.",
                    "created_offset": -20,
                },
                {
                    "name": "Quote card carousel",
                    "description": "Short-form carousel pattern for stitching proof snippets into one sales angle.",
                    "template_type": "social",
                    "platform": "Instagram",
                    "content_type": "carousel",
                    "body": "Cover slide, three proof slides, one objection slide, one CTA slide.",
                    "created_offset": -8,
                },
            ],
            "projects": [
                {
                    "key": "asteron_creator_os",
                    "name": "Creator OS Launch",
                    "description": "Launch system for the spring Creator OS release, including waitlist, launch proof, and objection handling.",
                    "created_offset": -34,
                    "updated_offset": -1,
                    "campaigns": [
                        {
                            "key": "asteron_waitlist_sprint",
                            "name": "Creator OS Waitlist Sprint",
                            "objective": "Convert founder audience attention into waitlist signups before the release webinar.",
                            "audience": "Small creator businesses and operators evaluating whether to replace ad hoc launch docs.",
                            "campaign_type": "product_launch",
                            "start_offset": -16,
                            "end_offset": 14,
                            "status": CampaignStatus.ACTIVE,
                            "created_offset": -24,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "Creator OS removes launch chaos by turning scattered process into one repeatable system.",
                                "call_to_action": "Join the waitlist.",
                                "tone": "Operator-sharp, confident, specific.",
                                "channels": ["LinkedIn", "Email", "Instagram"],
                                "themes": ["launch systems", "operator clarity", "proof over hype"],
                                "references": "Founder call notes, onboarding interview clips, and pricing FAQ drafts.",
                            },
                            "assets": [
                                {
                                    "name": "Launch proof board",
                                    "asset_type": "moodboard",
                                    "file_url": "https://example.com/assets/asteron/launch-proof-board.pdf",
                                    "notes": "Proof-led narrative direction for launch week visuals.",
                                    "created_offset": -14,
                                },
                                {
                                    "name": "Founder headshots select",
                                    "asset_type": "image_set",
                                    "file_url": "https://example.com/assets/asteron/founder-headshots.zip",
                                    "notes": "Approved portrait selects for landing and organic social.",
                                    "created_offset": -10,
                                },
                                {
                                    "name": "Waitlist webinar cover",
                                    "asset_type": "hero_image",
                                    "file_url": "https://example.com/assets/asteron/waitlist-webinar-cover.png",
                                    "notes": "Main event visual used across landing and email.",
                                    "created_offset": -6,
                                },
                            ],
                            "manual_calendar_items": [
                                {
                                    "title": "Founder webinar dry run",
                                    "platform": "Zoom",
                                    "item_type": "live_event",
                                    "scheduled_offset": 5,
                                    "status": "planned",
                                    "notes": "Final dry run with slides, Q&A order, and CTA transitions.",
                                },
                            ],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                                CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                            },
                            "dependencies": [
                                {
                                    "dependent_type": CampaignDependencyNodeType.CAMPAIGN_MILESTONE,
                                    "dependent_milestone_key": CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY.value,
                                    "blocker_type": CampaignDependencyNodeType.DRAFT_STAGE,
                                    "blocker_draft_key": "asteron_beta_faq_thread",
                                    "blocker_stage_key": DraftStatus.APPROVED.value,
                                    "note": "Launch-ready stays blocked until the beta FAQ thread reaches approved.",
                                    "created_offset": -3,
                                },
                            ],
                            "drafts": [
                                {
                                    "key": "asteron_launch_narrative",
                                    "title": "Creator OS launch narrative",
                                    "platform": "LinkedIn",
                                    "content_type": "organic post",
                                    "body": "Most launches fail before they miss a revenue target. They fail when the team cannot answer what ships when. Creator OS gives founders one operating system for launch week instead of ten scattered docs.",
                                    "status": DraftStatus.SCHEDULED.value,
                                    "planned_offset": 3,
                                    "reviewer": "jordan",
                                    "review_comment": "Lead stronger with the operating problem, then move into proof.",
                                    "rejection_comment": "Version one sounded generic. Make the workflow pain more concrete.",
                                    "created_offset": -15,
                                    "updated_offset": -2,
                                },
                                {
                                    "key": "asteron_founder_teaser_reel",
                                    "title": "Founder teaser reel",
                                    "platform": "Instagram",
                                    "content_type": "reel",
                                    "body": "Three-shot founder teaser: chaos board, clean launch dashboard, one sentence on how launch week feels after the switch.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -2,
                                    "reviewer": "jordan",
                                    "review_comment": "Good motion rhythm. Keep the product moment in the last frame.",
                                    "created_offset": -12,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "asteron_pricing_objection_carousel",
                                    "title": "Pricing objection carousel",
                                    "platform": "Instagram",
                                    "content_type": "carousel",
                                    "body": "Address the main objection in the first slide, then show how one missed launch week costs more than the system.",
                                    "status": DraftStatus.APPROVED.value,
                                    "planned_offset": 6,
                                    "reviewer": "jordan",
                                    "review_comment": "Slides are clean. Tighten the fourth slide to avoid repeating the first proof point.",
                                    "created_offset": -8,
                                    "updated_offset": -3,
                                },
                                {
                                    "key": "asteron_beta_faq_thread",
                                    "title": "Beta FAQ thread",
                                    "platform": "Twitter/X",
                                    "content_type": "thread",
                                    "body": "A short thread answering onboarding, switching, and content migration questions from beta calls.",
                                    "status": DraftStatus.IN_REVIEW.value,
                                    "planned_offset": 5,
                                    "review_comment": "This is close. Clarify the migration answer and remove one redundant FAQ.",
                                    "created_offset": -6,
                                    "updated_offset": -1,
                                },
                            ],
                        },
                        {
                            "key": "asteron_conversion_cleanup",
                            "name": "March Conversion Cleanup",
                            "objective": "Improve conversion from webinar, landing page, and proof-led nurture assets before cart close.",
                            "audience": "Warm leads who engaged with launch content but have not converted yet.",
                            "campaign_type": "conversion_push",
                            "start_offset": -9,
                            "end_offset": 12,
                            "status": CampaignStatus.ACTIVE,
                            "created_offset": -14,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "The right objection-handling content should remove hesitation, not pile on urgency.",
                                "call_to_action": "Review the replay and start the setup.",
                                "tone": "Calm, direct, buyer-aware.",
                                "channels": ["Email", "Web", "Instagram"],
                                "themes": ["objection handling", "decision clarity", "proof blocks"],
                                "references": "Webinar questions, Hotjar notes, and pricing-page scroll recordings.",
                            },
                            "assets": [],
                            "manual_calendar_items": [
                                {
                                    "title": "CRO copy review",
                                    "platform": "Meet",
                                    "item_type": "review_session",
                                    "scheduled_offset": 1,
                                    "status": "scheduled",
                                    "notes": "Review proof block order, CTA hierarchy, and urgency framing.",
                                },
                            ],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                            },
                            "dependencies": [
                                {
                                    "dependent_type": CampaignDependencyNodeType.CAMPAIGN_MILESTONE,
                                    "dependent_milestone_key": CampaignMilestoneKey.ALL_REVIEWS_COMPLETE.value,
                                    "blocker_type": CampaignDependencyNodeType.DRAFT_STAGE,
                                    "blocker_draft_key": "asteron_landing_page_proof_blocks",
                                    "blocker_stage_key": DraftStatus.APPROVED.value,
                                    "note": "All reviews stay open until the landing-page proof draft clears approval.",
                                    "created_offset": -2,
                                },
                            ],
                            "drafts": [
                                {
                                    "key": "asteron_webinar_followup_email",
                                    "title": "Webinar follow-up email",
                                    "platform": "Email",
                                    "content_type": "newsletter",
                                    "body": "Thank people for the time, show the highest-leverage lesson, then route them back to the replay and setup flow.",
                                    "status": DraftStatus.SCHEDULED.value,
                                    "planned_offset": 1,
                                    "reviewer": "jordan",
                                    "review_comment": "Move the replay link higher and make the CTA cleaner.",
                                    "rejection_comment": "The first pass buried the replay link under too much summary.",
                                    "created_offset": -7,
                                    "updated_offset": -2,
                                },
                                {
                                    "key": "asteron_landing_page_proof_blocks",
                                    "title": "Landing page proof blocks",
                                    "platform": "Web",
                                    "content_type": "page section",
                                    "body": "Rewrite three landing sections using sharper before-and-after proof from onboarding interviews.",
                                    "status": DraftStatus.IN_REVIEW.value,
                                    "planned_offset": -1,
                                    "review_comment": "The proof is stronger now, but section two still reads too abstract.",
                                    "created_offset": -5,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "asteron_quote_cards",
                                    "title": "Customer proof quote cards",
                                    "platform": "Instagram",
                                    "content_type": "carousel",
                                    "body": "Turn three customer lines into short quote cards with one operational payoff on each slide.",
                                    "status": DraftStatus.DRAFT.value,
                                    "planned_offset": 4,
                                    "created_offset": -4,
                                    "updated_offset": -2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "key": "asteron_community_engine",
                    "name": "Community Engine",
                    "description": "Lifecycle and community content system for newsletter retention, referrals, and proof loops.",
                    "created_offset": -72,
                    "updated_offset": -2,
                    "campaigns": [
                        {
                            "key": "asteron_newsletter_revival",
                            "name": "Operator Newsletter Revival",
                            "objective": "Restart the weekly newsletter with stronger retention and referral momentum.",
                            "audience": "Existing subscribers who previously opened launch content but drifted from the weekly newsletter.",
                            "campaign_type": "retention",
                            "start_offset": -68,
                            "end_offset": -28,
                            "status": CampaignStatus.COMPLETED,
                            "created_offset": -74,
                            "updated_offset": -28,
                            "brief": {
                                "key_message": "The newsletter should feel like an operating memo, not a diluted blog post.",
                                "call_to_action": "Reply with the next operating problem to break down.",
                                "tone": "Editorial, useful, specific.",
                                "channels": ["Email", "LinkedIn"],
                                "themes": ["operator notes", "systems", "weekly cadence"],
                                "references": "Best-performing editions, reply inbox themes, and churn survey notes.",
                            },
                            "assets": [
                                {
                                    "name": "Newsletter cover pack",
                                    "asset_type": "design_pack",
                                    "file_url": "https://example.com/assets/asteron/newsletter-cover-pack.zip",
                                    "notes": "Illustration and chart system for recurring operator notes.",
                                    "created_offset": -63,
                                },
                                {
                                    "name": "Referral examples board",
                                    "asset_type": "moodboard",
                                    "file_url": "https://example.com/assets/asteron/referral-examples.pdf",
                                    "notes": "Reference examples for referral CTA placement.",
                                    "created_offset": -50,
                                },
                            ],
                            "manual_calendar_items": [
                                {
                                    "title": "Newsletter retro",
                                    "platform": "Notion",
                                    "item_type": "retrospective",
                                    "scheduled_offset": -26,
                                    "status": "completed",
                                    "notes": "Post-campaign retro covering open-rate recovery and referral lift.",
                                },
                            ],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                                CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                                CampaignMilestoneKey.ALL_REVIEWS_COMPLETE.value,
                                CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY.value,
                                CampaignMilestoneKey.CAMPAIGN_COMPLETED.value,
                            },
                            "dependencies": [],
                            "drafts": [
                                {
                                    "key": "asteron_issue_01",
                                    "title": "Issue 01 systems note",
                                    "platform": "Email",
                                    "content_type": "newsletter",
                                    "body": "The first issue explains the one mistake that creates launch chaos and how operators can remove it.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -60,
                                    "reviewer": "jordan",
                                    "review_comment": "Good pacing. Shorten the second paragraph.",
                                    "created_offset": -66,
                                    "updated_offset": -61,
                                },
                                {
                                    "key": "asteron_referral_email",
                                    "title": "Referral landing email",
                                    "platform": "Email",
                                    "content_type": "newsletter",
                                    "body": "A short referral ask anchored to one useful framework instead of generic sharing language.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -45,
                                    "reviewer": "jordan",
                                    "review_comment": "Keep the referral ask closer to the proof snippet.",
                                    "created_offset": -51,
                                    "updated_offset": -46,
                                },
                                {
                                    "key": "asteron_subscriber_wins_clip",
                                    "title": "Subscriber wins clip",
                                    "platform": "LinkedIn",
                                    "content_type": "video",
                                    "body": "One-minute highlight of subscriber results framed as what changed in the operating system.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -32,
                                    "reviewer": "jordan",
                                    "review_comment": "Keep the clip under a minute and use captions for the proof lines.",
                                    "created_offset": -38,
                                    "updated_offset": -33,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "key": "harbor",
            "name": "Harbor & Hill",
            "slug": "harbor-hill-demo",
            "description": "Premium home brand blending editorial storytelling, product styling, and retailer launch moments.",
            "industry": "Home lifestyle",
            "tone_of_voice": "Warm, tactile, editorial, and image-led without drifting into vague luxury language.",
            "target_audience": "Style-conscious households refreshing spaces for hosting, rituals, and seasonal updates.",
            "preferred_channels": ["Instagram", "Pinterest", "Email", "Blog"],
            "guidelines_summary": "Stay elegant and concrete, show the room before the product, and keep every CTA easy to act on.",
            "plan_code": "starter",
            "plan_interval": PlanInterval.MONTHLY,
            "created_offset": -92,
            "updated_offset": -1,
            "members": {
                "maya": BrandRole.ADMIN,
                "jordan": BrandRole.REVIEWER,
                "sofia": BrandRole.EDITOR,
            },
            "templates": [
                {
                    "name": "Collection story frame",
                    "description": "Editorial angle for anchoring a collection around one hosting mood.",
                    "template_type": "editorial",
                    "platform": "Blog",
                    "content_type": "feature article",
                    "body": "Open on atmosphere, anchor with two product moments, then show the room-level payoff.",
                    "created_offset": -78,
                },
                {
                    "name": "Styled reel shot list",
                    "description": "Short-form shot sequence for room styling reels.",
                    "template_type": "video",
                    "platform": "Instagram",
                    "content_type": "reel",
                    "body": "Start wide, move through tactile closeups, then reveal the final hosted scene.",
                    "created_offset": -50,
                },
                {
                    "name": "Retail partner launch email",
                    "description": "Launch email built for store events and showroom traffic.",
                    "template_type": "email",
                    "platform": "Email",
                    "content_type": "launch email",
                    "body": "Event framing, hero products, in-person date, simple RSVP bridge.",
                    "created_offset": -12,
                },
            ],
            "projects": [
                {
                    "key": "harbor_seasonal",
                    "name": "Seasonal Collections",
                    "description": "Seasonal product storytelling across reels, email, retail, and editorial assets.",
                    "created_offset": -86,
                    "updated_offset": -1,
                    "campaigns": [
                        {
                            "key": "harbor_winter_closeout",
                            "name": "Winter Closeout Stories",
                            "objective": "Move final winter inventory without flattening the brand into discount-only messaging.",
                            "audience": "Existing customers and high-intent browsers considering end-of-season purchases.",
                            "campaign_type": "seasonal_closeout",
                            "start_offset": -84,
                            "end_offset": -56,
                            "status": CampaignStatus.COMPLETED,
                            "created_offset": -88,
                            "updated_offset": -56,
                            "brief": {
                                "key_message": "The closeout should still feel considered, styled, and editorial.",
                                "call_to_action": "Shop the final winter edit.",
                                "tone": "Warm, elevated, lightly urgent.",
                                "channels": ["Email", "Pinterest", "Blog"],
                                "themes": ["last look", "styled spaces", "seasonal transition"],
                                "references": "Lookbook archive, merchant notes, and top winter PDP imagery.",
                            },
                            "assets": [
                                {
                                    "name": "Winter lookbook selects",
                                    "asset_type": "image_set",
                                    "file_url": "https://example.com/assets/harbor/winter-lookbook-selects.zip",
                                    "notes": "Final selects used for closeout blog and email blocks.",
                                    "created_offset": -79,
                                },
                            ],
                            "manual_calendar_items": [],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                                CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                                CampaignMilestoneKey.ALL_REVIEWS_COMPLETE.value,
                                CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY.value,
                                CampaignMilestoneKey.CAMPAIGN_COMPLETED.value,
                            },
                            "dependencies": [],
                            "drafts": [
                                {
                                    "key": "harbor_last_call_email",
                                    "title": "Last-call collection email",
                                    "platform": "Email",
                                    "content_type": "newsletter",
                                    "body": "One soft-last-call email that keeps the products styled rather than sounding like clearance copy.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -72,
                                    "reviewer": "jordan",
                                    "review_comment": "Elegant tone. Bring the top product forward in the first block.",
                                    "created_offset": -80,
                                    "updated_offset": -73,
                                },
                                {
                                    "key": "harbor_closeout_pin_series",
                                    "title": "Closeout pin series",
                                    "platform": "Pinterest",
                                    "content_type": "pin set",
                                    "body": "A small batch of product pins anchored in room scenes rather than cropped product shots.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -65,
                                    "reviewer": "jordan",
                                    "review_comment": "Good selection. Keep copy lines even shorter for the pin overlays.",
                                    "created_offset": -70,
                                    "updated_offset": -66,
                                },
                                {
                                    "key": "harbor_ugc_roundup_feature",
                                    "title": "UGC roundup feature",
                                    "platform": "Blog",
                                    "content_type": "feature article",
                                    "body": "A feature collecting customer room photos with quick notes on why each setup works.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -58,
                                    "reviewer": "jordan",
                                    "review_comment": "Good curation. Trim the intro so the visuals arrive faster.",
                                    "created_offset": -61,
                                    "updated_offset": -58,
                                },
                            ],
                        },
                        {
                            "key": "harbor_spring_hosting",
                            "name": "Spring Hosting Week",
                            "objective": "Drive awareness and saves for the spring hosting collection through room-led storytelling.",
                            "audience": "Home-focused shoppers planning spring tables, gatherings, and small hosting upgrades.",
                            "campaign_type": "seasonal_launch",
                            "start_offset": -8,
                            "end_offset": 20,
                            "status": CampaignStatus.ACTIVE,
                            "created_offset": -15,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "Make hosting feel aspirational but achievable with a few specific room choices.",
                                "call_to_action": "Shop the spring hosting edit.",
                                "tone": "Elegant, image-first, and concrete.",
                                "channels": ["Instagram", "Blog", "Email"],
                                "themes": ["hosting", "spring reset", "table styling"],
                                "references": "Spring lookbook, retail floor walkthrough, and creator UGC shortlist.",
                            },
                            "assets": [
                                {
                                    "name": "Patio hero selects",
                                    "asset_type": "image_set",
                                    "file_url": "https://example.com/assets/harbor/patio-hero-selects.zip",
                                    "notes": "Primary stills for spring hosting week launch.",
                                    "created_offset": -12,
                                },
                                {
                                    "name": "Outdoor table motion clips",
                                    "asset_type": "video_clips",
                                    "file_url": "https://example.com/assets/harbor/outdoor-table-clips.zip",
                                    "notes": "Clips used for reel edit and landing background loops.",
                                    "created_offset": -7,
                                },
                            ],
                            "manual_calendar_items": [
                                {
                                    "title": "Spring collection shoot",
                                    "platform": "Studio",
                                    "item_type": "production",
                                    "scheduled_offset": -10,
                                    "status": "completed",
                                    "notes": "Finished capture day for patio and table scenes.",
                                },
                            ],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                                CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                            },
                            "dependencies": [],
                            "drafts": [
                                {
                                    "key": "harbor_patio_hosting_reel",
                                    "title": "Patio hosting reel",
                                    "platform": "Instagram",
                                    "content_type": "reel",
                                    "body": "Three quick styling beats that move from bare table to hosted spring setting.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -4,
                                    "reviewer": "jordan",
                                    "review_comment": "Motion beats land well. Keep the final product callout on screen a touch longer.",
                                    "created_offset": -14,
                                    "updated_offset": -4,
                                },
                                {
                                    "key": "harbor_styling_checklist",
                                    "title": "Table styling checklist",
                                    "platform": "Blog",
                                    "content_type": "article",
                                    "body": "A short checklist for pulling together a spring table without over-styling it.",
                                    "status": DraftStatus.SCHEDULED.value,
                                    "planned_offset": 2,
                                    "reviewer": "jordan",
                                    "review_comment": "The checklist is strong. Tighten the opener and keep the CTA lighter.",
                                    "created_offset": -6,
                                    "updated_offset": -2,
                                },
                                {
                                    "key": "harbor_storyboard",
                                    "title": "Showroom visit storyboard",
                                    "platform": "Instagram",
                                    "content_type": "story board",
                                    "body": "Loose storyboard for a story sequence walking through spring textures, room details, and two hero pieces.",
                                    "status": DraftStatus.IDEA.value,
                                    "created_offset": -3,
                                    "updated_offset": -2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "key": "harbor_retail",
                    "name": "Retail Partners",
                    "description": "Showroom and retail-facing campaign work for in-person launches and partner enablement.",
                    "created_offset": -20,
                    "updated_offset": -1,
                    "campaigns": [
                        {
                            "key": "harbor_showroom_revival",
                            "name": "Showroom Revival",
                            "objective": "Support the showroom refresh with partner communications and a lightweight launch system.",
                            "audience": "Retail partners, design trade contacts, and showroom visitors.",
                            "campaign_type": "retail_launch",
                            "start_offset": 7,
                            "end_offset": 32,
                            "status": CampaignStatus.PLANNING,
                            "created_offset": -6,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "The showroom refresh should feel like a curated experience, not a stock rotation.",
                                "call_to_action": "Book the showroom visit.",
                                "tone": "Editorial, polished, quietly confident.",
                                "channels": ["Email", "Instagram"],
                                "themes": ["showroom launch", "trade audience", "editorial merchandising"],
                                "references": "Floor plan draft, partner invite notes, and merchant display sketches.",
                            },
                            "assets": [],
                            "manual_calendar_items": [
                                {
                                    "title": "Retailer alignment call",
                                    "platform": "Meet",
                                    "item_type": "planning_session",
                                    "scheduled_offset": 8,
                                    "status": "planned",
                                    "notes": "Confirm floor-story order, guest list, and retail talking points.",
                                },
                            ],
                            "completed_milestones": set(),
                            "dependencies": [
                                {
                                    "dependent_type": CampaignDependencyNodeType.CAMPAIGN_MILESTONE,
                                    "dependent_milestone_key": CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                                    "blocker_type": CampaignDependencyNodeType.DRAFT_STAGE,
                                    "blocker_draft_key": "harbor_launch_invite_email",
                                    "blocker_stage_key": DraftStatus.IN_REVIEW.value,
                                    "note": "First-drafts-ready should wait until the invite email reaches review.",
                                    "created_offset": -1,
                                },
                            ],
                            "drafts": [
                                {
                                    "key": "harbor_launch_invite_email",
                                    "title": "Launch invite email",
                                    "platform": "Email",
                                    "content_type": "launch email",
                                    "body": "A showroom invitation that feels curated and event-led, with a simple RSVP path.",
                                    "status": DraftStatus.DRAFT.value,
                                    "planned_offset": 10,
                                    "created_offset": -2,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "harbor_partner_moodboard",
                                    "title": "Partner moodboard carousel",
                                    "platform": "Instagram",
                                    "content_type": "carousel",
                                    "body": "Concept carousel showing the visual direction for the showroom revival.",
                                    "status": DraftStatus.IDEA.value,
                                    "created_offset": -1,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "harbor_staff_talking_points",
                                    "title": "Retail staff talking points",
                                    "platform": "Internal",
                                    "content_type": "enablement brief",
                                    "body": "Short trade-facing talking points on what changed in the collection and how to guide showroom conversations.",
                                    "status": DraftStatus.APPROVED.value,
                                    "planned_offset": 9,
                                    "reviewer": "jordan",
                                    "review_comment": "This is clear. Keep one simpler opener for new floor staff.",
                                    "created_offset": -4,
                                    "updated_offset": -2,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "key": "northstar",
            "name": "Northstar Labs",
            "slug": "northstar-labs-demo",
            "description": "Performance-minded wellness brand balancing founder voice, launch proof, and retention systems.",
            "industry": "Wellness tech",
            "tone_of_voice": "Crisp, practical, proof-led, and calm. Avoid trend language and empty optimization clichés.",
            "target_audience": "High-output professionals building routines around energy, focus, and recovery.",
            "preferred_channels": ["LinkedIn", "Instagram", "Email", "Podcast"],
            "guidelines_summary": "Lead with realistic routine fit, grounded proof, and one habit-level next step.",
            "plan_code": "scale",
            "plan_interval": PlanInterval.MONTHLY,
            "created_offset": -90,
            "updated_offset": -1,
            "members": {
                "maya": BrandRole.ADMIN,
                "jordan": BrandRole.REVIEWER,
                "leo": BrandRole.EDITOR,
                "sofia": BrandRole.VIEWER,
            },
            "templates": [
                {
                    "name": "Launch proof post",
                    "description": "Proof-heavy post format for product launches and founder updates.",
                    "template_type": "social",
                    "platform": "LinkedIn",
                    "content_type": "organic post",
                    "body": "Result-first hook, two proof lines, one next-step CTA.",
                    "created_offset": -70,
                },
                {
                    "name": "Retention restart email",
                    "description": "Email structure for win-back and routine-reset messaging.",
                    "template_type": "email",
                    "platform": "Email",
                    "content_type": "newsletter",
                    "body": "Acknowledge the lapse, simplify the restart, then show one proof-backed reason to return.",
                    "created_offset": -35,
                },
                {
                    "name": "UGC comparison carousel",
                    "description": "Carousel pattern comparing before-and-after routine behaviors.",
                    "template_type": "social",
                    "platform": "Instagram",
                    "content_type": "carousel",
                    "body": "Start with the tension, show a realistic swap, then close with the simplest new habit.",
                    "created_offset": -10,
                },
            ],
            "projects": [
                {
                    "key": "northstar_performance",
                    "name": "Performance Stack",
                    "description": "Founder voice and product-launch content spanning launch proof, education, and creator distribution.",
                    "created_offset": -78,
                    "updated_offset": -1,
                    "campaigns": [
                        {
                            "key": "northstar_q1_focus_launch",
                            "name": "Q1 Focus Ritual Launch",
                            "objective": "Drive early demand for the focus ritual through proof-led founder content and short-form creator clips.",
                            "audience": "Busy professionals replacing crash-prone caffeine habits with steadier routines.",
                            "campaign_type": "product_launch",
                            "start_offset": -74,
                            "end_offset": -46,
                            "status": CampaignStatus.COMPLETED,
                            "created_offset": -78,
                            "updated_offset": -46,
                            "brief": {
                                "key_message": "Focus should feel cleaner and more repeatable, not more intense.",
                                "call_to_action": "Try the ritual.",
                                "tone": "Confident, specific, grounded in proof.",
                                "channels": ["Email", "Instagram", "LinkedIn"],
                                "themes": ["steady focus", "habit loop", "launch proof"],
                                "references": "Founder notes, beta feedback, and routine interview snippets.",
                            },
                            "assets": [
                                {
                                    "name": "Cold brew launch photo set",
                                    "asset_type": "image_set",
                                    "file_url": "https://example.com/assets/northstar/cold-brew-launch-photos.zip",
                                    "notes": "Hero stills for launch email and organic posts.",
                                    "created_offset": -72,
                                },
                                {
                                    "name": "Creator teaser selects",
                                    "asset_type": "video_clips",
                                    "file_url": "https://example.com/assets/northstar/creator-teaser-clips.zip",
                                    "notes": "Approved creator clips for product launch week.",
                                    "created_offset": -66,
                                },
                            ],
                            "manual_calendar_items": [],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                                CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                                CampaignMilestoneKey.ALL_REVIEWS_COMPLETE.value,
                                CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY.value,
                                CampaignMilestoneKey.CAMPAIGN_COMPLETED.value,
                            },
                            "dependencies": [],
                            "drafts": [
                                {
                                    "key": "northstar_launch_email",
                                    "title": "Launch proof email",
                                    "platform": "Email",
                                    "content_type": "newsletter",
                                    "body": "A proof-first launch email explaining what changed in tester routines after one week.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -68,
                                    "reviewer": "jordan",
                                    "review_comment": "Good proof density. The opening line can be even cleaner.",
                                    "created_offset": -73,
                                    "updated_offset": -68,
                                },
                                {
                                    "key": "northstar_creator_teaser",
                                    "title": "Creator teaser reel",
                                    "platform": "Instagram",
                                    "content_type": "reel",
                                    "body": "Short creator-led teaser showing the product in a real desk routine.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -62,
                                    "reviewer": "jordan",
                                    "review_comment": "The pace works. Keep the final benefit sentence on screen slightly longer.",
                                    "created_offset": -67,
                                    "updated_offset": -62,
                                },
                                {
                                    "key": "northstar_customer_thread",
                                    "title": "Customer proof thread",
                                    "platform": "LinkedIn",
                                    "content_type": "thread",
                                    "body": "A short thread on what customers changed in their midday routine and why the ritual stuck.",
                                    "status": DraftStatus.PUBLISHED.value,
                                    "planned_offset": -54,
                                    "reviewer": "jordan",
                                    "review_comment": "The examples are good. One less proof block will make the thread faster to read.",
                                    "created_offset": -58,
                                    "updated_offset": -54,
                                },
                            ],
                        },
                        {
                            "key": "northstar_cold_brew_launch",
                            "name": "Cold Brew Focus Launch",
                            "objective": "Drive trial signups for the cold brew line with proof-led founder and creator content.",
                            "audience": "Professionals who want smoother energy and clearer focus without a hard crash.",
                            "campaign_type": "product_launch",
                            "start_offset": -12,
                            "end_offset": 18,
                            "status": CampaignStatus.ACTIVE,
                            "created_offset": -18,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "Clear energy should fit a normal day rather than demand a perfect routine.",
                                "call_to_action": "Join the early access list.",
                                "tone": "Clear, credible, lightly founder-led.",
                                "channels": ["LinkedIn", "Instagram", "Email"],
                                "themes": ["clear energy", "habit fit", "proof"],
                                "references": "Launch deck, beta feedback, and creator talking points.",
                            },
                            "assets": [
                                {
                                    "name": "Launch creator stills",
                                    "asset_type": "image_set",
                                    "file_url": "https://example.com/assets/northstar/launch-creator-stills.zip",
                                    "notes": "Approved creator stills for LinkedIn and Instagram launch assets.",
                                    "created_offset": -10,
                                },
                                {
                                    "name": "UGC comparison board",
                                    "asset_type": "moodboard",
                                    "file_url": "https://example.com/assets/northstar/ugc-comparison-board.pdf",
                                    "notes": "Before-and-after routine references for carousel drafting.",
                                    "created_offset": -8,
                                },
                                {
                                    "name": "Launch CTA lockups",
                                    "asset_type": "design_pack",
                                    "file_url": "https://example.com/assets/northstar/launch-cta-lockups.zip",
                                    "notes": "CTA variations for founder and creator surfaces.",
                                    "created_offset": -4,
                                },
                            ],
                            "manual_calendar_items": [
                                {
                                    "title": "Creator approval check-in",
                                    "platform": "Slack huddle",
                                    "item_type": "review_session",
                                    "scheduled_offset": -1,
                                    "status": "completed",
                                    "notes": "Locked creator edits and final launch CTA order.",
                                },
                            ],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                                CampaignMilestoneKey.FIRST_DRAFTS_READY.value,
                            },
                            "dependencies": [],
                            "drafts": [
                                {
                                    "key": "northstar_launch_proof_post",
                                    "title": "Launch proof post",
                                    "platform": "LinkedIn",
                                    "content_type": "organic post",
                                    "body": "Three beta testers replaced their afternoon slump with a routine they could actually keep. That is the whole point of this launch.",
                                    "status": DraftStatus.SCHEDULED.value,
                                    "planned_offset": 4,
                                    "reviewer": "jordan",
                                    "review_comment": "Strong proof flow. Keep the second sentence a touch tighter.",
                                    "created_offset": -11,
                                    "updated_offset": -3,
                                },
                                {
                                    "key": "northstar_ugc_comparison",
                                    "title": "UGC comparison carousel",
                                    "platform": "Instagram",
                                    "content_type": "carousel",
                                    "body": "A comparison carousel showing the difference between a spike-and-crash energy routine and a steadier ritual.",
                                    "status": DraftStatus.APPROVED.value,
                                    "planned_offset": 8,
                                    "reviewer": "jordan",
                                    "review_comment": "The structure works. Add a stronger proof beat on slide four.",
                                    "created_offset": -7,
                                    "updated_offset": -3,
                                },
                                {
                                    "key": "northstar_founder_pov",
                                    "title": "Founder POV on clean focus",
                                    "platform": "LinkedIn",
                                    "content_type": "thought leadership post",
                                    "body": "Most energy products ask people to become different people. This launch is built for an ordinary crowded day.",
                                    "status": DraftStatus.DRAFT.value,
                                    "planned_offset": 6,
                                    "created_offset": -6,
                                    "updated_offset": -2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "key": "northstar_retention",
                    "name": "Retention Lab",
                    "description": "Retention and win-back operating system for repeat-purchase campaigns and routine reactivation.",
                    "created_offset": -18,
                    "updated_offset": -1,
                    "campaigns": [
                        {
                            "key": "northstar_momentum_reset",
                            "name": "Subscriber Momentum Reset",
                            "objective": "Increase repeat purchase rate by showing how the routine fits into a normal busy week.",
                            "audience": "Subscribers who purchased once but have not come back in the last 45 days.",
                            "campaign_type": "retention",
                            "start_offset": -5,
                            "end_offset": 16,
                            "status": CampaignStatus.ACTIVE,
                            "created_offset": -8,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "A restart message should lower friction and make the first week feel easy.",
                                "call_to_action": "Restart your subscription.",
                                "tone": "Helpful, practical, non-desperate.",
                                "channels": ["Email", "LinkedIn", "Instagram"],
                                "themes": ["restart routine", "habit stickiness", "proof"],
                                "references": "Retention notes, subscriber replies, and prior win-back tests.",
                            },
                            "assets": [
                                {
                                    "name": "Restart email module pack",
                                    "asset_type": "design_pack",
                                    "file_url": "https://example.com/assets/northstar/restart-email-modules.zip",
                                    "notes": "Reusable modules for restart messaging and offer framing.",
                                    "created_offset": -4,
                                },
                            ],
                            "manual_calendar_items": [
                                {
                                    "title": "Restart offer QA",
                                    "platform": "Notion",
                                    "item_type": "qa",
                                    "scheduled_offset": 2,
                                    "status": "scheduled",
                                    "notes": "Final QA pass across email, landing, and offer logic.",
                                },
                            ],
                            "completed_milestones": {
                                CampaignMilestoneKey.BRIEF_APPROVED.value,
                            },
                            "dependencies": [
                                {
                                    "dependent_type": CampaignDependencyNodeType.CAMPAIGN_MILESTONE,
                                    "dependent_milestone_key": CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY.value,
                                    "blocker_type": CampaignDependencyNodeType.DRAFT_STAGE,
                                    "blocker_draft_key": "northstar_productivity_myths",
                                    "blocker_stage_key": DraftStatus.APPROVED.value,
                                    "note": "Launch-ready depends on the overdue productivity-myths draft clearing approval.",
                                    "created_offset": -1,
                                },
                            ],
                            "drafts": [
                                {
                                    "key": "northstar_winback_email",
                                    "title": "Win-back restart email",
                                    "platform": "Email",
                                    "content_type": "newsletter",
                                    "body": "A simple restart email showing how subscribers can come back without rebuilding their whole routine.",
                                    "status": DraftStatus.SCHEDULED.value,
                                    "planned_offset": 1,
                                    "reviewer": "jordan",
                                    "review_comment": "Much better. The restart payoff is clear now.",
                                    "rejection_comment": "The first version buried the incentive and over-explained the routine.",
                                    "created_offset": -5,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "northstar_habit_loop_reel",
                                    "title": "Habit loop reel",
                                    "platform": "Instagram",
                                    "content_type": "reel",
                                    "body": "Show the easiest version of the ritual people can keep on a genuinely busy day.",
                                    "status": DraftStatus.DRAFT.value,
                                    "planned_offset": 5,
                                    "created_offset": -4,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "northstar_productivity_myths",
                                    "title": "Productivity myths post",
                                    "platform": "LinkedIn",
                                    "content_type": "organic post",
                                    "body": "A post reframing focus myths that make routines harder to keep than they need to be.",
                                    "status": DraftStatus.IN_REVIEW.value,
                                    "planned_offset": -2,
                                    "review_comment": "The frame is strong. Add one more concrete example before approval.",
                                    "created_offset": -9,
                                    "updated_offset": -2,
                                },
                            ],
                        },
                        {
                            "key": "northstar_partnership_pipeline",
                            "name": "Creator Partnership Pipeline",
                            "objective": "Prepare a tighter outbound creator program for the next launch cycle.",
                            "audience": "Health and productivity creators aligned with proof-led routines rather than hype-based performance claims.",
                            "campaign_type": "partnerships",
                            "start_offset": 11,
                            "end_offset": 39,
                            "status": CampaignStatus.PLANNING,
                            "created_offset": -5,
                            "updated_offset": -1,
                            "brief": {
                                "key_message": "The creator program should feel selective, proof-led, and easy to execute.",
                                "call_to_action": "Confirm the shortlist and outreach plan.",
                                "tone": "Selective, practical, brand-safe.",
                                "channels": ["Email", "Instagram"],
                                "themes": ["creator fit", "proof-led partners", "structured outreach"],
                                "references": "Shortlist spreadsheet, creator notes, and partner tracker.",
                            },
                            "assets": [],
                            "manual_calendar_items": [
                                {
                                    "title": "Creator shortlist review",
                                    "platform": "Meet",
                                    "item_type": "planning_session",
                                    "scheduled_offset": 12,
                                    "status": "planned",
                                    "notes": "Review shortlist tiers and outbound sequence before outreach begins.",
                                },
                            ],
                            "completed_milestones": set(),
                            "dependencies": [],
                            "drafts": [
                                {
                                    "key": "northstar_ambassador_memo",
                                    "title": "Ambassador shortlist memo",
                                    "platform": "Notion",
                                    "content_type": "memo",
                                    "body": "Loose memo on creator fit criteria, proof flags, and priority shortlist notes.",
                                    "status": DraftStatus.IDEA.value,
                                    "created_offset": -2,
                                    "updated_offset": -1,
                                },
                                {
                                    "key": "northstar_outreach_email",
                                    "title": "Partnership outreach email",
                                    "platform": "Email",
                                    "content_type": "sequence",
                                    "body": "Plainspoken first-touch outreach to creators with a clear ask and simple proof context.",
                                    "status": DraftStatus.DRAFT.value,
                                    "planned_offset": 12,
                                    "created_offset": -3,
                                    "updated_offset": -1,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ]

    brands_by_key: dict[str, Brand] = {}
    campaigns_by_key: dict[str, Campaign] = {}
    drafts_by_key: dict[str, ContentDraft] = {}
    memberships: list[BrandMembership] = []

    for brand_spec in brand_specs:
        brand_created_at = offset_datetime(anchor, brand_spec["created_offset"], hour=9)
        brand_updated_at = offset_datetime(anchor, brand_spec["updated_offset"], hour=16)
        brand = ensure_brand(
            db,
            owner=owner,
            name=brand_spec["name"],
            slug=brand_spec["slug"],
            description=brand_spec["description"],
            industry=brand_spec["industry"],
            tone_of_voice=brand_spec["tone_of_voice"],
            target_audience=brand_spec["target_audience"],
            preferred_channels=brand_spec["preferred_channels"],
            guidelines_summary=brand_spec["guidelines_summary"],
        )
        brands_by_key[brand_spec["key"]] = brand
        stamp_record(brand, created_at=brand_created_at, updated_at=brand_updated_at)

        if brand_spec["plan_code"] != "starter" or brand_spec["plan_interval"] != PlanInterval.MONTHLY:
            maybe_upgrade_brand_plan(
                db,
                owner=owner,
                brand_id=brand.id,
                plan_code=brand_spec["plan_code"],
                interval=brand_spec["plan_interval"],
            )

        db.refresh(brand, attribute_names=["subscription"])
        if brand.subscription is not None:
            period_start = offset_datetime(anchor, brand_spec["updated_offset"] - 12, hour=8)
            period_days = 365 if brand_spec["plan_interval"] == PlanInterval.YEARLY else 30
            brand.subscription.current_period_start = period_start
            brand.subscription.current_period_end = period_start + timedelta(days=period_days)
            stamp_record(brand.subscription, created_at=brand_created_at, updated_at=brand_updated_at)

        for member_key, role in brand_spec["members"].items():
            membership = ensure_membership(
                db,
                brand_id=brand.id,
                invite_email=team[member_key].email,
                user_id=team[member_key].id,
                invited_by_id=owner.id,
                role=role,
            )
            membership.invited_at = brand_created_at + timedelta(hours=2)
            membership.joined_at = brand_created_at + timedelta(days=1)
            stamp_record(membership, created_at=brand_created_at + timedelta(hours=1), updated_at=brand_created_at + timedelta(days=1))
            memberships.append(membership)

        for template_spec in brand_spec["templates"]:
            template = ensure_template(
                db,
                owner=owner,
                brand_id=brand.id,
                name=template_spec["name"],
                description=template_spec["description"],
                template_type=template_spec["template_type"],
                platform=template_spec["platform"],
                content_type=template_spec["content_type"],
                body=template_spec["body"],
            )
            template_created_at = offset_datetime(anchor, template_spec["created_offset"], hour=11)
            stamp_record(template, created_at=template_created_at, updated_at=template_created_at + timedelta(hours=3))

        for project_spec in brand_spec["projects"]:
            project_created_at = offset_datetime(anchor, project_spec["created_offset"], hour=9)
            project_updated_at = offset_datetime(anchor, project_spec["updated_offset"], hour=15)
            project = ensure_project(
                db,
                owner=owner,
                brand_id=brand.id,
                name=project_spec["name"],
                description=project_spec["description"],
            )
            stamp_record(project, created_at=project_created_at, updated_at=project_updated_at)

            for campaign_spec in project_spec["campaigns"]:
                campaign_created_at = offset_datetime(anchor, campaign_spec["created_offset"], hour=9)
                campaign_updated_at = offset_datetime(anchor, campaign_spec["updated_offset"], hour=16)
                campaign = ensure_campaign(
                    db,
                    owner=owner,
                    project_id=project.id,
                    name=campaign_spec["name"],
                    objective=campaign_spec["objective"],
                    audience=campaign_spec["audience"],
                    campaign_type=campaign_spec["campaign_type"],
                    start_date=offset_date(anchor, campaign_spec["start_offset"]),
                    end_date=offset_date(anchor, campaign_spec["end_offset"]),
                    status=campaign_spec["status"],
                )
                campaigns_by_key[campaign_spec["key"]] = campaign
                stamp_record(campaign, created_at=campaign_created_at, updated_at=campaign_updated_at)

                ensure_brief(
                    db,
                    campaign_id=campaign.id,
                    key_message=campaign_spec["brief"]["key_message"],
                    call_to_action=campaign_spec["brief"]["call_to_action"],
                    tone=campaign_spec["brief"]["tone"],
                    channels=campaign_spec["brief"]["channels"],
                    themes=campaign_spec["brief"]["themes"],
                    references=campaign_spec["brief"]["references"],
                )
                brief = db.scalar(select(ContentBrief).where(ContentBrief.campaign_id == campaign.id))
                if brief is not None:
                    stamp_record(brief, created_at=campaign_created_at + timedelta(hours=2), updated_at=campaign_created_at + timedelta(hours=5))

                for draft_spec in campaign_spec["drafts"]:
                    planned_publish_at = (
                        offset_datetime(anchor, draft_spec["planned_offset"], hour=10)
                        if "planned_offset" in draft_spec
                        else None
                    )
                    reviewer = team[draft_spec["reviewer"]] if "reviewer" in draft_spec else jordan
                    status = draft_spec["status"]

                    if status in {DraftStatus.PUBLISHED.value, DraftStatus.SCHEDULED.value, DraftStatus.APPROVED.value}:
                        draft = seed_reviewed_draft(
                            db,
                            owner=owner,
                            reviewer=reviewer,
                            campaign_id=campaign.id,
                            title=draft_spec["title"],
                            platform=draft_spec["platform"],
                            content_type=draft_spec["content_type"],
                            body=draft_spec["body"],
                            planned_publish_at=planned_publish_at,
                            final_status=status,
                            review_comment=draft_spec["review_comment"],
                            rejection_comment=draft_spec.get("rejection_comment"),
                        )
                    else:
                        draft = seed_open_draft(
                            db,
                            owner=owner,
                            campaign_id=campaign.id,
                            title=draft_spec["title"],
                            platform=draft_spec["platform"],
                            content_type=draft_spec["content_type"],
                            body=draft_spec["body"],
                            planned_publish_at=planned_publish_at,
                            status=status,
                        )
                        if status == DraftStatus.IN_REVIEW.value and draft_spec.get("review_comment"):
                            add_review_comment(
                                db,
                                draft_id=draft.id,
                                payload=DraftReviewCreate(comment=draft_spec["review_comment"]),
                                user=reviewer,
                            )
                            draft = db.get(ContentDraft, draft.id)

                    if draft is None:
                        raise RuntimeError(f"Unable to seed draft '{draft_spec['title']}'.")

                    draft_created_at = offset_datetime(anchor, draft_spec["created_offset"], hour=10)
                    draft_updated_at = offset_datetime(anchor, draft_spec["updated_offset"], hour=15)
                    stamp_draft_timeline(draft, created_at=draft_created_at, updated_at=draft_updated_at)
                    drafts_by_key[draft_spec["key"]] = draft

                for asset_spec in campaign_spec["assets"]:
                    create_campaign_asset_record(
                        db,
                        campaign=campaign,
                        owner=owner,
                        name=asset_spec["name"],
                        asset_type=asset_spec["asset_type"],
                        file_url=asset_spec["file_url"],
                        notes=asset_spec["notes"],
                        created_at=offset_datetime(anchor, asset_spec["created_offset"], hour=11),
                    )

                for item_spec in campaign_spec["manual_calendar_items"]:
                    create_manual_calendar_item(
                        db,
                        brand=brand,
                        campaign=campaign,
                        owner=owner,
                        title=item_spec["title"],
                        platform=item_spec["platform"],
                        item_type=item_spec["item_type"],
                        scheduled_for=offset_datetime(anchor, item_spec["scheduled_offset"], hour=13),
                        status=item_spec["status"],
                        notes=item_spec["notes"],
                    )

                ensure_campaign_milestones(db, campaign=campaign)
                db.flush()
                db.refresh(campaign, attribute_names=["milestones"])
                milestone_lookup = {
                    milestone.key.value if isinstance(milestone.key, CampaignMilestoneKey) else str(milestone.key): milestone
                    for milestone in campaign.milestones
                }
                milestone_target_dates = {
                    CampaignMilestoneKey.BRIEF_APPROVED.value: campaign.start_date - timedelta(days=6),
                    CampaignMilestoneKey.FIRST_DRAFTS_READY.value: campaign.start_date - timedelta(days=2),
                    CampaignMilestoneKey.ALL_REVIEWS_COMPLETE.value: campaign.end_date - timedelta(days=5),
                    CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY.value: campaign.end_date - timedelta(days=1),
                    CampaignMilestoneKey.CAMPAIGN_COMPLETED.value: campaign.end_date,
                }
                for milestone_key, milestone in milestone_lookup.items():
                    target_date = milestone_target_dates[milestone_key]
                    milestone.target_date = target_date
                    if milestone_key in campaign_spec["completed_milestones"]:
                        completed_at = at_date(target_date, hour=10)
                        milestone.completed_at = completed_at
                        milestone.completed_by_user_id = owner.id
                        milestone.notes = f"Marked complete during the {campaign.name.lower()} operating sequence."
                        stamp_record(
                            milestone,
                            created_at=campaign_created_at + timedelta(days=max(1, milestone.sort_order // 10)),
                            updated_at=completed_at,
                        )
                    else:
                        milestone.completed_at = None
                        milestone.completed_by_user_id = None
                        milestone.notes = f"Scheduled for {target_date.isoformat()} and still in motion."
                        pending_updated_at = min(campaign_updated_at, at_date(target_date, hour=9))
                        stamp_record(
                            milestone,
                            created_at=campaign_created_at + timedelta(days=max(1, milestone.sort_order // 10)),
                            updated_at=max(campaign_created_at, pending_updated_at),
                        )

                for dependency_spec in campaign_spec["dependencies"]:
                    dependency = CampaignDependency(
                        campaign_id=campaign.id,
                        dependent_type=dependency_spec["dependent_type"],
                        dependent_milestone_id=(
                            milestone_lookup[dependency_spec["dependent_milestone_key"]].id
                            if dependency_spec["dependent_type"] == CampaignDependencyNodeType.CAMPAIGN_MILESTONE
                            else None
                        ),
                        dependent_draft_id=dependency_spec.get("dependent_draft_id"),
                        dependent_stage_key=dependency_spec.get("dependent_stage_key"),
                        blocker_type=dependency_spec["blocker_type"],
                        blocker_milestone_id=(
                            milestone_lookup[dependency_spec["blocker_milestone_key"]].id
                            if dependency_spec["blocker_type"] == CampaignDependencyNodeType.CAMPAIGN_MILESTONE
                            else None
                        ),
                        blocker_draft_id=(
                            drafts_by_key[dependency_spec["blocker_draft_key"]].id
                            if dependency_spec["blocker_type"] == CampaignDependencyNodeType.DRAFT_STAGE
                            else None
                        ),
                        blocker_stage_key=dependency_spec.get("blocker_stage_key"),
                        note=dependency_spec["note"],
                        created_by=owner.id,
                    )
                    db.add(dependency)
                    db.flush()
                    dependency_created_at = offset_datetime(anchor, dependency_spec["created_offset"], hour=12)
                    stamp_record(dependency, created_at=dependency_created_at, updated_at=dependency_created_at)

    assignment_specs = [
        {
            "kind": "campaign",
            "campaign_key": "asteron_waitlist_sprint",
            "assignee": "maya",
            "note": "Own the launch run sheet, webinar sequence, and cross-channel approvals.",
            "due_offset": 1,
            "hour": 11,
        },
        {
            "kind": "draft",
            "draft_key": "asteron_launch_narrative",
            "assignee": "leo",
            "assignment_type": AssignmentEntityType.DRAFT,
            "note": "Polish the proof stack and tighten the CTA framing before scheduling.",
            "due_offset": 0,
            "hour": 18,
        },
        {
            "kind": "draft",
            "draft_key": "asteron_beta_faq_thread",
            "assignee": "jordan",
            "assignment_type": AssignmentEntityType.REVIEW_TASK,
            "note": "Final review pass on migration and onboarding answers.",
            "due_offset": -1,
            "hour": 17,
        },
        {
            "kind": "draft",
            "draft_key": "asteron_landing_page_proof_blocks",
            "assignee": "jordan",
            "assignment_type": AssignmentEntityType.REVIEW_TASK,
            "note": "Approve or request one more pass on the proof-block rewrite.",
            "due_offset": 1,
            "hour": 12,
        },
        {
            "kind": "draft",
            "draft_key": "harbor_launch_invite_email",
            "assignee": "sofia",
            "assignment_type": AssignmentEntityType.DRAFT,
            "note": "Take the invite from planning copy to review-ready launch email.",
            "due_offset": 3,
            "hour": 14,
        },
        {
            "kind": "campaign",
            "campaign_key": "harbor_showroom_revival",
            "assignee": "maya",
            "note": "Lock the retailer guest list and showroom event timeline.",
            "due_offset": 4,
            "hour": 10,
        },
        {
            "kind": "draft",
            "draft_key": "northstar_launch_proof_post",
            "assignee": "leo",
            "assignment_type": AssignmentEntityType.DRAFT,
            "note": "Tighten the proof stack for the launch LinkedIn post before it goes live.",
            "due_offset": 2,
            "hour": 16,
        },
        {
            "kind": "draft",
            "draft_key": "northstar_productivity_myths",
            "assignee": "jordan",
            "assignment_type": AssignmentEntityType.REVIEW_TASK,
            "note": "Resolve the final proof gap and clear the overdue myth-busting post.",
            "due_offset": 0,
            "hour": 13,
        },
        {
            "kind": "draft",
            "draft_key": "northstar_outreach_email",
            "assignee": "owner",
            "assignment_type": AssignmentEntityType.DRAFT,
            "note": "Refine partner-fit language before outreach begins next week.",
            "due_offset": 5,
            "hour": 15,
        },
    ]

    for assignment_spec in assignment_specs:
        due_at = offset_datetime(anchor, assignment_spec["due_offset"], hour=assignment_spec["hour"])
        assignee = team[assignment_spec["assignee"]]
        if assignment_spec["kind"] == "campaign":
            ensure_campaign_assignment(
                db,
                actor=owner,
                campaign_id=campaigns_by_key[assignment_spec["campaign_key"]].id,
                assignee_user_id=assignee.id,
                note=assignment_spec["note"],
                due_at=due_at,
            )
        else:
            ensure_draft_assignment(
                db,
                actor=owner,
                draft_id=drafts_by_key[assignment_spec["draft_key"]].id,
                assignee_user_id=assignee.id,
                assignment_type=assignment_spec["assignment_type"],
                note=assignment_spec["note"],
                due_at=due_at,
            )

    comment_specs = [
        {
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "author": "maya",
            "body": "The webinar CTA should show up one beat earlier in the landing path.",
            "created_offset": -2,
            "mention": "owner",
        },
        {
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "author": "owner",
            "body": "Agreed. I am keeping the waitlist CTA in the second section and trimming the founder paragraph.",
            "created_offset": -2,
            "parent_to_previous": True,
        },
        {
            "brand": "asteron",
            "draft": "asteron_beta_faq_thread",
            "author": "jordan",
            "body": "The migration answer is still too soft. It needs one clear promise and one limitation.",
            "created_offset": -1,
            "mention": "leo",
        },
        {
            "brand": "northstar",
            "draft": "northstar_launch_proof_post",
            "author": "maya",
            "body": "This is strong. The first line should mention the ritual rather than the product format.",
            "created_offset": -3,
            "mention": "owner",
        },
        {
            "brand": "harbor",
            "campaign": "harbor_showroom_revival",
            "author": "sofia",
            "body": "We should treat the showroom invite like an editorial opening night, not a retail event blast.",
            "created_offset": -1,
        },
    ]

    previous_comment: CollaborationComment | None = None
    for comment_spec in comment_specs:
        created_at = offset_datetime(anchor, comment_spec["created_offset"], hour=11)
        comment = create_comment_record(
            db,
            brand=brands_by_key[comment_spec["brand"]],
            campaign=campaigns_by_key[comment_spec["campaign"]] if "campaign" in comment_spec else None,
            draft=drafts_by_key[comment_spec["draft"]] if "draft" in comment_spec else None,
            author=team[comment_spec["author"]],
            body=comment_spec["body"],
            created_at=created_at,
            mentioned_user=team[comment_spec["mention"]] if "mention" in comment_spec else None,
            parent_comment=previous_comment if comment_spec.get("parent_to_previous") else None,
        )
        previous_comment = comment

    tool_usage_specs = [
        {
            "tool_name": "fetch_brand_guidelines",
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "draft": "asteron_launch_narrative",
            "created_offset": -2,
            "request_payload": {"brand_id": brands_by_key["asteron"].id},
            "result_summary": {"guidance_points": 5, "channels": ["LinkedIn", "Email", "Instagram"]},
        },
        {
            "tool_name": "fetch_templates",
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "draft": "asteron_launch_narrative",
            "created_offset": -2,
            "minute": 20,
            "request_payload": {"brand_id": brands_by_key["asteron"].id, "platform": "LinkedIn", "content_type": "organic post"},
            "result_summary": {"returned": 2, "total": 3},
        },
        {
            "tool_name": "validate_content_against_guidelines",
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "draft": "asteron_launch_narrative",
            "created_offset": -1,
            "request_payload": {"brand_id": brands_by_key["asteron"].id, "draft_id": drafts_by_key["asteron_launch_narrative"].id},
            "result_summary": {"score": 88, "needs_attention": 2},
        },
        {
            "tool_name": "brand_voice_validator",
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "draft": "asteron_launch_narrative",
            "created_offset": -1,
            "minute": 25,
            "request_payload": {"draft_id": drafts_by_key["asteron_launch_narrative"].id},
            "result_summary": {"voice_score": 91, "summary": "Strong operator tone with one line that reads too broad."},
            "artifact": {
                "artifact_type": HelperArtifactType.VOICE_VALIDATION,
                "title": "Launch narrative voice validation",
                "summary": "Voice alignment is strong, with one sentence flagged as too generic.",
                "payload": {"voice_score": 91, "flagged_lines": ["The third sentence needs more concrete proof."]},
            },
        },
        {
            "tool_name": "cross_channel_adaptation",
            "brand": "asteron",
            "campaign": "asteron_waitlist_sprint",
            "draft": "asteron_launch_narrative",
            "created_offset": -1,
            "minute": 45,
            "request_payload": {"draft_id": drafts_by_key["asteron_launch_narrative"].id, "targets": ["email", "instagram_caption"]},
            "result_summary": {"variations": 2, "summary": "Generated email and caption adaptations from the core launch narrative."},
            "artifact": {
                "artifact_type": HelperArtifactType.CROSS_CHANNEL_ADAPTATION,
                "title": "Launch narrative channel adaptations",
                "summary": "Saved two tighter channel adaptations for email and Instagram.",
                "payload": {"variants": ["email", "instagram_caption"]},
            },
        },
        {
            "tool_name": "template_recommendation",
            "brand": "asteron",
            "campaign": "asteron_conversion_cleanup",
            "draft": "asteron_webinar_followup_email",
            "created_offset": -1,
            "minute": 5,
            "request_payload": {"draft_id": drafts_by_key["asteron_webinar_followup_email"].id},
            "result_summary": {"recommended_templates": 2, "summary": "Matched the draft to webinar follow-up and objection-handling templates."},
            "artifact": {
                "artifact_type": HelperArtifactType.TEMPLATE_RECOMMENDATIONS,
                "title": "Webinar follow-up template recommendations",
                "summary": "Recommended two reusable patterns for the webinar follow-up sequence.",
                "payload": {"template_names": ["Webinar follow-up sequence", "Conversion cleanup email"]},
            },
        },
        {
            "tool_name": "review_feedback_to_revision_checklist",
            "brand": "asteron",
            "campaign": "asteron_conversion_cleanup",
            "draft": "asteron_webinar_followup_email",
            "created_offset": -1,
            "minute": 35,
            "request_payload": {"draft_id": drafts_by_key["asteron_webinar_followup_email"].id},
            "result_summary": {"checklist_items": 4, "summary": "Extracted four specific revision tasks from review feedback."},
            "artifact": {
                "artifact_type": HelperArtifactType.REVISION_CHECKLIST,
                "title": "Webinar follow-up revision checklist",
                "summary": "Saved the revision checklist generated from reviewer comments.",
                "payload": {"items": ["Move replay link up", "Shorten the opener", "Trim duplicate proof", "Tighten CTA"]},
            },
        },
        {
            "tool_name": "asset_recommendation",
            "brand": "northstar",
            "campaign": "northstar_cold_brew_launch",
            "draft": "northstar_launch_proof_post",
            "created_offset": -4,
            "request_payload": {"draft_id": drafts_by_key["northstar_launch_proof_post"].id},
            "result_summary": {"recommended_assets": 3, "summary": "Matched creator stills and CTA lockups to the launch proof post."},
            "artifact": {
                "artifact_type": HelperArtifactType.ASSET_RECOMMENDATIONS,
                "title": "Launch proof asset recommendations",
                "summary": "Recommended creator stills and CTA lockups for the launch post.",
                "payload": {"asset_names": ["Launch creator stills", "Launch CTA lockups"]},
            },
        },
        {
            "tool_name": "brand_voice_validator",
            "brand": "northstar",
            "campaign": "northstar_momentum_reset",
            "draft": "northstar_winback_email",
            "created_offset": -2,
            "request_payload": {"draft_id": drafts_by_key["northstar_winback_email"].id},
            "result_summary": {"voice_score": 87, "summary": "Good practical tone, with one section reading too offer-heavy."},
            "artifact": {
                "artifact_type": HelperArtifactType.VOICE_VALIDATION,
                "title": "Win-back email voice validation",
                "summary": "Voice is aligned overall, but one offer block still feels too pushy.",
                "payload": {"voice_score": 87, "flagged_sections": ["Offer block"]},
            },
        },
        {
            "tool_name": "summarize_review_feedback",
            "brand": "northstar",
            "campaign": "northstar_momentum_reset",
            "draft": "northstar_winback_email",
            "created_offset": -1,
            "request_payload": {"draft_id": drafts_by_key["northstar_winback_email"].id, "limit": 6},
            "result_summary": {"themes": 3, "summary": "Summarized reviewer comments around clarity, proof, and incentive placement."},
        },
    ]

    for tool_usage_spec in tool_usage_specs:
        created_at = offset_datetime(
            anchor,
            tool_usage_spec["created_offset"],
            hour=14,
            minute=tool_usage_spec.get("minute", 0),
        )
        brand = brands_by_key[tool_usage_spec["brand"]]
        campaign = campaigns_by_key[tool_usage_spec["campaign"]]
        draft = drafts_by_key[tool_usage_spec["draft"]]
        log = create_tool_usage_entry(
            db,
            tool_name=tool_usage_spec["tool_name"],
            actor=owner,
            brand=brand,
            campaign=campaign,
            draft=draft,
            target_entity_type="draft",
            target_entity_id=draft.id,
            created_at=created_at,
            request_payload=tool_usage_spec["request_payload"],
            result_summary=tool_usage_spec["result_summary"],
        )
        if "artifact" in tool_usage_spec:
            create_helper_artifact_record(
                db,
                draft=draft,
                creator=owner,
                tool_name=tool_usage_spec["tool_name"],
                artifact_type=tool_usage_spec["artifact"]["artifact_type"],
                title=tool_usage_spec["artifact"]["title"],
                summary=tool_usage_spec["artifact"]["summary"],
                payload=tool_usage_spec["artifact"]["payload"],
                created_at=created_at + timedelta(minutes=5),
                source_log=log,
            )

    notify_users(
        db,
        user_ids=[owner.id],
        brand_id=brands_by_key["asteron"].id,
        notification_type=NotificationType.MENTION,
        title="Launch CTA note",
        body="Maya mentioned a CTA sequencing change in the waitlist sprint workspace.",
        entity_type="campaign",
        entity_id=campaigns_by_key["asteron_waitlist_sprint"].id,
        actor_user_id=maya.id,
        metadata={"campaign_id": campaigns_by_key["asteron_waitlist_sprint"].id},
    )
    notify_users(
        db,
        user_ids=[leo.id, owner.id],
        brand_id=brands_by_key["northstar"].id,
        notification_type=NotificationType.REVIEW_REQUESTED,
        title="Northstar draft needs a pass",
        body="The productivity myths post is still waiting on a final review and proof example.",
        entity_type="draft",
        entity_id=drafts_by_key["northstar_productivity_myths"].id,
        actor_user_id=jordan.id,
        metadata={"draft_id": drafts_by_key["northstar_productivity_myths"].id},
    )
    notify_users(
        db,
        user_ids=[owner.id],
        brand_id=brands_by_key["harbor"].id,
        notification_type=NotificationType.ASSIGNMENT_CREATED,
        title="Showroom planning assignment",
        body="Maya is coordinating the retailer timeline for the showroom revival launch.",
        entity_type="campaign",
        entity_id=campaigns_by_key["harbor_showroom_revival"].id,
        actor_user_id=maya.id,
        metadata={"campaign_id": campaigns_by_key["harbor_showroom_revival"].id},
    )

    db.commit()

    summary = {
        "brands": db.scalar(
            select(func.count(Brand.id))
            .join(BrandMembership)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "projects": db.scalar(
            select(func.count(Project.id))
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "campaigns": db.scalar(
            select(func.count(Campaign.id))
            .join(Project, Project.id == Campaign.project_id)
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "drafts": db.scalar(
            select(func.count(ContentDraft.id))
            .join(Campaign, Campaign.id == ContentDraft.campaign_id)
            .join(Project, Project.id == Campaign.project_id)
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "calendar_items": db.scalar(
            select(func.count(CalendarItem.id))
            .join(BrandMembership, BrandMembership.brand_id == CalendarItem.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "templates": db.scalar(
            select(func.count(ContentTemplate.id))
            .join(BrandMembership, BrandMembership.brand_id == ContentTemplate.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "helper_runs": db.scalar(
            select(func.count(ToolUsageLog.id))
            .join(BrandMembership, BrandMembership.brand_id == ToolUsageLog.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "helper_artifacts": db.scalar(
            select(func.count(DraftHelperArtifact.id))
            .join(ContentDraft, ContentDraft.id == DraftHelperArtifact.draft_id)
            .join(Campaign, Campaign.id == ContentDraft.campaign_id)
            .join(Project, Project.id == Campaign.project_id)
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "subscriptions": db.scalar(
            select(func.count(BrandSubscription.id))
            .join(Brand, Brand.id == BrandSubscription.brand_id)
            .join(BrandMembership, BrandMembership.brand_id == Brand.id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
    }
    print(f"Seeded workspace for {owner.email}")
    for key, value in summary.items():
        print(f"{key}: {value}")


def main() -> None:
    parser = ArgumentParser(description="Seed a realistic demo workspace for a specific user.")
    parser.add_argument("--email", required=True, help="User email that should receive the demo workspace.")
    parser.add_argument("--password", default="demo-pass-1234", help="Password that should be set for the target user.")
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Remove existing application data before rebuilding the workspace. Plans and the target user account are preserved.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_workspace(
            db,
            email=args.email.strip().lower(),
            password=args.password,
            reset_all=args.reset_all,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
