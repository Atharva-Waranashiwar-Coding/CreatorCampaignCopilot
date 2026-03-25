from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.enums import DraftStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.collaboration_comment import CollaborationCommentCreate, CollaborationCommentRead
from app.schemas.content_draft import ContentDraftCreate, ContentDraftRead, ContentDraftUpdate
from app.schemas.draft_version import DraftVersionRead
from app.schemas.draft_review import (
    DraftReviewCreate,
    DraftReviewDecision,
    DraftReviewRead,
    DraftReviewThreadRead,
)
from app.services.assignments import create_draft_assignment, list_draft_assignments
from app.services.drafts import create_draft, delete_draft, get_draft, list_draft_versions, list_drafts, update_draft
from app.services.comments import create_draft_comment, list_draft_comments
from app.services.reviews import (
    add_review_comment,
    approve_draft,
    get_draft_review_thread,
    list_review_queue,
    reject_draft,
    resubmit_draft,
    submit_draft_for_review,
)

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[ContentDraftRead])
def read_drafts(
    campaign_id: int | None = None,
    platform: str | None = None,
    status: DraftStatus | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContentDraftRead]:
    return list_drafts(
        db,
        user=current_user,
        campaign_id=campaign_id,
        platform=platform,
        status=status,
        search=search,
    )


@router.get("/review-queue", response_model=list[ContentDraftRead])
def read_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContentDraftRead]:
    try:
        return list_review_queue(db, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("", response_model=ContentDraftRead, status_code=status.HTTP_201_CREATED)
def create_draft_route(
    payload: ContentDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return create_draft(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{draft_id}/reviews", response_model=DraftReviewThreadRead)
def read_draft_reviews(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftReviewThreadRead:
    try:
        return get_draft_review_thread(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{draft_id}/comments", response_model=list[CollaborationCommentRead])
def read_draft_comments(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollaborationCommentRead]:
    try:
        return list_draft_comments(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/comments", response_model=list[CollaborationCommentRead], status_code=status.HTTP_201_CREATED)
def create_draft_comment_route(
    draft_id: int,
    payload: CollaborationCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollaborationCommentRead]:
    try:
        return create_draft_comment(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{draft_id}/assignments", response_model=list[AssignmentRead])
def read_draft_assignments(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentRead]:
    try:
        return list_draft_assignments(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/assignments", response_model=list[AssignmentRead], status_code=status.HTTP_201_CREATED)
def create_draft_assignment_route(
    draft_id: int,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentRead]:
    try:
        return create_draft_assignment(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{draft_id}/versions", response_model=list[DraftVersionRead])
def read_draft_versions(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DraftVersionRead]:
    try:
        return list_draft_versions(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/reviews", response_model=DraftReviewRead, status_code=status.HTTP_201_CREATED)
def create_draft_review(
    draft_id: int,
    payload: DraftReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftReviewRead:
    try:
        return add_review_comment(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/submit", response_model=ContentDraftRead)
def submit_draft_route(
    draft_id: int,
    payload: DraftReviewDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return submit_draft_for_review(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/approve", response_model=ContentDraftRead)
def approve_draft_route(
    draft_id: int,
    payload: DraftReviewDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return approve_draft(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/reject", response_model=ContentDraftRead)
def reject_draft_route(
    draft_id: int,
    payload: DraftReviewDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return reject_draft(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{draft_id}/resubmit", response_model=ContentDraftRead)
def resubmit_draft_route(
    draft_id: int,
    payload: DraftReviewDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return resubmit_draft(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{draft_id}", response_model=ContentDraftRead)
def read_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return get_draft(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{draft_id}", response_model=ContentDraftRead)
def update_draft_route(
    draft_id: int,
    payload: ContentDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return update_draft(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_route(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_draft(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
