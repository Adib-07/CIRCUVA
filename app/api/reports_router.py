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

def generate_report_code(db: Session) -> str:
    count = db.query(Report).count() + 1
    random_suffix = str(count).zfill(6)
    year = datetime.datetime.now().year
    return f"CVA-{year}-{random_suffix}"

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
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    query = db.query(Report)

    if status:
        query = query.filter(Report.status == status)
    if category:
        query = query.filter(Report.category == category)
    if urgency:
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
            pass
    if date_to:
        try:
            dt = datetime.datetime.fromisoformat(date_to)
            query = query.filter(Report.created_at <= dt)
        except ValueError:
            pass

    if sort == "oldest":
        query = query.order_by(Report.created_at.asc())
    else:
        query = query.order_by(Report.created_at.desc())

    reports = query.offset(skip).limit(limit).all()

    # Format reporter name into model output
    result = []
    for r in reports:
        out = ReportOut.model_validate(r)
        out.reporter_name = r.reporter.name if r.reporter else "Anonymous Reporter"
        result.append(out)
    return result

@router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    """File upload endpoint saving files to /uploads and returning accessible URL"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        ext = ".jpg" # fallback extension

    filename = f"cva_{uuid.uuid4().hex[:10]}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds maximum allowed size (10MB).")

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
        # Default category image from config registry if no image uploaded
        cat_key = report_in.category.lower().replace(" ", "_")
        default_photo = settings.DEMO_PHOTOGRAPHY.get(cat_key, settings.DEMO_PHOTOGRAPHY["overflowing_bin"])
        img = ReportImage(report_id=db_report.id, image_url=default_photo, image_type="evidence")
        db.add(img)

    # Update user impact score (+5 for reporting)
    current_user.impact_score += 5
    
    # Send notification to user
    notif = Notification(
        user_id=current_user.id,
        title="Report Submitted Successfully",
        message=f"Your waste report {code} for '{report_in.category}' has been logged and queued for review."
    )
    db.add(notif)
    db.commit()
    db.refresh(db_report)

    out = ReportOut.model_validate(db_report)
    out.reporter_name = current_user.name
    return out

@router.get("/{report_id}", response_model=ReportDetail)
def get_report_detail(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    out = ReportDetail.model_validate(report)
    out.reporter_name = report.reporter.name if report.reporter else "Anonymous Student"
    
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

    if report.status not in ("submitted",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is already '{report.status}' and cannot be acknowledged again."
        )

    report.status = "acknowledged"
    report.updated_at = datetime.datetime.utcnow()
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
    
    report.status = status_in.status
    report.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(report)

    out = ReportOut.model_validate(report)
    out.reporter_name = report.reporter.name if report.reporter else "Student"
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
    
    worker = db.query(User).filter(User.id == assign_in.worker_id, User.role == "facilities").first()
    if not worker:
        # Fallback to any facility worker if specific ID not found
        worker = db.query(User).filter(User.role == "facilities").first()

    assignment = Assignment(
        report_id=report.id,
        worker_id=worker.id if worker else current_user.id,
        notes=assign_in.notes or "Dispatched by administrator"
    )
    db.add(assignment)
    
    report.status = "assigned"
    report.updated_at = datetime.datetime.utcnow()
    
    # Send notification to facility worker
    if worker:
        db.add(Notification(
            user_id=worker.id,
            title="New Cleanup Assignment",
            message=f"You have been assigned to resolve waste report {report.report_code} at {report.building}."
        ))

    db.commit()
    return get_report_detail(report_id, db)

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

    after_photo = resolve_in.after_image_url or settings.DEMO_PHOTOGRAPHY["after_clean"]

    resolution = Resolution(
        report_id=report.id,
        worker_id=current_user.id,
        before_image=report.images[0].image_url if report.images else settings.DEMO_PHOTOGRAPHY["overflowing_bin"],
        after_image=after_photo,
        resolution_notes=resolve_in.resolution_notes
    )
    db.add(resolution)
    
    # Save image to report images
    db.add(ReportImage(
        report_id=report.id,
        image_url=after_photo,
        image_type="after"
    ))

    report.status = "resolved"
    report.updated_at = datetime.datetime.utcnow()

    # Notify original reporter to verify
    db.add(Notification(
        user_id=report.user_id,
        title="Issue Marked Resolved",
        message=f"Facility team marked your report {report.report_code} at {report.building} as resolved. Please verify the cleanup!"
    ))

    db.commit()
    return get_report_detail(report_id, db)

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
        # Reopen report if user says not resolved
        report.status = "in_progress"
        # Notify admins
        admins = db.query(User).filter(User.role.in_(["admin", "facilities"])).all()
        for adm in admins:
            db.add(Notification(
                user_id=adm.id,
                title="Resolution Rejected by Reporter",
                message=f"Reporter rejected resolution for {report.report_code} at {report.building}: '{verify_in.feedback or 'Problem still persists'}'"
            ))

    report.updated_at = datetime.datetime.utcnow()
    db.commit()
    return get_report_detail(report_id, db)
