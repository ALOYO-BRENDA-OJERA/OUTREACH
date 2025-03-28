from flask import Flask
# from app.extensions import db, migrate, cors
from app.extensions import db, migrate, bcrypt, jwt, scheduler, mail, cors

# Import controllers (blueprints) for each module
from app.controllers.donor_controller import donor_bp
from app.controllers.hospital_controller import hospital_bp
from app.controllers.blood_request_controller import blood_request_bp
from app.controllers.notification_controller import notification_blueprint
from app.controllers.donor_match_controller import donor_match_bp

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

    # Register Blueprints with appropriate URL prefixes
    app.register_blueprint(donor_bp, url_prefix='/api/v1/donors')  # Register under /api/v1/donors endpoint
    app.register_blueprint(hospital_bp, url_prefix='/api/v1/hospitals')  # Register under /api/v1/hospitals endpoint
    app.register_blueprint(blood_request_bp, url_prefix='/api/v1/bloodrequests')  # Register under /api/v1/bloodrequests endpoint
    app.register_blueprint(notification_blueprint, url_prefix='/api/v1/notifications')  # Register under /api/v1/notifications endpoint
    app.register_blueprint(donor_match_bp, url_prefix='/api/v1/donormatches')  # Register under /api/v1/donormatches endpoint

    return app

# Ensure the app runs only if this script is executed directly
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)  # Run the Flask app in debug mode
