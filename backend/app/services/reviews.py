from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AssignmentEntityType, AssignmentStatus, DraftReviewAction, DraftStageType, MembershipStatus, NotificationType
from app.core.permissions import REVIEW_WORKFLOW_ROLES, WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.assignment import Assignment
from app.models.brand_membership import BrandMembership
from app.models.draft_review import DraftReview
from app.models.user import User
from app.schemas.content_draft import ContentDraftRead
from app.schemas.draft_review import DraftReviewCreate, DraftReviewDecision, DraftReviewRead, DraftReviewThreadRead
from app.services.audit import record_audit_log
from app.services.campaign_dependencies import assert_draft_stage_dependencies_satisfied
from app.services.collaboration import create_review_mentions, serialize_mention
from app.services.drafts import (
    _coerce_status,
    _create_version_snapshot,
    _get_draft_with_role,
    _get_draft_workflow,
    _serialize_draft,
    _sync_draft_calendar_item,
    list_drafts,
)
from app.services.draft_workflows import get_workflow_stage_by_type, get_workflow_stage_or_raise, is_workflow_transition_allowed
from app.services.notifications import notify_users


def _status_label(workflow, status: str | None) -> str | None:
    if status is None:
        return None
    try:
        return get_workflow_stage_or_raise(workflow, status).label
    except ValueError:
        return status.replace("_", " ").replace("-", " ").title()


def _serialize_review(review: DraftReview, workflow) -> DraftReviewRead:
    return DraftReviewRead(
        id=review.id,
        draft_id=review.draft_id,
        actor_user_id=review.actor_user_id,
        actor_name=review.actor.full_name if review.actor else None,
        action=review.action,
        comment=review.comment,
        mentions=[serialize_mention(mention) for mention in review.mentions],
        version_number=review.version_number,
        from_status=_coerce_status(review.from_status),
        from_status_label=_status_label(workflow, _coerce_status(review.from_status)),
        to_status=_coerce_status(review.to_status),
        to_status_label=_status_label(workflow, _coerce_status(review.to_status)),
        created_at=review.created_at,
    )


def _review_submission_action(draft) -> DraftReviewAction:
    has_prior_rejection = any(review.action == DraftReviewAction.REJECTED for review in draft.reviews)
    return DraftReviewAction.RESUBMITTED if has_prior_rejection else DraftReviewAction.SUBMITTED


def _available_actions(role, draft) -> list[DraftReviewAction]:
    workflow = _get_draft_workflow(draft)
    current_stage = get_workflow_stage_or_raise(workflow, draft.status)
    review_stage = get_workflow_stage_by_type(workflow, DraftStageType.REVIEW)
    actions: list[DraftReviewAction] = []

    if role in REVIEW_WORKFLOW_ROLES:
        actions.append(DraftReviewAction.COMMENTED)
        if current_stage.stage_type == DraftStageType.REVIEW:
            actions.extend([DraftReviewAction.APPROVED, DraftReviewAction.REJECTED])

    if role in WORKSPACE_MANAGEMENT_ROLES:
        if current_stage.stage_type != DraftStageType.REVIEW and is_workflow_transition_allowed(
            workflow,
            current_stage.key,
            review_stage.key,
        ):
            actions.append(_review_submission_action(draft))

    return actions


def _build_review_thread(draft, membership) -> DraftReviewThreadRead:
    workflow = _get_draft_workflow(draft)
    return DraftReviewThreadRead(
        draft_id=draft.id,
        current_user_role=membership.role,
        available_actions=_available_actions(membership.role, draft),
        reviews=[_serialize_review(review, workflow) for review in draft.reviews],
    )


def _create_review_entry(
    db: Session,
    *,
    draft,
    actor_user_id: int,
    action: DraftReviewAction,
    comment: str | None,
    from_status: str | None,
    to_status: str | None,
) -> DraftReview:
    review = DraftReview(
        draft_id=draft.id,
        actor_user_id=actor_user_id,
        action=action,
        comment=comment.strip() if isinstance(comment, str) and comment.strip() else None,
        version_number=draft.current_version_number,
        from_status=from_status,
        to_status=to_status,
    )
    db.add(review)
    db.flush()
    if review.comment:
        mentions = create_review_mentions(
            db,
            brand_id=draft.campaign.project.brand_id,
            author_user_id=actor_user_id,
            review=review,
        )
        notify_users(
            db,
            user_ids=[mention.mentioned_user_id for mention in mentions],
            brand_id=draft.campaign.project.brand_id,
            notification_type=NotificationType.MENTION,
            title="You were mentioned in a review note",
            body=f"{draft.title} includes a review note that mentioned you.",
            entity_type="content_draft",
            entity_id=draft.id,
            actor_user_id=actor_user_id,
            metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "review_id": review.id},
        )
    return review


def _review_notification_recipient_ids(db: Session, *, draft, actor_user_id: int) -> list[int]:
    review_assignments = db.scalars(
        select(Assignment.assignee_user_id).where(
            Assignment.brand_id == draft.campaign.project.brand_id,
            Assignment.assignment_type == AssignmentEntityType.REVIEW_TASK,
            Assignment.entity_id == draft.id,
            Assignment.status == AssignmentStatus.OPEN,
            Assignment.assignee_user_id != actor_user_id,
        )
    ).all()
    if review_assignments:
        return list(review_assignments)

    reviewer_members = db.scalars(
        select(BrandMembership.user_id).where(
            BrandMembership.brand_id == draft.campaign.project.brand_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
            BrandMembership.role.in_(REVIEW_WORKFLOW_ROLES),
            BrandMembership.user_id.is_not(None),
            BrandMembership.user_id != actor_user_id,
        )
    ).all()
    return [user_id for user_id in reviewer_members if user_id is not None]


def _notify_review_requested(db: Session, *, draft, actor_user: User, review_id: int) -> None:
    recipient_ids = _review_notification_recipient_ids(db, draft=draft, actor_user_id=actor_user.id)
    if not recipient_ids:
        return
    notify_users(
        db,
        user_ids=recipient_ids,
        brand_id=draft.campaign.project.brand_id,
        notification_type=NotificationType.REVIEW_REQUESTED,
        title="Review requested",
        body=f"{actor_user.full_name} requested review on {draft.title}.",
        entity_type="content_draft",
        entity_id=draft.id,
        actor_user_id=actor_user.id,
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "review_id": review_id},
    )


def _notify_draft_decision(
    db: Session,
    *,
    draft,
    actor_user: User,
    notification_type: NotificationType,
    review_id: int,
) -> None:
    recipient_ids = {draft.created_by}
    assigned_ids = db.scalars(
        select(Assignment.assignee_user_id).where(
            Assignment.brand_id == draft.campaign.project.brand_id,
            Assignment.entity_id == draft.id,
            Assignment.assignment_type.in_([AssignmentEntityType.DRAFT, AssignmentEntityType.REVIEW_TASK]),
            Assignment.status == AssignmentStatus.OPEN,
        )
    ).all()
    recipient_ids.update(assigned_ids)
    recipient_ids.discard(actor_user.id)
    if not recipient_ids:
        return

    title = "Draft approved" if notification_type == NotificationType.DRAFT_APPROVED else "Draft rejected"
    body = (
        f"{actor_user.full_name} approved {draft.title}."
        if notification_type == NotificationType.DRAFT_APPROVED
        else f"{actor_user.full_name} rejected {draft.title}."
    )
    notify_users(
        db,
        user_ids=list(recipient_ids),
        brand_id=draft.campaign.project.brand_id,
        notification_type=notification_type,
        title=title,
        body=body,
        entity_type="content_draft",
        entity_id=draft.id,
        actor_user_id=actor_user.id,
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "review_id": review_id},
    )


def get_draft_review_thread(db: Session, *, draft_id: int, user: User) -> DraftReviewThreadRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    return _build_review_thread(draft, membership)


def list_review_queue(db: Session, *, user: User) -> list[ContentDraftRead]:
    return [draft for draft in list_drafts(db, user=user) if draft.status_type == DraftStageType.REVIEW]


def add_review_comment(
    db: Session,
    *,
    draft_id: int,
    payload: DraftReviewCreate,
    user: User,
) -> DraftReviewRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        REVIEW_WORKFLOW_ROLES,
        "You do not have permission to review drafts.",
    )

    workflow = _get_draft_workflow(draft)
    current_status = draft.status
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.COMMENTED,
        comment=payload.comment,
        from_status=current_status,
        to_status=current_status,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.review_commented",
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "status": current_status},
    )
    db.commit()
    db.refresh(review, attribute_names=["actor"])
    return _serialize_review(review, workflow)


def submit_draft_for_review(
    db: Session,
    *,
    draft_id: int,
    payload: DraftReviewDecision,
    user: User,
) -> ContentDraftRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to submit drafts for review.",
    )

    workflow = _get_draft_workflow(draft)
    previous_status = draft.status
    review_stage = get_workflow_stage_by_type(workflow, DraftStageType.REVIEW)
    current_stage = get_workflow_stage_or_raise(workflow, previous_status)
    if current_stage.stage_type == DraftStageType.REVIEW:
        raise ValueError("This draft is already in the review stage.")
    if not is_workflow_transition_allowed(workflow, previous_status, review_stage.key):
        raise ValueError("This draft cannot be submitted for review from its current workflow stage.")

    action = _review_submission_action(draft)
    if action == DraftReviewAction.RESUBMITTED:
        draft.current_version_number += 1
        _create_version_snapshot(
            db,
            draft=draft,
            actor_user_id=user.id,
            change_summary="Resubmitted after review feedback",
        )

    assert_draft_stage_dependencies_satisfied(db, draft=draft, target_stage_key=review_stage.key)
    draft.status = review_stage.key
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=action,
        comment=payload.comment,
        from_status=previous_status,
        to_status=review_stage.key,
    )
    audit_action = "draft.resubmitted_for_review" if action == DraftReviewAction.RESUBMITTED else "draft.submitted_for_review"
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action=audit_action,
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "from": previous_status, "to": review_stage.key},
    )
    _notify_review_requested(db, draft=draft, actor_user=user, review_id=review.id)
    _sync_draft_calendar_item(db, draft=draft, actor_user_id=user.id)
    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)


def approve_draft(
    db: Session,
    *,
    draft_id: int,
    payload: DraftReviewDecision,
    user: User,
) -> ContentDraftRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        REVIEW_WORKFLOW_ROLES,
        "You do not have permission to approve drafts.",
    )

    workflow = _get_draft_workflow(draft)
    previous_status = draft.status
    current_stage = get_workflow_stage_or_raise(workflow, previous_status)
    approved_stage = get_workflow_stage_by_type(workflow, DraftStageType.APPROVED)
    if current_stage.stage_type != DraftStageType.REVIEW:
        raise ValueError("Only drafts in the review stage can be approved.")
    if not is_workflow_transition_allowed(workflow, previous_status, approved_stage.key):
        raise ValueError("This workflow does not allow approval from the current review stage.")

    assert_draft_stage_dependencies_satisfied(db, draft=draft, target_stage_key=approved_stage.key)
    draft.status = approved_stage.key
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.APPROVED,
        comment=payload.comment,
        from_status=previous_status,
        to_status=approved_stage.key,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.review_approved",
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "from": previous_status, "to": approved_stage.key},
    )
    _notify_draft_decision(
        db,
        draft=draft,
        actor_user=user,
        notification_type=NotificationType.DRAFT_APPROVED,
        review_id=review.id,
    )
    _sync_draft_calendar_item(db, draft=draft, actor_user_id=user.id)
    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)


def reject_draft(
    db: Session,
    *,
    draft_id: int,
    payload: DraftReviewDecision,
    user: User,
) -> ContentDraftRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        REVIEW_WORKFLOW_ROLES,
        "You do not have permission to reject drafts.",
    )

    workflow = _get_draft_workflow(draft)
    previous_status = draft.status
    current_stage = get_workflow_stage_or_raise(workflow, previous_status)
    changes_requested_stage = get_workflow_stage_by_type(workflow, DraftStageType.CHANGES_REQUESTED)
    if current_stage.stage_type != DraftStageType.REVIEW:
        raise ValueError("Only drafts in the review stage can be rejected.")
    if not is_workflow_transition_allowed(workflow, previous_status, changes_requested_stage.key):
        raise ValueError("This workflow does not allow rejection from the current review stage.")
    if not payload.comment or not payload.comment.strip():
        raise ValueError("A rejection comment is required.")

    assert_draft_stage_dependencies_satisfied(db, draft=draft, target_stage_key=changes_requested_stage.key)
    draft.status = changes_requested_stage.key
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.REJECTED,
        comment=payload.comment,
        from_status=previous_status,
        to_status=changes_requested_stage.key,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.review_rejected",
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "from": previous_status, "to": changes_requested_stage.key},
    )
    _notify_draft_decision(
        db,
        draft=draft,
        actor_user=user,
        notification_type=NotificationType.DRAFT_REJECTED,
        review_id=review.id,
    )
    _sync_draft_calendar_item(db, draft=draft, actor_user_id=user.id)
    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)


def resubmit_draft(
    db: Session,
    *,
    draft_id: int,
    payload: DraftReviewDecision,
    user: User,
) -> ContentDraftRead:
    return submit_draft_for_review(db, draft_id=draft_id, payload=payload, user=user)
