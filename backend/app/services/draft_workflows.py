from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.enums import DraftStageType, DraftStatus
from app.models.brand import Brand
from app.schemas.draft_workflow import (
    DraftWorkflowRead,
    DraftWorkflowStageRead,
    DraftWorkflowStageWrite,
    DraftWorkflowWrite,
)

DEFAULT_DRAFT_WORKFLOW_STAGES: list[dict[str, object]] = [
    {
        "key": DraftStatus.IDEA.value,
        "label": "Idea",
        "stage_type": DraftStageType.BACKLOG.value,
        "color": "amber",
        "description": "Loose concepts and early hooks.",
        "is_initial": True,
        "allowed_next_stage_keys": [DraftStatus.DRAFT.value, DraftStatus.IN_REVIEW.value],
    },
    {
        "key": DraftStatus.DRAFT.value,
        "label": "Draft",
        "stage_type": DraftStageType.IN_PROGRESS.value,
        "color": "sky",
        "description": "Working copy in active editing.",
        "is_initial": True,
        "allowed_next_stage_keys": [DraftStatus.IDEA.value, DraftStatus.IN_REVIEW.value],
    },
    {
        "key": DraftStatus.IN_REVIEW.value,
        "label": "In Review",
        "stage_type": DraftStageType.REVIEW.value,
        "color": "amber",
        "description": "Waiting on review feedback.",
        "is_initial": True,
        "allowed_next_stage_keys": [DraftStatus.APPROVED.value, DraftStatus.REJECTED.value],
    },
    {
        "key": DraftStatus.APPROVED.value,
        "label": "Approved",
        "stage_type": DraftStageType.APPROVED.value,
        "color": "emerald",
        "description": "Cleared and ready to schedule.",
        "is_initial": False,
        "allowed_next_stage_keys": [DraftStatus.SCHEDULED.value, DraftStatus.PUBLISHED.value],
    },
    {
        "key": DraftStatus.SCHEDULED.value,
        "label": "Scheduled",
        "stage_type": DraftStageType.SCHEDULED.value,
        "color": "cyan",
        "description": "Placed on the campaign calendar.",
        "is_initial": False,
        "allowed_next_stage_keys": [DraftStatus.PUBLISHED.value],
    },
    {
        "key": DraftStatus.PUBLISHED.value,
        "label": "Published",
        "stage_type": DraftStageType.PUBLISHED.value,
        "color": "slate",
        "description": "Live and shipped.",
        "is_initial": False,
        "allowed_next_stage_keys": [],
    },
    {
        "key": DraftStatus.REJECTED.value,
        "label": "Needs Changes",
        "stage_type": DraftStageType.CHANGES_REQUESTED.value,
        "color": "rose",
        "description": "Needs changes before the next review pass.",
        "is_initial": False,
        "allowed_next_stage_keys": [DraftStatus.IN_REVIEW.value],
    },
]

_INITIAL_STAGE_TYPES = {
    DraftStageType.BACKLOG,
    DraftStageType.IN_PROGRESS,
    DraftStageType.REVIEW,
}
_REQUIRED_SINGLE_STAGE_TYPES = {
    DraftStageType.REVIEW,
    DraftStageType.APPROVED,
    DraftStageType.CHANGES_REQUESTED,
    DraftStageType.PUBLISHED,
}


def build_default_draft_workflow_payload() -> list[dict[str, object]]:
    return [dict(stage) for stage in DEFAULT_DRAFT_WORKFLOW_STAGES]


def build_draft_workflow(
    workflow: DraftWorkflowWrite | Sequence[Mapping[str, object]] | None,
) -> DraftWorkflowRead:
    raw_stages: Sequence[Mapping[str, object]] | Sequence[DraftWorkflowStageWrite]
    if workflow is None:
        raw_stages = build_default_draft_workflow_payload()
    elif isinstance(workflow, DraftWorkflowWrite):
        raw_stages = workflow.stages
    else:
        raw_stages = workflow

    stages = [DraftWorkflowStageRead.model_validate(stage) for stage in raw_stages]
    _validate_workflow(stages)

    stage_key_by_type = {stage.stage_type: stage.key for stage in stages}
    return DraftWorkflowRead(
        stages=stages,
        initial_stage_keys=[stage.key for stage in stages if stage.is_initial],
        review_stage_key=stage_key_by_type[DraftStageType.REVIEW],
        approved_stage_key=stage_key_by_type[DraftStageType.APPROVED],
        changes_requested_stage_key=stage_key_by_type[DraftStageType.CHANGES_REQUESTED],
        scheduled_stage_key=stage_key_by_type.get(DraftStageType.SCHEDULED),
        published_stage_key=stage_key_by_type[DraftStageType.PUBLISHED],
    )


def normalize_brand_draft_workflow(workflow: DraftWorkflowWrite | None) -> list[dict[str, object]]:
    resolved = build_draft_workflow(workflow)
    return [stage.model_dump(mode="json") for stage in resolved.stages]


def get_brand_draft_workflow(brand: Brand) -> DraftWorkflowRead:
    return build_draft_workflow(brand.draft_workflow_config)


def draft_workflow_stage_map(workflow: DraftWorkflowRead) -> dict[str, DraftWorkflowStageRead]:
    return {stage.key: stage for stage in workflow.stages}


def get_workflow_stage_or_raise(
    workflow: DraftWorkflowRead,
    stage_key: str,
    *,
    message_prefix: str = "Draft status",
) -> DraftWorkflowStageRead:
    stage = draft_workflow_stage_map(workflow).get(str(stage_key))
    if stage is None:
        raise ValueError(f"{message_prefix} '{stage_key}' is not part of this brand workflow.")
    return stage


def get_workflow_stage_by_type(
    workflow: DraftWorkflowRead,
    stage_type: DraftStageType,
) -> DraftWorkflowStageRead:
    for stage in workflow.stages:
        if stage.stage_type == stage_type:
            return stage
    raise ValueError(f"Workflow is missing the required '{stage_type.value}' stage.")


def is_workflow_transition_allowed(
    workflow: DraftWorkflowRead,
    current_stage_key: str,
    next_stage_key: str,
) -> bool:
    if current_stage_key == next_stage_key:
        return True
    stage = get_workflow_stage_or_raise(workflow, current_stage_key)
    return next_stage_key in stage.allowed_next_stage_keys


def _validate_workflow(stages: list[DraftWorkflowStageRead]) -> None:
    keys = [stage.key for stage in stages]
    duplicates = {key for key in keys if keys.count(key) > 1}
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(f"Workflow stage keys must be unique. Duplicate keys: {duplicate_list}.")

    missing_initial = [stage.label for stage in stages if stage.is_initial and stage.stage_type not in _INITIAL_STAGE_TYPES]
    if missing_initial:
        labels = ", ".join(sorted(missing_initial))
        raise ValueError(f"Only backlog, in-progress, or review stages can be initial stages. Invalid stages: {labels}.")

    if not any(stage.is_initial for stage in stages):
        raise ValueError("Workflow must include at least one initial stage.")

    stage_count_by_type: dict[DraftStageType, int] = {}
    for stage in stages:
        stage_count_by_type[stage.stage_type] = stage_count_by_type.get(stage.stage_type, 0) + 1
        if stage.key in stage.allowed_next_stage_keys:
            raise ValueError(f"Stage '{stage.label}' cannot transition to itself.")

    for stage_type in _REQUIRED_SINGLE_STAGE_TYPES:
        count = stage_count_by_type.get(stage_type, 0)
        if count != 1:
            raise ValueError(f"Workflow must include exactly one '{stage_type.value}' stage.")

    if stage_count_by_type.get(DraftStageType.SCHEDULED, 0) > 1:
        raise ValueError("Workflow can include at most one scheduled stage.")

    stage_map = {stage.key: stage for stage in stages}
    for stage in stages:
        missing_targets = [key for key in stage.allowed_next_stage_keys if key not in stage_map]
        if missing_targets:
            missing_list = ", ".join(sorted(missing_targets))
            raise ValueError(f"Stage '{stage.label}' references unknown transition targets: {missing_list}.")

    review_stage = next(stage for stage in stages if stage.stage_type == DraftStageType.REVIEW)
    approved_stage = next(stage for stage in stages if stage.stage_type == DraftStageType.APPROVED)
    changes_requested_stage = next(stage for stage in stages if stage.stage_type == DraftStageType.CHANGES_REQUESTED)
    published_stage = next(stage for stage in stages if stage.stage_type == DraftStageType.PUBLISHED)

    if approved_stage.key not in review_stage.allowed_next_stage_keys:
        raise ValueError("The review stage must transition to the approved stage.")
    if changes_requested_stage.key not in review_stage.allowed_next_stage_keys:
        raise ValueError("The review stage must transition to the changes-requested stage.")
    if published_stage.allowed_next_stage_keys:
        raise ValueError("The published stage cannot define outgoing transitions.")
