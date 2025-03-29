# from datetime import datetime
# from app.extensions import db

# class Donor(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     age = db.Column(db.Integer, nullable=False)
#     blood_type = db.Column(db.String(5), nullable=False)
#     phone = db.Column(db.String(20), nullable=False, unique=True)
#     email = db.Column(db.String(100), unique=True)
#     city = db.Column(db.String(50), nullable=False)
#     location = db.Column(db.String(100))  # Optional GPS coordinates
#     availability_status = db.Column(db.Boolean, default=True)  # True = Available
    
#     # Use string-based relationship to avoid circular imports
#     donations = db.relationship('DonationRecord', backref='donor', lazy=True)
    
#     def to_dict(self):
#         return {
#             'id': self.id,
#             'name': self.name,
#             'age': self.age,
#             'blood_type': self.blood_type,
#             'phone': self.phone,
#             'email': self.email,
#             'city': self.city,
#             'location': self.location,
#             'availability_status': self.availability_status
#         }

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
    last_donation_date = db.Column(db.DateTime)  # Add this field
    
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
            'availability_status': self.availability_status,
            'last_donation_date': self.last_donation_date.isoformat() if self.last_donation_date else None
        }
    
    @property
    def is_eligible(self):
        """Check if donor is eligible to donate based on last donation date"""
        if not self.availability_status:
            return False
        if self.last_donation_date:
            from datetime import datetime, timedelta
            return datetime.utcnow() - self.last_donation_date > timedelta(days=90)
        return True