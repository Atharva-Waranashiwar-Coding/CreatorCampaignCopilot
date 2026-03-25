from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AssignmentEntityType, BrandRole, CampaignStatus, DraftStatus, MembershipStatus, NotificationType, PlanInterval
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.assignment import Assignment
from app.models.brand import Brand
from app.models.brand_membership import BrandMembership
from app.models.brand_subscription import BrandSubscription
from app.models.campaign import Campaign
from app.models.content_brief import ContentBrief
from app.models.content_draft import ContentDraft
from app.models.content_template import ContentTemplate
from app.models.draft_review import DraftReview
from app.models.draft_version import DraftVersion
from app.models.project import Project
from app.models.user import User
from app.schemas.assignment import AssignmentCreate
from app.schemas.billing import BrandSubscriptionUpdate
from app.schemas.brand import BrandCreate
from app.schemas.campaign import CampaignCreate
from app.schemas.content_draft import ContentDraftCreate, ContentDraftUpdate
from app.schemas.content_template import ContentTemplateCreate
from app.schemas.draft_review import DraftReviewCreate, DraftReviewDecision
from app.schemas.project import ProjectCreate
from app.services.access import get_brand_billing_snapshot, update_brand_subscription
from app.services.assignments import create_campaign_assignment, create_draft_assignment
from app.services.brands import create_brand
from app.services.campaigns import create_campaign
from app.services.drafts import create_draft, update_draft
from app.services.notifications import notify_users
from app.services.projects import create_project
from app.services.reviews import add_review_comment, approve_draft, reject_draft, submit_draft_for_review
from app.services.templates import create_template

DEMO_USERS = (
    {
        "email": "maya.chen.demo@example.com",
        "legacy_emails": ("maya.chen.demo@creatorcopilot.local",),
        "full_name": "Maya Chen",
    },
    {
        "email": "jordan.patel.demo@example.com",
        "legacy_emails": ("jordan.patel.demo@creatorcopilot.local",),
        "full_name": "Jordan Patel",
    },
    {
        "email": "leo.morgan.demo@example.com",
        "legacy_emails": ("leo.morgan.demo@creatorcopilot.local",),
        "full_name": "Leo Morgan",
    },
)


def ensure_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    legacy_emails: tuple[str, ...] = (),
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        for legacy_email in legacy_emails:
            user = db.scalar(select(User).where(User.email == legacy_email))
            if user is not None:
                break
    if user is not None:
        user.email = email
        user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password("demo-pass-1234"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def repair_legacy_draft_statuses(db: Session) -> None:
    legacy_status_map = {status.name: status.value for status in DraftStatus}

    drafts = db.scalars(
        select(ContentDraft).where(ContentDraft.status.in_(legacy_status_map))
    ).all()
    for draft in drafts:
        draft.status = legacy_status_map.get(draft.status, draft.status)

    versions = db.scalars(
        select(DraftVersion).where(DraftVersion.status.in_(legacy_status_map))
    ).all()
    for version in versions:
        version.status = legacy_status_map.get(version.status, version.status)

    reviews = db.scalars(
        select(DraftReview).where(
            DraftReview.from_status.in_(legacy_status_map) | DraftReview.to_status.in_(legacy_status_map)
        )
    ).all()
    for review in reviews:
        if review.from_status in legacy_status_map:
            review.from_status = legacy_status_map[review.from_status]
        if review.to_status in legacy_status_map:
            review.to_status = legacy_status_map[review.to_status]

    if drafts or versions or reviews:
        db.commit()


def ensure_membership(
    db: Session,
    *,
    brand_id: int,
    invite_email: str,
    user_id: int,
    invited_by_id: int,
    role: BrandRole,
) -> BrandMembership:
    membership = db.scalar(
        select(BrandMembership).where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.invite_email == invite_email,
        )
    )
    if membership is None:
        membership = db.scalar(
            select(BrandMembership).where(
                BrandMembership.brand_id == brand_id,
                BrandMembership.user_id == user_id,
            )
        )
    if membership is None:
        membership = BrandMembership(
            brand_id=brand_id,
            user_id=user_id,
            invite_email=invite_email,
            invited_by_id=invited_by_id,
            role=role,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )
        db.add(membership)
    else:
        membership.user_id = user_id
        membership.invite_email = invite_email
        membership.invited_by_id = invited_by_id
        membership.role = role
        membership.status = MembershipStatus.ACTIVE
        membership.joined_at = membership.joined_at or datetime.now(UTC)

    db.commit()
    db.refresh(membership)
    return membership


def ensure_brand(
    db: Session,
    *,
    owner: User,
    name: str,
    slug: str,
    description: str,
    industry: str,
    tone_of_voice: str,
    target_audience: str,
    preferred_channels: list[str],
    guidelines_summary: str,
) -> Brand:
    brand = db.scalar(select(Brand).where(Brand.slug == slug))
    if brand is None:
        create_brand(
            db,
            payload=BrandCreate(
                name=name,
                slug=slug,
                description=description,
                industry=industry,
                tone_of_voice=tone_of_voice,
                target_audience=target_audience,
                preferred_channels=preferred_channels,
                guidelines_summary=guidelines_summary,
            ),
            user=owner,
        )
        brand = db.scalar(select(Brand).where(Brand.slug == slug))

    if brand is None:
        raise RuntimeError(f"Unable to create brand '{name}'.")
    return brand


def ensure_project(db: Session, *, owner: User, brand_id: int, name: str, description: str) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.brand_id == brand_id,
            Project.name == name,
        )
    )
    if project is None:
        create_project(
            db,
            payload=ProjectCreate(
                brand_id=brand_id,
                name=name,
                description=description,
            ),
            user=owner,
        )
        project = db.scalar(
            select(Project).where(
                Project.brand_id == brand_id,
                Project.name == name,
            )
        )

    if project is None:
        raise RuntimeError(f"Unable to create project '{name}'.")
    return project


def ensure_campaign(
    db: Session,
    *,
    owner: User,
    project_id: int,
    name: str,
    objective: str,
    audience: str,
    campaign_type: str,
    start_date: date,
    end_date: date,
    status: CampaignStatus,
) -> Campaign:
    campaign = db.scalar(
        select(Campaign).where(
            Campaign.project_id == project_id,
            Campaign.name == name,
        )
    )
    if campaign is None:
        create_campaign(
            db,
            payload=CampaignCreate(
                project_id=project_id,
                name=name,
                objective=objective,
                audience=audience,
                campaign_type=campaign_type,
                start_date=start_date,
                end_date=end_date,
                status=status,
            ),
            user=owner,
        )
        campaign = db.scalar(
            select(Campaign).where(
                Campaign.project_id == project_id,
                Campaign.name == name,
            )
        )

    if campaign is None:
        raise RuntimeError(f"Unable to create campaign '{name}'.")
    return campaign


def ensure_brief(
    db: Session,
    *,
    campaign_id: int,
    key_message: str,
    call_to_action: str,
    tone: str,
    channels: list[str],
    themes: list[str],
    references: str,
) -> None:
    brief = db.scalar(select(ContentBrief).where(ContentBrief.campaign_id == campaign_id))
    if brief is None:
        brief = ContentBrief(
            campaign_id=campaign_id,
            key_message=key_message,
            call_to_action=call_to_action,
            tone=tone,
            channels=channels,
            themes=themes,
            reference_materials=references,
        )
        db.add(brief)
    else:
        brief.key_message = key_message
        brief.call_to_action = call_to_action
        brief.tone = tone
        brief.channels = channels
        brief.themes = themes
        brief.reference_materials = references
    db.commit()


def ensure_template(
    db: Session,
    *,
    owner: User,
    brand_id: int,
    name: str,
    description: str,
    template_type: str,
    platform: str | None,
    content_type: str | None,
    body: str,
) -> ContentTemplate:
    template = db.scalar(
        select(ContentTemplate).where(
            ContentTemplate.brand_id == brand_id,
            ContentTemplate.name == name,
        )
    )
    if template is None:
        create_template(
            db,
            payload=ContentTemplateCreate(
                brand_id=brand_id,
                name=name,
                description=description,
                template_type=template_type,
                platform=platform,
                content_type=content_type,
                body=body,
            ),
            user=owner,
        )
        template = db.scalar(
            select(ContentTemplate).where(
                ContentTemplate.brand_id == brand_id,
                ContentTemplate.name == name,
            )
        )

    if template is None:
        raise RuntimeError(f"Unable to create template '{name}'.")
    return template


def ensure_draft_assignment(
    db: Session,
    *,
    actor: User,
    draft_id: int,
    assignee_user_id: int,
    assignment_type: AssignmentEntityType,
    note: str,
    due_at: datetime | None,
) -> None:
    existing = db.scalar(
        select(Assignment.id).where(
            Assignment.draft_id == draft_id,
            Assignment.assignee_user_id == assignee_user_id,
            Assignment.assignment_type == assignment_type,
        )
    )
    if existing is not None:
        return

    create_draft_assignment(
        db,
        draft_id=draft_id,
        payload=AssignmentCreate(
            assignment_type=assignment_type,
            assignee_user_id=assignee_user_id,
            note=note,
            due_at=due_at,
        ),
        user=actor,
    )


def ensure_campaign_assignment(
    db: Session,
    *,
    actor: User,
    campaign_id: int,
    assignee_user_id: int,
    note: str,
    due_at: datetime | None,
) -> None:
    existing = db.scalar(
        select(Assignment.id).where(
            Assignment.campaign_id == campaign_id,
            Assignment.assignee_user_id == assignee_user_id,
            Assignment.assignment_type == AssignmentEntityType.CAMPAIGN,
        )
    )
    if existing is not None:
        return

    create_campaign_assignment(
        db,
        campaign_id=campaign_id,
        payload=AssignmentCreate(
            assignee_user_id=assignee_user_id,
            note=note,
            due_at=due_at,
        ),
        user=actor,
    )


def seed_reviewed_draft(
    db: Session,
    *,
    owner: User,
    reviewer: User,
    campaign_id: int,
    title: str,
    platform: str,
    content_type: str,
    body: str,
    planned_publish_at: datetime,
    final_status: str,
    review_comment: str,
    rejection_comment: str | None = None,
) -> ContentDraft:
    draft = db.scalar(
        select(ContentDraft).where(
            ContentDraft.campaign_id == campaign_id,
            ContentDraft.title == title,
        )
    )
    if draft is None:
        created = create_draft(
            db,
            payload=ContentDraftCreate(
                campaign_id=campaign_id,
                title=title,
                platform=platform,
                content_type=content_type,
                content_body=body,
                planned_publish_at=planned_publish_at,
            ),
            user=owner,
        )
        draft_id = created.id
    else:
        draft_id = draft.id

    draft = db.get(ContentDraft, draft_id)
    if draft is None:
        raise RuntimeError(f"Unable to create draft '{title}'.")

    if draft.status == "idea":
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(
                content_body=body,
                planned_publish_at=planned_publish_at,
                status="draft",
            ),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "draft":
        submit_draft_for_review(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment="Ready for a review pass."),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "in_review" and rejection_comment:
        reject_draft(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment=rejection_comment),
            user=reviewer,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "rejected":
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(
                content_body=f"{body}\n\nUpdated after feedback: tightened hook, clearer CTA, stronger proof.",
            ),
            user=owner,
        )
        submit_draft_for_review(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment="Adjusted the hook and CTA."),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "in_review":
        add_review_comment(
            db,
            draft_id=draft_id,
            payload=DraftReviewCreate(comment=review_comment),
            user=reviewer,
        )
        approve_draft(
            db,
            draft_id=draft_id,
            payload=DraftReviewDecision(comment="Good to ship."),
            user=reviewer,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "approved" and final_status in {"scheduled", "published"}:
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(
                status="scheduled",
                planned_publish_at=planned_publish_at,
            ),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is not None and draft.status == "scheduled" and final_status == "published":
        update_draft(
            db,
            draft_id=draft_id,
            payload=ContentDraftUpdate(status="published"),
            user=owner,
        )
        draft = db.get(ContentDraft, draft_id)

    if draft is None:
        raise RuntimeError(f"Unable to create draft '{title}'.")
    return draft


def seed_open_draft(
    db: Session,
    *,
    owner: User,
    campaign_id: int,
    title: str,
    platform: str,
    content_type: str,
    body: str,
    planned_publish_at: datetime | None,
    status: str,
) -> ContentDraft:
    draft = db.scalar(
        select(ContentDraft).where(
            ContentDraft.campaign_id == campaign_id,
            ContentDraft.title == title,
        )
    )
    if draft is None:
        draft = db.get(
            ContentDraft,
            create_draft(
                db,
                payload=ContentDraftCreate(
                    campaign_id=campaign_id,
                    title=title,
                    platform=platform,
                    content_type=content_type,
                    content_body=body,
                    planned_publish_at=planned_publish_at,
                ),
                user=owner,
            ).id,
        )

    if draft is not None and status != draft.status:
        update_draft(
            db,
            draft_id=draft.id,
            payload=ContentDraftUpdate(
                content_body=body,
                planned_publish_at=planned_publish_at,
                status=status,
            ),
            user=owner,
        )
        draft = db.get(ContentDraft, draft.id)

    if draft is None:
        raise RuntimeError(f"Unable to create draft '{title}'.")
    return draft


def maybe_upgrade_brand_plan(db: Session, *, owner: User, brand_id: int, plan_code: str, interval: PlanInterval) -> None:
    snapshot = get_brand_billing_snapshot(db, brand_id=brand_id, user=owner)
    if snapshot.current_plan.code == plan_code and snapshot.subscription.billing_interval == interval:
        return

    update_brand_subscription(
        db,
        brand_id=brand_id,
        payload=BrandSubscriptionUpdate(plan_code=plan_code, billing_interval=interval),
        user=owner,
    )


def seed_workspace(db: Session, *, email: str) -> None:
    owner = db.scalar(select(User).where(User.email == email))
    if owner is None:
        raise LookupError(f"User '{email}' was not found.")

    repair_legacy_draft_statuses(db)

    maya = ensure_user(
        db,
        email=DEMO_USERS[0]["email"],
        full_name=DEMO_USERS[0]["full_name"],
        legacy_emails=DEMO_USERS[0]["legacy_emails"],
    )
    jordan = ensure_user(
        db,
        email=DEMO_USERS[1]["email"],
        full_name=DEMO_USERS[1]["full_name"],
        legacy_emails=DEMO_USERS[1]["legacy_emails"],
    )
    leo = ensure_user(
        db,
        email=DEMO_USERS[2]["email"],
        full_name=DEMO_USERS[2]["full_name"],
        legacy_emails=DEMO_USERS[2]["legacy_emails"],
    )

    today = datetime.now(UTC)
    current_date = today.date()

    northstar = ensure_brand(
        db,
        owner=owner,
        name="Northstar Labs",
        slug="northstar-labs-demo",
        description="Performance-minded wellness brand with a strong founder voice and fast launch cycles.",
        industry="Wellness tech",
        tone_of_voice="Crisp, assured, practical, with proof-led claims and no jargon bloat.",
        target_audience="Operators, creators, and wellness-focused professionals balancing performance and recovery.",
        preferred_channels=["LinkedIn", "Instagram", "Email", "Podcast"],
        guidelines_summary="Lead with proof, make the payoff obvious in one line, and close with a single next step.",
    )
    harbor = ensure_brand(
        db,
        owner=owner,
        name="Harbor & Hill",
        slug="harbor-hill-demo",
        description="Premium home brand shaping seasonal campaigns across editorial, social, and email.",
        industry="Home lifestyle",
        tone_of_voice="Warm, editorial, tactile, and image-driven. Keep copy elegant and concrete.",
        target_audience="Style-conscious households refreshing living spaces for hosting and daily rituals.",
        preferred_channels=["Instagram", "Pinterest", "Email", "Blog"],
        guidelines_summary="Use vivid product imagery, keep claims grounded, and make every message feel styled not salesy.",
    )

    for brand in (northstar, harbor):
        ensure_membership(
            db,
            brand_id=brand.id,
            invite_email=maya.email,
            user_id=maya.id,
            invited_by_id=owner.id,
            role=BrandRole.ADMIN,
        )
        ensure_membership(
            db,
            brand_id=brand.id,
            invite_email=jordan.email,
            user_id=jordan.id,
            invited_by_id=owner.id,
            role=BrandRole.REVIEWER,
        )
        ensure_membership(
            db,
            brand_id=brand.id,
            invite_email=leo.email,
            user_id=leo.id,
            invited_by_id=owner.id,
            role=BrandRole.EDITOR,
        )

    maybe_upgrade_brand_plan(
        db,
        owner=owner,
        brand_id=northstar.id,
        plan_code="growth",
        interval=PlanInterval.YEARLY,
    )

    northstar_project = ensure_project(
        db,
        owner=owner,
        brand_id=northstar.id,
        name="Q2 Demand Engine",
        description="Launches, nurture, and social proof loops for the spring growth window.",
    )
    harbor_project = ensure_project(
        db,
        owner=owner,
        brand_id=harbor.id,
        name="Spring Hosting Collection",
        description="Seasonal campaign system spanning editorial storytelling, launch email, and creator-led social.",
    )

    northstar_launch = ensure_campaign(
        db,
        owner=owner,
        project_id=northstar_project.id,
        name="Cold Brew Focus Launch",
        objective="Drive trial signups for the new cold brew adaptogen line.",
        audience="Busy professionals who want sustained energy without a heavy caffeine crash.",
        campaign_type="product_launch",
        start_date=current_date - timedelta(days=10),
        end_date=current_date + timedelta(days=24),
        status=CampaignStatus.ACTIVE,
    )
    northstar_retention = ensure_campaign(
        db,
        owner=owner,
        project_id=northstar_project.id,
        name="Subscriber Momentum Reset",
        objective="Increase repeat purchase rate from email-driven content moments.",
        audience="Existing subscribers who have purchased once but have not returned in 45 days.",
        campaign_type="retention",
        start_date=current_date - timedelta(days=4),
        end_date=current_date + timedelta(days=18),
        status=CampaignStatus.ACTIVE,
    )
    harbor_launch = ensure_campaign(
        db,
        owner=owner,
        project_id=harbor_project.id,
        name="Patio Hosting Edit",
        objective="Build awareness for the new outdoor collection and drive high-intent traffic to launch assets.",
        audience="Home-focused shoppers planning spring gatherings and seasonal decor refreshes.",
        campaign_type="seasonal_launch",
        start_date=current_date - timedelta(days=6),
        end_date=current_date + timedelta(days=30),
        status=CampaignStatus.ACTIVE,
    )

    ensure_brief(
        db,
        campaign_id=northstar_launch.id,
        key_message="Clear energy, smoother focus, and a ritual people can adopt in one week.",
        call_to_action="Join the early access list.",
        tone="Confident, specific, and grounded in product proof.",
        channels=["LinkedIn", "Instagram", "Email"],
        themes=["focus ritual", "sustained energy", "launch proof"],
        references="Founder notes, customer interviews, and launch positioning deck.",
    )
    ensure_brief(
        db,
        campaign_id=northstar_retention.id,
        key_message="Show existing customers how the habit fits into a normal workday and a realistic routine.",
        call_to_action="Restart your subscription with the subscriber incentive.",
        tone="Helpful, practical, and low-pressure.",
        channels=["Email", "LinkedIn"],
        themes=["habit loop", "repeat use", "customer proof"],
        references="Retention experiment notes and previous win-back email performance.",
    )
    ensure_brief(
        db,
        campaign_id=harbor_launch.id,
        key_message="Make the collection feel like an easy hosting upgrade, not an intimidating styling project.",
        call_to_action="Shop the edit.",
        tone="Warm, elegant, and image-first.",
        channels=["Instagram", "Pinterest", "Email", "Blog"],
        themes=["hosting", "spring reset", "editorial styling"],
        references="Seasonal lookbook, merchandising notes, and UGC shortlist.",
    )

    ensure_template(
        db,
        owner=owner,
        brand_id=northstar.id,
        name="Launch proof post",
        description="Short social post structure for proof-heavy product announcements.",
        template_type="social",
        platform="LinkedIn",
        content_type="organic post",
        body="Hook with the result, give two proof points, then close with one concrete CTA.",
    )
    ensure_template(
        db,
        owner=owner,
        brand_id=northstar.id,
        name="Subscriber reset email",
        description="Nurture email layout for re-engaging customers without sounding desperate.",
        template_type="email",
        platform="Email",
        content_type="newsletter",
        body="Subject, quick context, one customer proof beat, one offer, one CTA.",
    )
    ensure_template(
        db,
        owner=owner,
        brand_id=harbor.id,
        name="Styled collection story",
        description="Editorial frame for seasonal assortment storytelling.",
        template_type="editorial",
        platform="Blog",
        content_type="feature",
        body="Open on atmosphere, move into hero products, end with an easy shopping bridge.",
    )

    linkedin_launch = seed_reviewed_draft(
        db,
        owner=owner,
        reviewer=jordan,
        campaign_id=northstar_launch.id,
        title="Cold brew focus launch teaser",
        platform="LinkedIn",
        content_type="organic post",
        body="The new cold brew ritual is built for clear energy, not a caffeine spike. Three testers swapped their mid-afternoon crash for a simpler focus routine in under a week.",
        planned_publish_at=today + timedelta(days=4),
        final_status="scheduled",
        review_comment="Strong proof section. Tighten the first sentence and keep the CTA singular.",
    )
    retention_email = seed_reviewed_draft(
        db,
        owner=owner,
        reviewer=jordan,
        campaign_id=northstar_retention.id,
        title="Subscriber momentum reset email",
        platform="Email",
        content_type="newsletter",
        body="You do not need a bigger routine. You need one that survives a busy week. Here is how customers are restarting the habit with less friction and a cleaner reward loop.",
        planned_publish_at=today + timedelta(days=2),
        final_status="scheduled",
        review_comment="Use a clearer transition into the offer and make the customer proof easier to skim.",
        rejection_comment="The first version buried the offer. Bring the benefit and the restart incentive higher.",
    )
    reel_script = seed_reviewed_draft(
        db,
        owner=owner,
        reviewer=jordan,
        campaign_id=harbor_launch.id,
        title="Patio hosting reel script",
        platform="Instagram",
        content_type="reel",
        body="Set the scene in one sentence, show the table reset in three shots, then land on the two products that make the whole setup feel effortless.",
        planned_publish_at=today - timedelta(days=1),
        final_status="published",
        review_comment="The motion beats are clean. Keep the product names in the final beat to help save intent.",
    )
    open_linkedin = seed_open_draft(
        db,
        owner=owner,
        campaign_id=northstar_launch.id,
        title="Founder POV on clean focus",
        platform="LinkedIn",
        content_type="thought leadership post",
        body="Most energy products ask people to become different people. This launch is designed to work inside a normal, crowded day.",
        planned_publish_at=today + timedelta(days=6),
        status="draft",
    )
    blog_feature = seed_open_draft(
        db,
        owner=owner,
        campaign_id=harbor_launch.id,
        title="Spring hosting editorial feature",
        platform="Blog",
        content_type="feature article",
        body="Hosting should feel prepared, not performative. This story pairs the new outdoor line with a simple sequence for setting a table that still feels lived in.",
        planned_publish_at=today + timedelta(days=8),
        status="idea",
    )

    ensure_campaign_assignment(
        db,
        actor=owner,
        campaign_id=northstar_launch.id,
        assignee_user_id=maya.id,
        note="Coordinate the launch run sheet and confirm approvals across email + paid social.",
        due_at=today + timedelta(days=1, hours=6),
    )
    ensure_draft_assignment(
        db,
        actor=owner,
        draft_id=linkedin_launch.id,
        assignee_user_id=leo.id,
        assignment_type=AssignmentEntityType.DRAFT,
        note="Polish the proof callout and final CTA framing.",
        due_at=today + timedelta(hours=18),
    )
    ensure_draft_assignment(
        db,
        actor=owner,
        draft_id=retention_email.id,
        assignee_user_id=jordan.id,
        assignment_type=AssignmentEntityType.REVIEW_TASK,
        note="Final review pass after the restart-offer revision.",
        due_at=today + timedelta(hours=10),
    )
    ensure_draft_assignment(
        db,
        actor=maya,
        draft_id=open_linkedin.id,
        assignee_user_id=owner.id,
        assignment_type=AssignmentEntityType.DRAFT,
        note="Take this from POV draft to review-ready post before the founder call tomorrow.",
        due_at=today + timedelta(hours=16),
    )

    notify_users(
        db,
        user_ids=[owner.id],
        brand_id=harbor.id,
        notification_type=NotificationType.MENTION,
        title="Seasonal creative cue",
        body="Maya flagged the hosting reel as a strong reference for the blog feature narrative.",
        entity_type="campaign",
        entity_id=harbor_launch.id,
        actor_user_id=maya.id,
        metadata={"campaign_id": harbor_launch.id},
    )
    db.commit()

    summary = {
        "brands": db.scalar(
            select(func.count(Brand.id))
            .join(BrandMembership)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "projects": db.scalar(
            select(func.count(Project.id))
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "campaigns": db.scalar(
            select(func.count(Campaign.id))
            .join(Project, Project.id == Campaign.project_id)
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "drafts": db.scalar(
            select(func.count(ContentDraft.id))
            .join(Campaign, Campaign.id == ContentDraft.campaign_id)
            .join(Project, Project.id == Campaign.project_id)
            .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
        "subscriptions": db.scalar(
            select(func.count(BrandSubscription.id))
            .join(Brand, Brand.id == BrandSubscription.brand_id)
            .join(BrandMembership, BrandMembership.brand_id == Brand.id)
            .where(
                BrandMembership.user_id == owner.id,
                BrandMembership.status == MembershipStatus.ACTIVE,
            )
        ) or 0,
    }
    print(f"Seeded workspace for {owner.email}")
    for key, value in summary.items():
        print(f"{key}: {value}")


def main() -> None:
    parser = ArgumentParser(description="Seed a realistic demo workspace for a specific user.")
    parser.add_argument("--email", required=True, help="Existing user email that should receive the demo workspace.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_workspace(db, email=args.email.strip().lower())
    finally:
        db.close()


if __name__ == "__main__":
    main()
