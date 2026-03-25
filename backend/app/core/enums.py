from enum import StrEnum


class BrandRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CampaignStatus(StrEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DraftStatus(StrEnum):
    IDEA = "idea"
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    REJECTED = "rejected"


class DraftStageType(StrEnum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    CHANGES_REQUESTED = "changes_requested"


class CampaignMilestoneKey(StrEnum):
    BRIEF_APPROVED = "brief_approved"
    FIRST_DRAFTS_READY = "first_drafts_ready"
    ALL_REVIEWS_COMPLETE = "all_reviews_complete"
    CAMPAIGN_LAUNCH_READY = "campaign_launch_ready"
    CAMPAIGN_COMPLETED = "campaign_completed"


class CampaignDependencyNodeType(StrEnum):
    CAMPAIGN_MILESTONE = "campaign_milestone"
    DRAFT_STAGE = "draft_stage"


class DraftReviewAction(StrEnum):
    COMMENTED = "commented"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUBMITTED = "resubmitted"


class CommentEntityType(StrEnum):
    CAMPAIGN = "campaign"
    DRAFT = "draft"


class AssignmentEntityType(StrEnum):
    CAMPAIGN = "campaign"
    DRAFT = "draft"
    REVIEW_TASK = "review_task"


class AssignmentStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELED = "canceled"


class NotificationType(StrEnum):
    MENTION = "mention"
    REVIEW_REQUESTED = "review_requested"
    DRAFT_APPROVED = "draft_approved"
    DRAFT_REJECTED = "draft_rejected"
    ASSIGNMENT_CREATED = "assignment_created"
    DUE_SOON = "due_soon"


class PlanInterval(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
