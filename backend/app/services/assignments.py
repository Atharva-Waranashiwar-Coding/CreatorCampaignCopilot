from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AssignmentEntityType, AssignmentStatus, MembershipStatus, NotificationType
from app.core.permissions import (
    COLLABORATION_WRITE_ROLES,
    REVIEW_WORKFLOW_ROLES,
    WORKSPACE_MANAGEMENT_ROLES,
    require_role,
)
from app.models.assignment import Assignment
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.project import Project
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentRead, AssignmentUpdate
from app.services.audit import record_audit_log
from app.services.notifications import notify_users


def serialize_assignment(assignment: Assignment) -> AssignmentRead:
    return AssignmentRead(
        id=assignment.id,
        brand_id=assignment.brand_id,
        assignment_type=assignment.assignment_type,
        campaign_id=assignment.campaign_id,
        draft_id=assignment.draft_id,
        entity_id=assignment.entity_id,
        assignee_user_id=assignment.assignee_user_id,
        assignee_name=assignment.assignee.full_name if assignment.assignee else None,
        assignee_email=assignment.assignee.email if assignment.assignee else None,
        assigned_by_user_id=assignment.assigned_by_user_id,
        assigned_by_name=assignment.assigned_by.full_name if assignment.assigned_by else None,
        note=assignment.note,
        due_at=assignment.due_at,
        status=assignment.status,
        completed_at=assignment.completed_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


def list_assignable_brand_members(db: Session, *, brand_id: int) -> list[User]:
    return db.scalars(
        select(User)
        .join(BrandMembership, BrandMembership.user_id == User.id)
        .where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(User.full_name.asc())
    ).all()


def list_entity_assignments(
    db: Session,
    *,
    brand_id: int,
    assignment_type: AssignmentEntityType,
    entity_id: int,
) -> list[AssignmentRead]:
    query = (
        select(Assignment)
        .options(joinedload(Assignment.assignee), joinedload(Assignment.assigned_by))
        .where(
            Assignment.brand_id == brand_id,
            Assignment.assignment_type == assignment_type,
            Assignment.entity_id == entity_id,
        )
        .order_by(Assignment.created_at.desc())
    )
    return [serialize_assignment(item) for item in db.scalars(query).all()]


def list_campaign_assignments(db: Session, *, campaign_id: int, user: User) -> list[AssignmentRead]:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    return list_entity_assignments(
        db,
        brand_id=campaign.project.brand_id,
        assignment_type=AssignmentEntityType.CAMPAIGN,
        entity_id=campaign.id,
    )


def create_campaign_assignment(
    db: Session,
    *,
    campaign_id: int,
    payload: AssignmentCreate,
    user: User,
) -> list[AssignmentRead]:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to assign campaign work.",
    )
    _ensure_assignable_member(
        db,
        brand_id=campaign.project.brand_id,
        assignee_user_id=payload.assignee_user_id,
        assignment_type=AssignmentEntityType.CAMPAIGN,
    )
    _assert_no_open_duplicate(
        db,
        brand_id=campaign.project.brand_id,
        assignment_type=AssignmentEntityType.CAMPAIGN,
        entity_id=campaign.id,
        assignee_user_id=payload.assignee_user_id,
    )

    assignment = Assignment(
        brand_id=campaign.project.brand_id,
        assignment_type=AssignmentEntityType.CAMPAIGN,
        campaign_id=campaign.id,
        draft_id=None,
        entity_id=campaign.id,
        assignee_user_id=payload.assignee_user_id,
        assigned_by_user_id=user.id,
        note=payload.note.strip() if payload.note else None,
        due_at=payload.due_at,
        status=AssignmentStatus.OPEN,
    )
    db.add(assignment)
    db.flush()
    _record_assignment_creation(db, assignment=assignment, actor=user, campaign_id=campaign.id, draft_id=None)
    db.commit()
    return list_campaign_assignments(db, campaign_id=campaign.id, user=user)


def list_draft_assignments(db: Session, *, draft_id: int, user: User) -> list[AssignmentRead]:
    draft, _ = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    assignments = db.scalars(
        select(Assignment)
        .options(joinedload(Assignment.assignee), joinedload(Assignment.assigned_by))
        .where(
            Assignment.brand_id == draft.campaign.project.brand_id,
            Assignment.entity_id == draft.id,
            Assignment.assignment_type.in_([AssignmentEntityType.DRAFT, AssignmentEntityType.REVIEW_TASK]),
        )
        .order_by(Assignment.created_at.desc())
    ).all()
    return [serialize_assignment(item) for item in assignments]


def create_draft_assignment(
    db: Session,
    *,
    draft_id: int,
    payload: AssignmentCreate,
    user: User,
) -> list[AssignmentRead]:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to assign draft work.",
    )
    assignment_type = payload.assignment_type or AssignmentEntityType.DRAFT
    _ensure_assignable_member(
        db,
        brand_id=draft.campaign.project.brand_id,
        assignee_user_id=payload.assignee_user_id,
        assignment_type=assignment_type,
    )
    _assert_no_open_duplicate(
        db,
        brand_id=draft.campaign.project.brand_id,
        assignment_type=assignment_type,
        entity_id=draft.id,
        assignee_user_id=payload.assignee_user_id,
    )

    assignment = Assignment(
        brand_id=draft.campaign.project.brand_id,
        assignment_type=assignment_type,
        campaign_id=draft.campaign_id,
        draft_id=draft.id,
        entity_id=draft.id,
        assignee_user_id=payload.assignee_user_id,
        assigned_by_user_id=user.id,
        note=payload.note.strip() if payload.note else None,
        due_at=payload.due_at,
        status=AssignmentStatus.OPEN,
    )
    db.add(assignment)
    db.flush()
    _record_assignment_creation(db, assignment=assignment, actor=user, campaign_id=draft.campaign_id, draft_id=draft.id)
    db.commit()
    return list_draft_assignments(db, draft_id=draft.id, user=user)


def update_assignment(
    db: Session,
    *,
    assignment_id: int,
    payload: AssignmentUpdate,
    user: User,
) -> AssignmentRead:
    row = db.execute(
        select(Assignment, BrandMembership)
        .join(BrandMembership, BrandMembership.brand_id == Assignment.brand_id)
        .options(joinedload(Assignment.assignee), joinedload(Assignment.assigned_by))
        .where(
            Assignment.id == assignment_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise LookupError("Assignment not found.")

    assignment, membership = row[0], row[1]
    data = payload.model_dump(exclude_unset=True)
    is_manager = membership.role in WORKSPACE_MANAGEMENT_ROLES
    can_complete_own_assignment = (
        assignment.assignee_user_id == user.id
        and set(data).issubset({"status"})
        and data.get("status") == AssignmentStatus.COMPLETED
    )
    if not is_manager and not can_complete_own_assignment:
        raise PermissionError("You do not have permission to update assignments.")

    if payload.assignee_user_id is not None and payload.assignee_user_id != assignment.assignee_user_id:
        _ensure_assignable_member(
            db,
            brand_id=assignment.brand_id,
            assignee_user_id=payload.assignee_user_id,
            assignment_type=assignment.assignment_type,
        )
        assignment.assignee_user_id = payload.assignee_user_id
        notify_users(
            db,
            user_ids=[assignment.assignee_user_id],
            brand_id=assignment.brand_id,
            notification_type=NotificationType.ASSIGNMENT_CREATED,
            title="You were assigned new work",
            body="An existing assignment was reassigned to you.",
            entity_type=assignment.assignment_type.value,
            entity_id=assignment.entity_id,
            actor_user_id=user.id,
            metadata={"assignment_id": assignment.id, "assignment_type": assignment.assignment_type.value},
        )

    if payload.note is not None:
        assignment.note = payload.note.strip() if payload.note else None
    if payload.due_at is not None:
        assignment.due_at = payload.due_at
    if payload.status is not None:
        assignment.status = payload.status
        assignment.completed_at = datetime.now(UTC) if payload.status == AssignmentStatus.COMPLETED else None

    record_audit_log(
        db,
        brand_id=assignment.brand_id,
        actor_user_id=user.id,
        entity_type="assignment",
        entity_id=assignment.id,
        action="assignment.updated",
        metadata={"assignment_type": assignment.assignment_type.value, "entity_id": assignment.entity_id},
    )
    db.commit()
    db.refresh(assignment)
    return serialize_assignment(assignment)


def list_user_open_assignments(db: Session, *, user_id: int) -> list[Assignment]:
    return db.scalars(
        select(Assignment)
        .options(joinedload(Assignment.assignee), joinedload(Assignment.assigned_by))
        .where(
            Assignment.assignee_user_id == user_id,
            Assignment.status == AssignmentStatus.OPEN,
        )
        .order_by(Assignment.due_at.asc().nullslast(), Assignment.created_at.desc())
    ).all()


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(joinedload(Campaign.project))
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")
    return row[0], row[1]


def _get_draft_with_role(db: Session, *, draft_id: int, user_id: int) -> tuple[ContentDraft, BrandMembership]:
    row = db.execute(
        select(ContentDraft, BrandMembership)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(joinedload(ContentDraft.campaign).joinedload(Campaign.project))
        .where(
            ContentDraft.id == draft_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this draft.")
    return row[0], row[1]


def _ensure_assignable_member(
    db: Session,
    *,
    brand_id: int,
    assignee_user_id: int,
    assignment_type: AssignmentEntityType,
) -> BrandMembership:
    membership = db.scalar(
        select(BrandMembership).where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.user_id == assignee_user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise ValueError("Assignee must be an active member of the brand.")

    allowed_roles = REVIEW_WORKFLOW_ROLES if assignment_type == AssignmentEntityType.REVIEW_TASK else COLLABORATION_WRITE_ROLES
    require_role(membership.role, allowed_roles, "Assignee does not have the right brand role for this assignment.")
    return membership


def _assert_no_open_duplicate(
    db: Session,
    *,
    brand_id: int,
    assignment_type: AssignmentEntityType,
    entity_id: int,
    assignee_user_id: int,
) -> None:
    existing = db.scalar(
        select(Assignment.id).where(
            Assignment.brand_id == brand_id,
            Assignment.assignment_type == assignment_type,
            Assignment.entity_id == entity_id,
            Assignment.assignee_user_id == assignee_user_id,
            Assignment.status == AssignmentStatus.OPEN,
        )
    )
    if existing is not None:
        raise ValueError("That user already has an open assignment for this item.")


def _record_assignment_creation(
    db: Session,
    *,
    assignment: Assignment,
    actor: User,
    campaign_id: int | None,
    draft_id: int | None,
) -> None:
    record_audit_log(
        db,
        brand_id=assignment.brand_id,
        actor_user_id=actor.id,
        entity_type="assignment",
        entity_id=assignment.id,
        action="assignment.created",
        metadata={
            "assignment_type": assignment.assignment_type.value,
            "campaign_id": campaign_id,
            "draft_id": draft_id,
            "assignee_user_id": assignment.assignee_user_id,
        },
    )
    if assignment.assignee_user_id != actor.id:
        notify_users(
            db,
            user_ids=[assignment.assignee_user_id],
            brand_id=assignment.brand_id,
            notification_type=NotificationType.ASSIGNMENT_CREATED,
            title="You were assigned new work",
            body=f"{actor.full_name} assigned you to a {assignment.assignment_type.value.replace('_', ' ')}.",
            entity_type=assignment.assignment_type.value,
            entity_id=assignment.entity_id,
            actor_user_id=actor.id,
            metadata={"assignment_id": assignment.id, "assignment_type": assignment.assignment_type.value},
        )
