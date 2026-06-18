# THIS IMPLEMENTS THE DATABASE SCHEMA DEFINITIONS 
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    
    # USE CONVENTION : Admin, Trekker, Staff
    role = db.Column(db.String(20), nullable=False, default="trekker")
    
    # USE CONVENTION , ALL SMALL CASE : active/pending/blacklisted
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))



class Treks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open")
    trek_updates = db.Column(db.String(250), default="As Scheduled")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# HERE WE ASSUME THAT ONLY ONE STAFF GETS ASSIGNED ONE TREK. 
# If many staff can be assigned to one trek , can remove primary_key
class StaffAssignment(db.Model):
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id", ondelete="CASCADE"), primary_key=True)
    staff_assigned = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), nullable=False, default="Booked")

