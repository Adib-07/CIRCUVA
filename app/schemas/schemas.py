from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "student"
    campus_id: Optional[int] = 1

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    impact_score: int = 10
    created_at: datetime

# Campus Schemas
class CampusBase(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    organization: str

class CampusCreate(CampusBase):
    pass

class CampusOut(CampusBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

# Report Image Schema
class ReportImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    image_type: str
    created_at: datetime

# Assignment Schema
class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_id: int
    worker_name: Optional[str] = None
    notes: Optional[str] = None
    assigned_at: datetime
    completed_at: Optional[datetime] = None

# Resolution Schema
class ResolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_id: int
    worker_name: Optional[str] = None
    before_image: Optional[str] = None
    after_image: str
    resolution_notes: str
    resolved_at: datetime

# Verification Schema
class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    verified: bool
    feedback: Optional[str] = None
    created_at: datetime

# Report Schemas
class ReportCreate(BaseModel):
    category: str
    description: str
    building: str
    latitude: float
    longitude: float
    severity: str = "medium"
    additional_info: Optional[str] = None
    campus_id: int = 1

class ReportStatusUpdate(BaseModel):
    status: str

class ReportAssign(BaseModel):
    worker_id: int
    notes: Optional[str] = "Dispatched clean-up task to facility team"

class ReportResolve(BaseModel):
    resolution_notes: str
    after_image_url: Optional[str] = None

class ReportVerify(BaseModel):
    verified: bool
    feedback: Optional[str] = None

class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_code: str
    user_id: int
    campus_id: int
    category: str
    description: str
    additional_info: Optional[str] = None
    building: str
    latitude: float
    longitude: float
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    reporter_name: Optional[str] = None
    images: List[ReportImageOut] = []

class ReportDetail(ReportOut):
    assignments: List[AssignmentOut] = []
    resolutions: List[ResolutionOut] = []
    verifications: List[VerificationOut] = []

# Notification Schema
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    read: bool
    created_at: datetime

# Analytics & Dashboard Schemas
class StatusCount(BaseModel):
    key: str
    label: str
    count: int

class TrendPoint(BaseModel):
    date: str
    reported: int
    resolved: int

class AnalyticsOverview(BaseModel):
    total_reports: int
    active_reports: int
    resolved_reports: int
    critical_reports: int
    avg_response_hours: float
    resolution_rate_pct: float
    weekly_new_reports: int
    total_impact_score: int = 0
    user_impact_score: int = 0
    by_status: List[StatusCount] = []
    by_category: dict = {}
    by_urgency: dict = {}
    trend: List[TrendPoint] = []

class HotspotOut(BaseModel):
    building: str
    report_count: int
    issue_types: List[str] = []
    resolution_rate_pct: float = 0.0
    last_report_at: Optional[datetime] = None
    latest_status: Optional[str] = None

class ActivityOut(BaseModel):
    id: int
    report_code: str
    type: str
    message: str
    timestamp: datetime
    severity: str
    status: str

class MetaOut(BaseModel):
    issue_types: List[str]
    statuses: List[dict]
    urgency_levels: List[str]
