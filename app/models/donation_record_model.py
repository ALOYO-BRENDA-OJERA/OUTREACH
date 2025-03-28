from datetime import datetime
from app.extensions import db

class DonationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    donated_at = db.Column(db.DateTime, default=datetime.utcnow)
    next_eligible_donation = db.Column(db.DateTime, nullable=False)
    
    # No need to define the relationship here since it's in the Donor model
    
    def to_dict(self):
        return {
            'id': self.id,
            'donor_id': self.donor_id,
            'hospital_id': self.hospital_id,
            'blood_type': self.blood_type,
            'donated_at': self.donated_at.isoformat(),
            'next_eligible_donation': self.next_eligible_donation.isoformat()
        }
