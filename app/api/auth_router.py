from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import PERSONAS, ISSUE_TYPES, STATUS_LIFECYCLE, URGENCY_LEVELS
from app.database.session import get_db
from app.models.all_models import User, Campus
from app.schemas.schemas import UserCreate, UserLogin, UserOut, Token, MetaOut
from app.auth.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Canonical persona roles and accepted legacy aliases.
ALLOWED_ROLES = ["student", "faculty", "facilities", "admin"]
ROLE_EMAIL_MAP = {p["role"]: p["email"] for p in PERSONAS}
LEGACY_ROLE_EMAIL_MAP = {
    "facility_worker": "marcus.worker@greenfield.edu",
    "super_admin": "sarah.admin@greenfield.edu",
}

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists."
        )
    
    # Verify campus
    campus = db.query(Campus).filter(Campus.id == user_in.campus_id).first()
    if not campus:
        campus = db.query(Campus).first()

    canonical_role = user_in.role if user_in.role in ALLOWED_ROLES else "student"
    db_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=canonical_role,
        campus_id=campus.id if campus else None,
        impact_score=10
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    token = create_access_token({"sub": db_user.email, "role": db_user.role, "id": db_user.id})
    return Token(access_token=token, user=UserOut.model_validate(db_user))

@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    token = create_access_token({"sub": user.email, "role": user.role, "id": user.id})
    return Token(access_token=token, user=UserOut.model_validate(user))

@router.get("/personas")
def list_personas():
    """Public metadata for the Demo Mode persona selector (no credentials exposed)."""
    return [
        {
            "role": p["role"],
            "label": p["label"],
            "description": p["description"],
            "capabilities": p["capabilities"],
        }
        for p in PERSONAS
    ]

@router.get("/meta", response_model=MetaOut)
def get_meta():
    """Public metadata: issue types, status lifecycle, and urgency levels for forms/filters."""
    return MetaOut(
        issue_types=ISSUE_TYPES,
        statuses=[{"key": s["key"], "label": s["label"]} for s in STATUS_LIFECYCLE],
        urgency_levels=URGENCY_LEVELS
    )

@router.get("/users")
def list_users(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List users (e.g. facilities staff) for assignment dropdowns."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.all()
    return [{"id": u.id, "name": u.name, "role": u.role, "email": u.email} for u in users]

@router.post("/demo-login/{role}", response_model=Token)
def demo_login(role: str, db: Session = Depends(get_db)):
    """Passwordless 1-Click login for DEMO personas only — explicitly a demo experience."""
    normalized = "facilities" if role.lower() == "facility_worker" else ("admin" if role.lower() == "super_admin" else role.lower())
    target_email = ROLE_EMAIL_MAP.get(normalized) or LEGACY_ROLE_EMAIL_MAP.get(role.lower(), "alex.student@greenfield.edu")
    user = db.query(User).filter(User.email == target_email).first()
    
    if not user:
        user = db.query(User).filter(User.role == normalized).first()
    if not user:
        user = db.query(User).first()

    if not user:
        raise HTTPException(status_code=404, detail="Demo user not found. Please seed the database.")

    token = create_access_token({"sub": user.email, "role": user.role, "id": user.id})
    return Token(access_token=token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
