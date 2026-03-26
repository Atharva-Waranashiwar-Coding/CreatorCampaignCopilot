from sqlalchemy.orm import Session

from app.core.enums import DraftStageType
from app.models.user import User
from app.schemas.content_draft import ContentDraftRead, ContentDraftStageMove, ContentDraftUpdate
from app.schemas.draft_review import DraftReviewDecision
from app.services.drafts import _get_draft_with_role, _get_draft_workflow, _serialize_draft, update_draft
from app.services.draft_workflows import get_workflow_stage_or_raise
from app.services.reviews import approve_draft, resubmit_draft, submit_draft_for_review


def move_draft_stage(
    db: Session,
    *,
    draft_id: int,
    payload: ContentDraftStageMove,
    user: User,
) -> ContentDraftRead:
    draft, _ = _get_draft_with_role(db, draft_id=draft_id, user_id=user.id)
    workflow = _get_draft_workflow(draft)
    current_status = draft.status
    target_status = payload.target_status
    current_stage = get_workflow_stage_or_raise(workflow, current_status)
    target_stage = get_workflow_stage_or_raise(workflow, target_status, message_prefix="Target draft status")

    if current_status == target_status:
        return _serialize_draft(draft)

    if target_stage.stage_type == DraftStageType.REVIEW:
        decision = DraftReviewDecision(comment=payload.comment)
        if current_stage.stage_type == DraftStageType.CHANGES_REQUESTED:
            return resubmit_draft(db, draft_id=draft_id, payload=decision, user=user)
        if current_stage.stage_type in {DraftStageType.BACKLOG, DraftStageType.IN_PROGRESS, DraftStageType.APPROVED, DraftStageType.SCHEDULED}:
            return submit_draft_for_review(db, draft_id=draft_id, payload=decision, user=user)

    if target_stage.stage_type == DraftStageType.APPROVED and current_stage.stage_type == DraftStageType.REVIEW:
        return approve_draft(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment=payload.comment),
            user=user,
        )

    if target_stage.stage_type == DraftStageType.CHANGES_REQUESTED:
        raise ValueError("Use the review workflow panel to reject drafts so feedback is captured.")

    return update_draft(
        db,
        draft_id=draft_id,
        payload=ContentDraftUpdate(status=target_status),
        user=user,
    )
