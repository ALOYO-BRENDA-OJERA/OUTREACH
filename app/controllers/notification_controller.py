from flask import Blueprint, request, jsonify
from app.models.notification_model import Notification
from app.models.donor_model import Donor
from app.models.blood_request_model import BloodRequest
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest
import africastalking




# Initialize Africa's Talking API
africastalking.initialize(username="your_username", api_key="your_api_key")


# Define the Blueprint for handling notifications
notification_blueprint = Blueprint('notification_blueprint', __name__)

# GET all notifications
@notification_blueprint.route('/notifications', methods=['GET'])
def get_notifications():
    try:
        notifications = Notification.query.all()  # Fetch all notifications
        return jsonify([notification.to_dict() for notification in notifications]), 200  # Return as JSON
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle database errors

# GET a specific notification by ID
@notification_blueprint.route('/notifications/<int:id>', methods=['GET'])
def get_notification(id):
    try:
        notification = Notification.query.get(id)  # Fetch notification by ID
        if not notification:
            raise NotFound('Notification not found')
        return jsonify(notification.to_dict()), 200  # Return notification record as JSON
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # If notification not found
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# POST a new notification
@notification_blueprint.route('/notifications', methods=['POST'])
def create_notification():
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')

        # Validate incoming data
        required_fields = ['donor_id', 'message']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f'Missing required field: {field}')

        donor = Donor.query.get(data['donor_id'])
        if not donor:
            raise NotFound('Donor not found')
        
        # Create a new notification record
        new_notification = Notification(
            donor_id=data['donor_id'],
            request_id=data.get('request_id'),  # Optional field
            message=data['message'],
            status='Sent'
        )

        # Send SMS using Africa's Talking API
        recipient = donor.phone  # Assumed that donor's phone number is stored
        response = africastalking.SMS.send([recipient], data['message'])
        
        # If the SMS is successfully sent, update the notification status
        if response["statusCode"] == "200":
            new_notification.status = 'Sent'
        else:
            new_notification.status = 'Failed'

        db.session.add(new_notification)
        db.session.commit()  # Commit the transaction
        
        return jsonify(new_notification.to_dict()), 201  # Return the new notification record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# PUT to update an existing notification
@notification_blueprint.route('/notifications/<int:id>', methods=['PUT'])
def update_notification(id):
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')

        # Find the notification record by ID
        notification = Notification.query.get(id)
        if not notification:
            raise NotFound('Notification not found')

        # Update the notification record with new data
        if 'message' in data:
            notification.message = data['message']
        if 'status' in data:
            notification.status = data['status']

        db.session.commit()  # Commit the changes
        
        return jsonify(notification.to_dict()), 200  # Return updated notification record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# DELETE a notification by ID
@notification_blueprint.route('/notifications/<int:id>', methods=['DELETE'])
def delete_notification(id):
    try:
        notification = Notification.query.get(id)
        if not notification:
            raise NotFound('Notification not found')

        db.session.delete(notification)  # Delete the notification record
        db.session.commit()  # Commit the changes

        return jsonify({'message': 'Notification deleted successfully'}), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error
