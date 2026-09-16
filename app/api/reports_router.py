import os
import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.all_models import User, Campus, Report, ReportImage, Assignment, Resolution, Verification, Notification
from app.schemas.schemas import (
    ReportOut, ReportDetail, ReportCreate, ReportStatusUpdate,
    ReportAssign, ReportResolve, ReportVerify
)
from app.auth.security import get_current_user, require_role

router = APIRouter(prefix="/reports", tags=["Reports"])

# Valid status transitions for the report lifecycle
VALID_STATUS_TRANSITIONS = {
    "submitted": {"acknowledged"},
    "acknowledged": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"verified", "in_progress"},  # verified or reopened
    "verified": set(),  # terminal state
}

VALID_REPORT_STATUSES = {"submitted", "acknowledged", "assigned", "in_progress", "resolved", "verified"}

ALLOWED_UPLOAD_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def generate_report_code(db: Session) -> str:
    """Generate a collision-safe report code using UUID randomness."""
    year = datetime.datetime.now(datetime.timezone.utc).year
    random_part = uuid.uuid4().hex[:6].upper()
    return f"CVA-{year}-{random_part}"


@router.get("", response_model=List[ReportOut])
def get_reports(
    status: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    urgency: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
    worker_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: str = "newest",
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(Report)

    if status:
        if status not in VALID_REPORT_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status filter. Valid: {sorted(VALID_REPORT_STATUSES)}")
        query = query.filter(Report.status == status)
    if category:
        query = query.filter(Report.category == category)
    if urgency:
        if urgency not in {"low", "medium", "high", "critical"}:
            raise HTTPException(status_code=400, detail="Invalid urgency filter. Valid: low, medium, high, critical")
        query = query.filter(Report.severity == urgency)
    if location:
        query = query.filter(Report.building.ilike(f"%{location}%"))
    if search:
        query = query.filter(
            (Report.description.ilike(f"%{search}%")) |
            (Report.building.ilike(f"%{search}%")) |
            (Report.category.ilike(f"%{search}%")) |
            (Report.report_code.ilike(f"%{search}%"))
        )
    if user_id:
        query = query.filter(Report.user_id == user_id)
    if worker_id:
        query = query.join(Assignment).filter(Assignment.worker_id == worker_id)
    if date_from:
        try:
            df = datetime.datetime.fromisoformat(date_from)
            query = query.filter(Report.created_at >= df)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_from format. Use ISO 8601 (e.g. 2026-01-01).")
    if date_to:
        try:
            dt = datetime.datetime.fromisoformat(date_to)
            query = query.filter(Report.created_at <= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_to format. Use ISO 8601 (e.g. 2026-12-31).")

    if sort == "oldest":
        query = query.order_by(Report.created_at.asc())
    else:
        query = query.order_by(Report.created_at.desc())

    reports = query.offset(skip).limit(limit).all()

    result = []
    for r in reports:
        out = ReportOut.model_validate(r)
        out.reporter_name = r.reporter.name if r.reporter else "Anonymous Reporter"
        result.append(out)
    return result


@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Authenticated file upload with MIME validation and size enforcement."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Validate MIME type from content-type header
    if file.content_type not in ALLOWED_UPLOAD_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_MIMES))}"
        )

    # Read and validate size before any processing
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds maximum allowed size (10MB).")

    # Validate actual file content by checking magic bytes
    header = contents[:8] if len(contents) >= 8 else contents
    is_valid_image = False
    if header[:2] == b'\xff\xd8':  # JPEG
        is_valid_image = True
        ext = ".jpg"
    elif header[:4] == b'\x89PNG':  # PNG
        is_valid_image = True
        ext = ".png"
    elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':  # WebP
        is_valid_image = True
        ext = ".webp"
    elif header[:3] == b'GIF':  # GIF
        is_valid_image = True
        ext = ".gif"

    if not is_valid_image:
        raise HTTPException(status_code=400, detail="File content does not match a supported image format.")

    # Generate server-side filename (never use user-controlled filename)
    filename = f"cva_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    return {"image_url": f"/uploads/{filename}"}


@router.post("", response_model=ReportOut)
def create_report(
    report_in: ReportCreate,
    image_urls: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if report_in.severity not in {"low", "medium", "high", "critical"}:
        raise HTTPException(status_code=400, detail="Invalid severity. Valid: low, medium, high, critical")

    code = generate_report_code(db)

    campus = db.query(Campus).filter(Campus.id == report_in.campus_id).first()
    if not campus:
        campus = db.query(Campus).first()

    db_report = Report(
        report_code=code,
        user_id=current_user.id,
        campus_id=campus.id if campus else 1,
        category=report_in.category,
        description=report_in.description,
        additional_info=report_in.additional_info,
        building=report_in.building,
        latitude=report_in.latitude,
        longitude=report_in.longitude,
        severity=report_in.severity,
        status="submitted"
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    # Attach images if provided
    if image_urls:
        for url in image_urls:
            img = ReportImage(report_id=db_report.id, image_url=url, image_type="evidence")
            db.add(img)
    else:
        cat_key = report_in.category.lower().replace(" ", "_")
        default_photo = settings.DEMO_PHOTOGRAPHY.get(cat_key, settings.DEMO_PHOTOGRAPHY["overflowing_bin"])
        img = ReportImage(report_id=db_report.id, image_url=default_photo, image_type="evidence")
        db.add(img)

    current_user.impact_score += 5

    notif = Notification(
        user_id=current_user.id,
        title="Report Submitted Successfully",
        message=f"Your issue report {code} for '{report_in.category}' has been logged and queued for review."
    )
    db.add(notif)
    db.commit()
    db.refresh(db_report)

    out = ReportOut.model_validate(db_report)
    out.reporter_name = current_user.name
    return out


@router.get("/{report_id}", response_model=ReportDetail)
def get_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Authorization: students can only view their own reports
    if current_user.role == "student" and report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own reports.")

    out = ReportDetail.model_validate(report)
    out.reporter_name = report.reporter.name if report.reporter else "Anonymous Reporter"

    # Populate worker names in assignments and resolutions
    for a in out.assignments:
        w = db.query(User).filter(User.id == a.worker_id).first()
        if w:
            a.worker_name = w.name

    for r in out.resolutions:
        w = db.query(User).filter(User.id == r.worker_id).first()
        if w:
            r.worker_name = w.name

    return out


@router.post("/{report_id}/acknowledge", response_model=ReportOut)
def acknowledge_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "facilities"]))
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status not in VALID_STATUS_TRANSITIONS.get(report.status, set()) and report.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is '{report.status}' and cannot be acknowledged."
        )
    if report.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is '{report.status}' and cannot be acknowledged. Must be 'submitted'."
        )

    report.status = "acknowledged"
    report.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(report)

    out = ReportOut.model_validate(report)
    out.reporter_name = report.reporter.name if report.reporter else "Reporter"
    return out


@router.patch("/{report_id}/status", response_model=ReportOut)
def update_report_status(
    report_id: int,
    status_in: ReportStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "facilities"]))
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    new_status = status_in.status
    if new_status not in VALID_REPORT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{new_status}'. Valid: {sorted(VALID_REPORT_STATUSES)}"
        )

    allowed_transitions = VALID_STATUS_TRANSITIONS.get(report.status, set())
    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{report.status}' to '{new_status}'. "
                   f"Allowed: {sorted(allowed_transitions) if allowed_transitions else 'none (terminal state)'}"
        )

    report.status = new_status
    report.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(report)

    out = ReportOut.model_validate(report)
    out.reporter_name = report.reporter.name if report.reporter else "Reporter"
    return out


@router.post("/{report_id}/assign", response_model=ReportDetail)
def assign_report(
    report_id: int,
    assign_in: ReportAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "facilities"]))
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status not in ("acknowledged", "assigned", "in_progress"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign report in '{report.status}' status. Must be acknowledged, assigned, or in_progress."
        )

    worker = db.query(User).filter(User.id == assign_in.worker_id, User.role == "facilities").first()
    if not worker:
        worker = db.query(User).filter(User.role == "facilities").first()

    if not worker:
        raise HTTPException(status_code=400, detail="No facility worker available for assignment.")

    assignment = Assignment(
        report_id=report.id,
        worker_id=worker.id,
        notes=assign_in.notes or "Dispatched by administrator"
    )
    db.add(assignment)

    report.status = "assigned"
    report.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.add(Notification(
        user_id=worker.id,
        title="New Cleanup Assignment",
        message=f"You have been assigned to resolve issue report {report.report_code} at {report.building}."
    ))

    db.commit()
    return get_report_detail(report_id, db, current_user)


@router.post("/{report_id}/resolve", response_model=ReportDetail)
def resolve_report(
    report_id: int,
    resolve_in: ReportResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["facilities", "admin"]))
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status not in ("assigned", "in_progress"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resolve report in '{report.status}' status. Must be assigned or in_progress."
        )

    after_photo = resolve_in.after_image_url or settings.DEMO_PHOTOGRAPHY["after_clean"]

    resolution = Resolution(
        report_id=report.id,
        worker_id=current_user.id,
        before_image=report.images[0].image_url if report.images else settings.DEMO_PHOTOGRAPHY["overflowing_bin"],
        after_image=after_photo,
        resolution_notes=resolve_in.resolution_notes
    )
    db.add(resolution)

    db.add(ReportImage(
        report_id=report.id,
        image_url=after_photo,
        image_type="after"
    ))

    report.status = "resolved"
    report.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.add(Notification(
        user_id=report.user_id,
        title="Issue Marked Resolved",
        message=f"Facility team marked your report {report.report_code} at {report.building} as resolved. Please verify the cleanup!"
    ))

    db.commit()
    return get_report_detail(report_id, db, current_user)


@router.post("/{report_id}/verify", response_model=ReportDetail)
def verify_report(
    report_id: int,
    verify_in: ReportVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != "resolved":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot verify report in '{report.status}' status. Must be 'resolved'."
        )

    # Only the original reporter can verify
    if report.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the original reporter can verify resolution."
        )

    verification = Verification(
        report_id=report.id,
        user_id=current_user.id,
        verified=verify_in.verified,
        feedback=verify_in.feedback
    )
    db.add(verification)

    if verify_in.verified:
        report.status = "verified"
        current_user.impact_score += 10
        db.add(Notification(
            user_id=current_user.id,
            title="Verification Complete!",
            message=f"Thank you for confirming resolution of {report.report_code}! You earned +10 Impact Score points."
        ))
    else:
        report.status = "in_progress"
        admins = db.query(User).filter(User.role.in_(["admin", "facilities"])).all()
        for adm in admins:
            db.add(Notification(
                user_id=adm.id,
                title="Resolution Rejected by Reporter",
                message=f"Reporter rejected resolution for {report.report_code} at {report.building}: '{verify_in.feedback or 'Problem still persists'}'"
            ))

    report.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    return get_report_detail(report_id, db, current_user)
