from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assignment import AssignmentRead, AssignmentUpdate
from app.services.assignments import list_user_open_assignments, serialize_assignment, update_assignment

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/mine", response_model=list[AssignmentRead])
def read_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentRead]:
    try:
        return [serialize_assignment(item) for item in list_user_open_assignments(db, user_id=current_user.id)]
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment_route(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssignmentRead:
    try:
        return update_assignment(db, assignment_id=assignment_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
