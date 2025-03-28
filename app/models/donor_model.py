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
    
    # Use string-based relationship to avoid circular imports
    donations = db.relationship('DonationRecord', backref='donor', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'blood_type': self.blood_type,
            'phone': self.phone,
            'email': self.email,
            'city': self.city,
            'location': self.location,
            'availability_status': self.availability_status
        }
