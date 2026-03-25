from sqlalchemy.orm import Session

from app.core.enums import DraftReviewAction, DraftStatus
from app.core.permissions import REVIEW_WORKFLOW_ROLES, WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.draft_review import DraftReview
from app.models.user import User
from app.schemas.content_draft import ContentDraftRead
from app.schemas.draft_review import DraftReviewCreate, DraftReviewDecision, DraftReviewRead, DraftReviewThreadRead
from app.services.audit import record_audit_log
from app.services.drafts import (
    _coerce_status,
    _create_version_snapshot,
    _get_draft_with_role,
    _serialize_draft,
    _sync_draft_calendar_item,
    list_drafts,
)


def _serialize_review(review: DraftReview) -> DraftReviewRead:
    return DraftReviewRead(
        id=review.id,
        draft_id=review.draft_id,
        actor_user_id=review.actor_user_id,
        actor_name=review.actor.full_name if review.actor else None,
        action=review.action,
        comment=review.comment,
        version_number=review.version_number,
        from_status=_coerce_status(review.from_status) if review.from_status is not None else None,
        to_status=_coerce_status(review.to_status) if review.to_status is not None else None,
        created_at=review.created_at,
    )


def _available_actions(role, status: DraftStatus) -> list[DraftReviewAction]:
    actions: list[DraftReviewAction] = []

    if role in REVIEW_WORKFLOW_ROLES:
        actions.append(DraftReviewAction.COMMENTED)
        if status == DraftStatus.IN_REVIEW:
            actions.extend([DraftReviewAction.APPROVED, DraftReviewAction.REJECTED])

    if role in WORKSPACE_MANAGEMENT_ROLES:
        if status in {DraftStatus.IDEA, DraftStatus.DRAFT}:
            actions.append(DraftReviewAction.SUBMITTED)
        if status == DraftStatus.REJECTED:
            actions.append(DraftReviewAction.RESUBMITTED)

    return actions


def _build_review_thread(draft, membership) -> DraftReviewThreadRead:
    return DraftReviewThreadRead(
        draft_id=draft.id,
        current_user_role=membership.role,
        available_actions=_available_actions(membership.role, _coerce_status(draft.status)),
        reviews=[_serialize_review(review) for review in draft.reviews],
    )


def _create_review_entry(
    db: Session,
    *,
    draft,
    actor_user_id: int,
    action: DraftReviewAction,
    comment: str | None,
    from_status: DraftStatus | None,
    to_status: DraftStatus | None,
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
    return review


def get_draft_review_thread(db: Session, *, draft_id: int, user: User) -> DraftReviewThreadRead:
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    return _build_review_thread(draft, membership)


def list_review_queue(db: Session, *, user: User) -> list[ContentDraftRead]:
    return list_drafts(db, user=user, status=DraftStatus.IN_REVIEW)


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

    current_status = _coerce_status(draft.status)
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
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "status": current_status.value},
    )
    db.commit()
    db.refresh(review, attribute_names=["actor"])
    return _serialize_review(review)


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

    previous_status = _coerce_status(draft.status)
    if previous_status not in {DraftStatus.IDEA, DraftStatus.DRAFT}:
        raise ValueError("Only idea or draft items can be submitted for review.")

    draft.status = DraftStatus.IN_REVIEW
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.SUBMITTED,
        comment=payload.comment,
        from_status=previous_status,
        to_status=DraftStatus.IN_REVIEW,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.submitted_for_review",
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "from": previous_status.value, "to": "in_review"},
    )
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

    previous_status = _coerce_status(draft.status)
    if previous_status != DraftStatus.IN_REVIEW:
        raise ValueError("Only drafts in review can be approved.")

    draft.status = DraftStatus.APPROVED
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.APPROVED,
        comment=payload.comment,
        from_status=previous_status,
        to_status=DraftStatus.APPROVED,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.review_approved",
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "from": previous_status.value, "to": "approved"},
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

    previous_status = _coerce_status(draft.status)
    if previous_status != DraftStatus.IN_REVIEW:
        raise ValueError("Only drafts in review can be rejected.")
    if not payload.comment or not payload.comment.strip():
        raise ValueError("A rejection comment is required.")

    draft.status = DraftStatus.REJECTED
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.REJECTED,
        comment=payload.comment,
        from_status=previous_status,
        to_status=DraftStatus.REJECTED,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.review_rejected",
        metadata={"campaign_id": draft.campaign_id, "draft_id": draft.id, "from": previous_status.value, "to": "rejected"},
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
    draft, membership = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to resubmit drafts.",
    )

    previous_status = _coerce_status(draft.status)
    if previous_status != DraftStatus.REJECTED:
        raise ValueError("Only rejected drafts can be resubmitted.")

    draft.current_version_number += 1
    draft.status = DraftStatus.IN_REVIEW
    _create_version_snapshot(
        db,
        draft=draft,
        actor_user_id=user.id,
        change_summary="Resubmitted after review feedback",
    )
    review = _create_review_entry(
        db,
        draft=draft,
        actor_user_id=user.id,
        action=DraftReviewAction.RESUBMITTED,
        comment=payload.comment,
        from_status=previous_status,
        to_status=DraftStatus.IN_REVIEW,
    )
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_review",
        entity_id=review.id,
        action="draft.resubmitted_for_review",
        metadata={
            "campaign_id": draft.campaign_id,
            "draft_id": draft.id,
            "from": previous_status.value,
            "to": "in_review",
            "version_number": draft.current_version_number,
        },
    )
    _sync_draft_calendar_item(db, draft=draft, actor_user_id=user.id)
    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)
