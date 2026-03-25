from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AssignmentEntityType, AssignmentStatus, MembershipStatus
from app.models.assignment import Assignment
from app.models.brand_membership import BrandMembership
from app.models.user import User
from app.schemas.assignment import AssignmentRead


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
