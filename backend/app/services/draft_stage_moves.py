from sqlalchemy.orm import Session

from app.core.enums import DraftStatus
from app.models.user import User
from app.schemas.content_draft import ContentDraftRead, ContentDraftStageMove, ContentDraftUpdate
from app.schemas.draft_review import DraftReviewDecision
from app.services.drafts import _coerce_status, _get_draft_with_role, _serialize_draft, update_draft
from app.services.reviews import approve_draft, resubmit_draft, submit_draft_for_review


def move_draft_stage(
    db: Session,
    *,
    draft_id: int,
    payload: ContentDraftStageMove,
    user: User,
) -> ContentDraftRead:
    draft, _ = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    current_status = _coerce_status(draft.status)
    target_status = payload.target_status

    if current_status == target_status:
        return _serialize_draft(draft)

    if target_status == DraftStatus.IN_REVIEW:
        decision = DraftReviewDecision(comment=payload.comment)
        if current_status in {DraftStatus.IDEA, DraftStatus.DRAFT}:
            return submit_draft_for_review(db, draft_id=draft_id, payload=decision, user=user)
        if current_status == DraftStatus.REJECTED:
            return resubmit_draft(db, draft_id=draft_id, payload=decision, user=user)

    if target_status == DraftStatus.APPROVED and current_status == DraftStatus.IN_REVIEW:
        return approve_draft(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment=payload.comment),
            user=user,
        )

    if target_status == DraftStatus.REJECTED:
        raise ValueError("Use the review workflow panel to reject drafts so feedback is captured.")

    return update_draft(
        db,
        draft_id=draft_id,
        payload=ContentDraftUpdate(status=target_status),
        user=user,
    )
