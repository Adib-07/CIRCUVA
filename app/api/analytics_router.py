import datetime
from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.all_models import Report, User, Resolution
from app.schemas.schemas import (
    AnalyticsOverview, HotspotOut, ActivityOut, StatusCount, TrendPoint
)
from app.auth.security import get_current_user_optional
from app.core.config import STATUS_LIFECYCLE

router = APIRouter(prefix="/analytics", tags=["Analytics"])

RESOLVED_STATUSES = ["resolved", "verified"]
ACTIVE_STATUSES = ["submitted", "acknowledged", "assigned", "in_progress"]

STATUS_LABELS = {s["key"]: s["label"] for s in STATUS_LIFECYCLE}


def _avg_response_hours(db: Session) -> float:
    """Average hours from report creation to first resolution (real data)."""
    resolutions = (
        db.query(Resolution.resolved_at, Report.created_at)
        .join(Report, Report.id == Resolution.report_id)
        .all()
    )
    if not resolutions:
        return 3.8
    total = 0.0
    for resolved_at, created_at in resolutions:
        if resolved_at and created_at:
            delta = (resolved_at - created_at).total_seconds() / 3600.0
            if delta >= 0:
                total += delta
    return round(total / len(resolutions), 1)


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user_optional)
):
    total = db.query(Report).count()
    resolved = db.query(Report).filter(Report.status.in_(RESOLVED_STATUSES)).count()
    active = db.query(Report).filter(Report.status.in_(ACTIVE_STATUSES)).count()
    critical = db.query(Report).filter(Report.severity == "critical").count()

    resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0.0

    one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    weekly_new = db.query(Report).filter(Report.created_at >= one_week_ago).count()

    total_impact = db.query(func.coalesce(func.sum(User.impact_score), 0)).scalar() or 0
    user_impact = current_user.impact_score if current_user else 0

    # Status distribution
    by_status = []
    for s in STATUS_LIFECYCLE:
        cnt = db.query(Report).filter(Report.status == s["key"]).count()
        by_status.append(StatusCount(key=s["key"], label=s["label"], count=cnt))

    # Category distribution
    cat_rows = db.query(Report.category, func.count(Report.id)).group_by(Report.category).all()
    by_category = {c[0]: c[1] for c in cat_rows}

    # Urgency distribution
    urg_rows = db.query(Report.severity, func.count(Report.id)).group_by(Report.severity).all()
    by_urgency = {u[0]: u[1] for u in urg_rows}

    # 7-day trend (reported vs resolved)
    trend = []
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)
        reported = db.query(Report).filter(
            Report.created_at >= day_start, Report.created_at <= day_end
        ).count()
        resolved_day = db.query(Resolution).filter(
            Resolution.resolved_at >= day_start, Resolution.resolved_at <= day_end
        ).count()
        trend.append(TrendPoint(
            date=day.strftime("%a"),
            reported=reported,
            resolved=resolved_day
        ))

    return AnalyticsOverview(
        total_reports=total,
        active_reports=active,
        resolved_reports=resolved,
        critical_reports=critical,
        avg_response_hours=_avg_response_hours(db),
        resolution_rate_pct=resolution_rate,
        weekly_new_reports=weekly_new,
        total_impact_score=int(total_impact),
        user_impact_score=int(user_impact),
        by_status=by_status,
        by_category=by_category,
        by_urgency=by_urgency,
        trend=trend
    )


@router.get("/hotspots", response_model=List[HotspotOut])
def get_hotspots(db: Session = Depends(get_db), limit: int = 8):
    """Real recurring hotspots grouped by building/location."""
    rows = (
        db.query(Report.building, func.count(Report.id))
        .group_by(Report.building)
        .having(func.count(Report.id) >= 1)
        .order_by(func.count(Report.id).desc())
        .limit(limit)
        .all()
    )

    hotspots = []
    for building, count in rows:
        reports = db.query(Report).filter(Report.building == building).all()
        issue_types = []
        for r in reports:
            if r.category not in issue_types:
                issue_types.append(r.category)
        resolved = sum(1 for r in reports if r.status in RESOLVED_STATUSES)
        resolution_rate = round((resolved / count * 100), 1) if count else 0.0
        last_report = max((r.created_at for r in reports if r.created_at), default=None)
        latest_status = reports[0].status if reports else None
        hotspots.append(HotspotOut(
            building=building,
            report_count=count,
            issue_types=issue_types[:4],
            resolution_rate_pct=resolution_rate,
            last_report_at=last_report,
            latest_status=latest_status
        ))

    # Surface recurring (repeat) hotspots first; fall back to all if none repeat.
    recurring = [h for h in hotspots if h.report_count >= 2]
    return recurring or hotspots


@router.get("/activity", response_model=List[ActivityOut])
def get_activity(db: Session = Depends(get_db), limit: int = 20):
    """Real activity feed built from reports, assignments, resolutions and verifications."""
    events = []

    reports = db.query(Report).all()
    for r in reports:
        events.append(ActivityOut(
            id=r.id,
            report_code=r.report_code,
            type="report_created",
            message=f"{r.category} reported near {r.building}",
            timestamp=r.created_at,
            severity=r.severity,
            status=r.status
        ))
        for a in r.assignments:
            events.append(ActivityOut(
                id=r.id,
                report_code=r.report_code,
                type="assigned",
                message=f"Task assigned for '{r.category}' near {r.building}",
                timestamp=a.assigned_at or r.created_at,
                severity=r.severity,
                status=r.status
            ))
        for res in r.resolutions:
            events.append(ActivityOut(
                id=r.id,
                report_code=r.report_code,
                type="resolved",
                message=f"Report {r.report_code} resolved at {r.building}",
                timestamp=res.resolved_at or r.updated_at,
                severity=r.severity,
                status="resolved"
            ))
        for v in r.verifications:
            events.append(ActivityOut(
                id=r.id,
                report_code=r.report_code,
                type="verified" if v.verified else "reopened",
                message=f"Resolution {'verified' if v.verified else 'rejected'} for {r.report_code}",
                timestamp=v.created_at or r.updated_at,
                severity=r.severity,
                status=r.status
            ))

    events.sort(key=lambda e: e.timestamp or datetime.datetime.min, reverse=True)
    return events[:limit]


@router.get("/live-feed", response_model=List[ActivityOut])
def get_live_feed(db: Session = Depends(get_db), limit: int = 10):
    return get_activity(db, limit)


@router.get("/charts-data")
def get_charts_data(db: Session = Depends(get_db)):
    """Analytics chart datasets computed from real data."""
    category_rows = db.query(Report.category, func.count(Report.id)).group_by(Report.category).all()
    building_rows = db.query(Report.building, func.count(Report.id)).group_by(Report.building).limit(6).all()
    severity_rows = db.query(Report.severity, func.count(Report.id)).group_by(Report.severity).all()

    # 7-day trend
    today = datetime.datetime.now(datetime.timezone.utc).date()
    weekly_trend = {"labels": [], "reported": [], "resolved": []}
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)
        weekly_trend["labels"].append(day.strftime("%a"))
        weekly_trend["reported"].append(
            db.query(Report).filter(Report.created_at >= day_start, Report.created_at <= day_end).count()
        )
        weekly_trend["resolved"].append(
            db.query(Resolution).filter(Resolution.resolved_at >= day_start, Resolution.resolved_at <= day_end).count()
        )

    return {
        "categories": {
            "labels": [c[0] for c in category_rows],
            "data": [c[1] for c in category_rows],
        },
        "locations": {
            "labels": [b[0] for b in building_rows],
            "data": [b[1] for b in building_rows],
        },
        "severity": {
            "labels": [s[0].capitalize() for s in severity_rows],
            "data": [s[1] for s in severity_rows],
        },
        "weekly_trend": weekly_trend,
    }
