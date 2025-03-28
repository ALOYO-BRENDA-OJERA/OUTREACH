from datetime import datetime
from app.extensions import db

class BloodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))  # Optional GPS coordinates
    contact_number = db.Column(db.String(20), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    
    # Missing fields that would be useful:
    blood_type = db.Column(db.String(5), nullable=False)
    units_needed = db.Column(db.Integer, nullable=False, default=1)
    urgency_level = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BloodRequest {self.name}>'
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'location': self.location,
            'contact_number': self.contact_number,
            'hospital_id': self.hospital_id,
            'blood_type': self.blood_type,
            'units_needed': self.units_needed,
            'urgency_level': self.urgency_level,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
