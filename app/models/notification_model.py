from datetime import datetime
from app.extensions import db
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_request.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('Sent', 'Delivered', 'Failed', name='notification_status'), default='Sent')
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
