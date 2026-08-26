import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="student", nullable=False) # student, faculty, facilities, admin
    campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=True)
    impact_score = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    campus = relationship("Campus", back_populates="users")
    reports = relationship("Report", back_populates="reporter")
    assignments = relationship("Assignment", back_populates="worker")
    verifications = relationship("Verification", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class Campus(Base):
    __tablename__ = "campuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    address = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    organization = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="campus")
    reports = relationship("Report", back_populates="campus")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_code = Column(String(50), unique=True, index=True, nullable=False) # CVA-2026-XXXXXX
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=False)
    category = Column(String(100), nullable=False) # Overflowing Bin, Recycling Contamination, Illegal Dumping, Litter Hotspot, Damaged Waste Infrastructure, Missed Collection, Other
    description = Column(Text, nullable=False)
    additional_info = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    building = Column(String(150), nullable=False)
    severity = Column(String(20), default="medium", nullable=False) # low, medium, high, critical
    status = Column(String(30), default="submitted", nullable=False) # submitted, acknowledged, assigned, in_progress, resolved, verified
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    reporter = relationship("User", back_populates="reports")
    campus = relationship("Campus", back_populates="reports")
    images = relationship("ReportImage", back_populates="report", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="report", cascade="all, delete-orphan")
    resolutions = relationship("Resolution", back_populates="report", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="report", cascade="all, delete-orphan")

class ReportImage(Base):
    __tablename__ = "report_images"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    image_type = Column(String(50), default="evidence") # evidence, before, after
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("Report", back_populates="images")

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    report = relationship("Report", back_populates="assignments")
    worker = relationship("User", back_populates="assignments")

class Resolution(Base):
    __tablename__ = "resolutions"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    before_image = Column(String(500), nullable=True)
    after_image = Column(String(500), nullable=False)
    resolution_notes = Column(Text, nullable=False)
    resolved_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("Report", back_populates="resolutions")

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified = Column(Boolean, nullable=False) # True = fixed, False = reopened
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("Report", back_populates="verifications")
    user = relationship("User", back_populates="verifications")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")
