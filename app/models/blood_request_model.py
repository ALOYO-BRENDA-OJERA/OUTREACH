from datetime import datetime
from app.extensions import db

class BloodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))  # Optional GPS coordinates
    contact_number = db.Column(db.String(20), nullable=False)

    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)


    def __repr__(self):
        return f'<BloodRequest {self.name}>'
