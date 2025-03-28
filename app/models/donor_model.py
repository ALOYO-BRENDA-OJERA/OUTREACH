from datetime import datetime
from app.extensions import db
class Donor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(100), unique=True)
    city = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))  # Optional GPS coordinates
    availability_status = db.Column(db.Boolean, default=True)  # True = Available

    donations = db.relationship('DonationRecord', backref='donor', lazy=True)
