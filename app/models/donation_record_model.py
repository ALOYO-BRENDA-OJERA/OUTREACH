from datetime import datetime
from app.extensions import db
class DonationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    blood_type = db.Column(db.String(5), nullable=False)
    donated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensures donors don’t donate too frequently (e.g., every 8 weeks)
    next_eligible_donation = db.Column(db.DateTime, nullable=False)
