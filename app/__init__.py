from flask import Flask
from app.extensions import db, migrate, bcrypt, jwt, scheduler, mail, cors

# Import models in dependency order
from app.models.hospital_model import Hospital
from app.models.donor_model import Donor
from app.models.blood_request_model import BloodRequest
from app.models.donation_record_model import DonationRecord
from app.models.donor_match_model import DonorMatch
from app.models.notification_model import Notification

# Import controllers (blueprints) for each module
from app.controllers.hospital_controller import hospital_bp
from app.controllers.donor_controller import donor_bp
from app.controllers.blood_request_controller import blood_request_bp
from app.controllers.donor_match_controller import donor_match_bp
from app.controllers.notification_controller import notification_blueprint
from app.controllers.donation_records_controller import donation_blueprint  # Added donation blueprint

def create_app():
    """Flask application factory"""
    app = Flask(__name__)
    
    # Configuration (you can load this from config.py or directly here)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/reachout'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'
    
    # Initialize extensions
    db.init_app(app)  # Use the db initialized in extensions
    migrate.init_app(app, db)  # Use the migrate initialized in extensions
    cors.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    scheduler.init_app(app)
    
    # Register Blueprints in logical order (hospital first, then donors, etc.)
    app.register_blueprint(hospital_bp, url_prefix='/api/v1/hospitals')
    app.register_blueprint(donor_bp, url_prefix='/api/v1/donors')
    app.register_blueprint(blood_request_bp, url_prefix='/api/v1/blood_requests')
    app.register_blueprint(donor_match_bp, url_prefix='/api/v1/donor_matches')
    app.register_blueprint(notification_blueprint, url_prefix='/api/v1/notifications')
    app.register_blueprint(donation_blueprint)  # Added donation blueprint
    
    return app

# Ensure the app runs only if this script is executed directly
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)  # Run the Flask app in debug mode
