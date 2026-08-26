import datetime
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine, Base
from app.models.all_models import User, Campus, Report, ReportImage, Assignment, Resolution, Verification, Notification
from app.auth.security import hash_password
from app.core.config import settings

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Campus).filter(Campus.name == "Greenfield University — Demo Campus").first():
            print("Database already contains demo seed data.")
            return

        print("Seeding database with Greenfield University demo data...")

        # 1. Create Demo Campus
        campus = Campus(
            name="Greenfield University — Demo Campus",
            address="100 University Heights Parkway, Cambridge, MA",
            latitude=42.3601,
            longitude=-71.0942,
            organization="Greenfield Educational Trust"
        )
        db.add(campus)
        db.commit()
        db.refresh(campus)

        # 2. Create Users
        password_hash = hash_password("Password123!")

        student = User(
            name="Alex Rivera",
            email="alex.student@greenfield.edu",
            password_hash=password_hash,
            role="student",
            campus_id=campus.id,
            impact_score=45
        )
        worker1 = User(
            name="Marcus Vance",
            email="marcus.worker@greenfield.edu",
            password_hash=password_hash,
            role="facilities",
            campus_id=campus.id,
            impact_score=120
        )
        worker2 = User(
            name="Elena Rostova",
            email="elena.worker@greenfield.edu",
            password_hash=password_hash,
            role="facilities",
            campus_id=campus.id,
            impact_score=95
        )
        faculty = User(
            name="Dr. Priya Nair",
            email="priya.faculty@greenfield.edu",
            password_hash=password_hash,
            role="faculty",
            campus_id=campus.id,
            impact_score=80
        )
        admin = User(
            name="Dr. Sarah Jenkins",
            email="sarah.admin@greenfield.edu",
            password_hash=password_hash,
            role="admin",
            campus_id=campus.id,
            impact_score=250
        )

        db.add_all([student, worker1, worker2, faculty, admin])
        db.commit()
        db.refresh(student)
        db.refresh(worker1)
        db.refresh(worker2)
        db.refresh(faculty)
        db.refresh(admin)

        # 3. Create Sample Reports (full lifecycle + repeated locations for real hotspots)
        now = datetime.datetime.utcnow()
        reports_data = [
            {
                "code": "CVA-2026-004821", "category": "Overflowing Bin",
                "description": "Main waste receptacle overflowing into patio dining area near student cafeteria north entrance.",
                "building": "Student Cafeteria — North Entrance", "severity": "high", "status": "in_progress",
                "lat": 42.3608, "lng": -71.0938, "reporter": student, "assigned_to": worker1,
                "photo": settings.DEMO_PHOTOGRAPHY["overflowing_bin"], "days_ago": 1, "resp_hours": 5
            },
            {
                "code": "CVA-2026-004822", "category": "Litter Hotspot",
                "description": "Accumulation of plastic cups and food wrappers scattered across the outdoor study benches.",
                "building": "Engineering Block B Quad", "severity": "medium", "status": "resolved",
                "lat": 42.3595, "lng": -71.0950, "reporter": student, "assigned_to": worker1,
                "photo": settings.DEMO_PHOTOGRAPHY["litter_outdoor"], "after_photo": settings.DEMO_PHOTOGRAPHY["after_clean"],
                "days_ago": 3, "resp_hours": 8
            },
            {
                "code": "CVA-2026-004823", "category": "Food Waste",
                "description": "Unattended catering trays and leftover food container pileup attracting sanitation hazards.",
                "building": "Student Center Terrace", "severity": "critical", "status": "submitted",
                "lat": 42.3612, "lng": -71.0932, "reporter": student,
                "photo": settings.DEMO_PHOTOGRAPHY["food_waste"], "days_ago": 0, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004824", "category": "Damaged Waste Infrastructure",
                "description": "Old monitors, discarded server racks, and broken cable bundles left uncollected in basement corridor.",
                "building": "Science Complex Basement", "severity": "high", "status": "verified",
                "lat": 42.3588, "lng": -71.0961, "reporter": student, "assigned_to": worker2,
                "photo": settings.DEMO_PHOTOGRAPHY["e_waste"], "after_photo": settings.DEMO_PHOTOGRAPHY["after_clean"],
                "days_ago": 6, "resp_hours": 26
            },
            {
                "code": "CVA-2026-004825", "category": "Damaged Waste Infrastructure",
                "description": "Hinge broken on compost segregation container; lid stuck wide open in heavy wind.",
                "building": "Main Library East Lawn", "severity": "low", "status": "assigned",
                "lat": 42.3603, "lng": -71.0925, "reporter": student, "assigned_to": worker2,
                "photo": settings.DEMO_PHOTOGRAPHY["waste_bins"], "days_ago": 2, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004826", "category": "Recycling Contamination",
                "description": "Non-recyclable trash dumped directly into dedicated blue paper recycling bin.",
                "building": "Hostel B Courtyard", "severity": "medium", "status": "resolved",
                "lat": 42.3620, "lng": -71.0945, "reporter": student, "assigned_to": worker1,
                "photo": settings.DEMO_PHOTOGRAPHY["recycling_station"], "after_photo": settings.DEMO_PHOTOGRAPHY["after_clean"],
                "days_ago": 4, "resp_hours": 12
            },
            {
                "code": "CVA-2026-004827", "category": "Litter Hotspot",
                "description": "Windblown paper flyers and empty water bottles scattered along the spectator bleachers.",
                "building": "Athletic Field Walkway", "severity": "low", "status": "submitted",
                "lat": 42.3579, "lng": -71.0970, "reporter": student,
                "photo": settings.DEMO_PHOTOGRAPHY["litter_outdoor"], "days_ago": 0, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004828", "category": "Illegal Dumping",
                "description": "Discarded wooden pallets and furniture blocking emergency exit doors behind administration building.",
                "building": "Administration Hall Rear Loading Dock", "severity": "critical", "status": "submitted",
                "lat": 42.3615, "lng": -71.0955, "reporter": student,
                "photo": settings.DEMO_PHOTOGRAPHY["illegal_dumping"], "days_ago": 0, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004829", "category": "Overflowing Bin",
                "description": "Recycling station behind the north dining hall overflowing again after weekend event.",
                "building": "Student Cafeteria — North Entrance", "severity": "medium", "status": "resolved",
                "lat": 42.3609, "lng": -71.0939, "reporter": student, "assigned_to": worker1,
                "photo": settings.DEMO_PHOTOGRAPHY["overflowing_bin"], "after_photo": settings.DEMO_PHOTOGRAPHY["after_clean"],
                "days_ago": 5, "resp_hours": 10
            },
            {
                "code": "CVA-2026-004830", "category": "Recycling Contamination",
                "description": "Greasy pizza boxes placed in the paper recycling stream outside the engineering lab.",
                "building": "Engineering Block B Quad", "severity": "high", "status": "assigned",
                "lat": 42.3596, "lng": -71.0951, "reporter": student, "assigned_to": worker1,
                "photo": settings.DEMO_PHOTOGRAPHY["recycling_station"], "days_ago": 1, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004831", "category": "Missed Collection",
                "description": "Monday morning collection skipped for the terrace bins; bags piling up at the service door.",
                "building": "Student Center Terrace", "severity": "medium", "status": "acknowledged",
                "lat": 42.3613, "lng": -71.0933, "reporter": faculty,
                "photo": settings.DEMO_PHOTOGRAPHY["waste_bins"], "days_ago": 1, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004832", "category": "Damaged Waste Infrastructure",
                "description": "Broken compactor door in the science complex loading bay poses a safety hazard.",
                "building": "Science Complex Basement", "severity": "high", "status": "in_progress",
                "lat": 42.3589, "lng": -71.0962, "reporter": faculty, "assigned_to": worker2,
                "photo": settings.DEMO_PHOTOGRAPHY["waste_bins"], "days_ago": 2, "resp_hours": 4
            },
            {
                "code": "CVA-2026-004833", "category": "Overflowing Bin",
                "description": "Third overflow this week at the north cafeteria entrance — likely undersized bin for peak hours.",
                "building": "Student Cafeteria — North Entrance", "severity": "high", "status": "submitted",
                "lat": 42.3607, "lng": -71.0937, "reporter": student,
                "photo": settings.DEMO_PHOTOGRAPHY["overflowing_bin"], "days_ago": 0, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004834", "category": "Recycling Contamination",
                "description": "Mixed organic waste found in the glass recycling bank near the hostel courtyard.",
                "building": "Hostel B Courtyard", "severity": "low", "status": "submitted",
                "lat": 42.3621, "lng": -71.0946, "reporter": student,
                "photo": settings.DEMO_PHOTOGRAPHY["recycling_station"], "days_ago": 0, "resp_hours": 0
            },
            {
                "code": "CVA-2026-004835", "category": "Litter Hotspot",
                "description": "Recurring litter buildup along the athletic field walkway after evening practice.",
                "building": "Athletic Field Walkway", "severity": "low", "status": "resolved",
                "lat": 42.3580, "lng": -71.0971, "reporter": student, "assigned_to": worker2,
                "photo": settings.DEMO_PHOTOGRAPHY["litter_outdoor"], "after_photo": settings.DEMO_PHOTOGRAPHY["after_clean"],
                "days_ago": 7, "resp_hours": 9
            },
            {
                "code": "CVA-2026-004836", "category": "Illegal Dumping",
                "description": "Repeat dumping of furniture behind administration hall — needs a monitoring camera.",
                "building": "Administration Hall Rear Loading Dock", "severity": "critical", "status": "acknowledged",
                "lat": 42.3616, "lng": -71.0956, "reporter": faculty,
                "photo": settings.DEMO_PHOTOGRAPHY["illegal_dumping"], "days_ago": 1, "resp_hours": 0
            },
        ]

        for item in reports_data:
            created = now - datetime.timedelta(days=item.get("days_ago", 0), hours=item.get("resp_hours", 0) / 2)
            rep = Report(
                report_code=item["code"],
                user_id=item["reporter"].id,
                campus_id=campus.id,
                category=item["category"],
                description=item["description"],
                building=item["building"],
                severity=item["severity"],
                status=item["status"],
                latitude=item["lat"],
                longitude=item["lng"],
                created_at=created,
                updated_at=created
            )
            db.add(rep)
            db.commit()
            db.refresh(rep)

            # Evidence Image
            img = ReportImage(
                report_id=rep.id,
                image_url=item["photo"],
                image_type="evidence"
            )
            db.add(img)

            # Assignment if present
            if "assigned_to" in item:
                asgn = Assignment(
                    report_id=rep.id,
                    worker_id=item["assigned_to"].id,
                    notes=f"Dispatched by Admin to {item['assigned_to'].name}",
                    assigned_at=created + datetime.timedelta(hours=1)
                )
                db.add(asgn)

            # Resolution if present
            if "after_photo" in item:
                resolved_at = created + datetime.timedelta(hours=item.get("resp_hours", 6))
                res = Resolution(
                    report_id=rep.id,
                    worker_id=item.get("assigned_to", worker1).id,
                    before_image=item["photo"],
                    after_image=item["after_photo"],
                    resolution_notes="Cleared area, disinfected surrounding pavement, and replaced bin liner.",
                    resolved_at=resolved_at
                )
                db.add(res)
                img_after = ReportImage(
                    report_id=rep.id,
                    image_url=item["after_photo"],
                    image_type="after"
                )
                db.add(img_after)

            # Verification if present
            if item["status"] == "verified":
                ver = Verification(
                    report_id=rep.id,
                    user_id=student.id,
                    verified=True,
                    feedback="Area is completely clean now. Great turnaround time!"
                )
                db.add(ver)

        # 4. Add Initial Notifications
        notifications = [
            Notification(
                user_id=student.id,
                title="Welcome to Circuva",
                message="Report issues, track cleanup status, and earn Impact Score points for a cleaner campus!"
            ),
            Notification(
                user_id=student.id,
                title="Issue Resolved",
                message="Report CVA-2026-004822 at Engineering Block B Quad has been resolved by Marcus Vance."
            ),
            Notification(
                user_id=worker1.id,
                title="Task Assignment",
                message="Assigned to report CVA-2026-004821: Overflowing Bin at Student Cafeteria."
            )
        ]
        db.add_all(notifications)
        db.commit()

        print("Database successfully seeded!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
