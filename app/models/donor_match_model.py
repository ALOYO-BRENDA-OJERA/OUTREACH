from datetime import datetime
from app.extensions import db
class DonorMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_request.id'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    status = db.Column(db.Enum('Notified', 'Accepted', 'Rejected', 'Completed', name='match_status'), default='Notified')
    notified_at = db.Column(db.DateTime, default=datetime.utcnow)

    donor = db.relationship('Donor', backref='matches')
    request = db.relationship('BloodRequest', backref='matches')    