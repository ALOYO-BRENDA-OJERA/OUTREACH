from datetime import datetime
from app.extensions import db

class DonorMatch(db.Model):
    __tablename__ = 'donor_match'  # Optionally set a custom table name

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_request.id'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    status = db.Column(db.Enum('Notified', 'Accepted', 'Rejected', 'Completed', name='match_status'), default='Notified')
    notified_at = db.Column(db.DateTime, default=datetime.utcnow)

    donor = db.relationship('Donor', backref='matches')
    request = db.relationship('BloodRequest', backref='matches')

    def to_dict(self):
     return {
        'id': self.id,
        'request_id': self.request_id,
        'donor_id': self.donor_id,
        'status': self.status,
        'notified_at': self.notified_at.isoformat() if self.notified_at else None,
        'donor': {
            'id': self.donor.id,
            'name': self.donor.name,  # Assuming donor has a 'name' field
            'email': self.donor.email  # Assuming donor has an 'email' field
        } if self.donor else None,
        'request': {
            'id': self.request.id,
            'blood_type': self.request.blood_type,  # Correct field name
            'units_needed': self.request.units_needed,
            'urgency_level': self.request.urgency_level,
            'status': self.request.status
        } if self.request else None
    }
