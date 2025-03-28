from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models.notification_model import Notification
from app.models.donor_model import Donor
from app.models.blood_request_model import BloodRequest
from app.models.donor_match_model import DonorMatch
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest
import africastalking

# Initialize Africa's Talking API
africastalking.initialize(username="your_username", api_key="your_api_key")

# Define the Blueprint for handling notifications
notification_blueprint = Blueprint('notification_blueprint', __name__, url_prefix='/api/v1/notifications')

# GET all notifications
@notification_blueprint.route('/', methods=['GET'])
def get_notifications():
    try:
        notifications = Notification.query.all()  # Fetch all notifications
        return jsonify([notification.to_dict() for notification in notifications]), 200  # Return as JSON
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle database errors

# GET a specific notification by ID
@notification_blueprint.route('/<int:id>', methods=['GET'])
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
@notification_blueprint.route('/', methods=['POST'])
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
            status='Pending'
        )
        
        # Send SMS using Africa's Talking API
        recipient = donor.phone  # Assumed that donor's phone number is stored
        response = africastalking.SMS.send([recipient], data['message'])
            
        # If the SMS is successfully sent, update the notification status
        if response.get("statusCode") == "200":
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
@notification_blueprint.route('/<int:id>', methods=['PUT'])
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
@notification_blueprint.route('/<int:id>', methods=['DELETE'])
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

# Notify a donor about a match
@notification_blueprint.route('/notify-match/<int:match_id>', methods=['POST'])
def notify_match(match_id):
    try:
        # Get the match
        match = DonorMatch.query.get(match_id)
        if not match:
            raise NotFound('Donor match not found')
            
        # Get the donor and request
        donor = Donor.query.get(match.donor_id)
        blood_request = BloodRequest.query.get(match.request_id)
        
        if not donor or not blood_request:
            raise NotFound('Donor or blood request not found')
            
        # Create message
        message = f"Hello {donor.name}, you have been matched with a blood request. " \
                 f"Blood type needed: {blood_request.blood_type}, " \
                 f"Urgency: {blood_request.urgency_level}. " \
                 f"Please respond if you can donate."
        
        # Create notification record
        new_notification = Notification(
            donor_id=donor.id,
            request_id=blood_request.id,
            message=message,
            status='Pending'
        )
        
        # Send SMS
        recipient = donor.phone
        response = africastalking.SMS.send([recipient], message)
        
        # Update status based on response
        if response.get("statusCode") == "200":
            new_notification.status = 'Sent'
            # Also update the match status
            match.status = 'Notified'
            match.notified_at = datetime.utcnow()
        else:
            new_notification.status = 'Failed'
            
        db.session.add(new_notification)
        db.session.commit()
        
        return jsonify(new_notification.to_dict()), 201
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

# Notify a requester when no matches are found
@notification_blueprint.route('/notify-no-matches/<int:request_id>', methods=['POST'])
def notify_no_matches(request_id):
    try:
        # Get the blood request
        blood_request = BloodRequest.query.get(request_id)
        if not blood_request:
            raise NotFound('Blood request not found')
            
        # Get the requester (assuming blood_request has a requester_id field)
        requester = Donor.query.get(blood_request.requester_id)  # Using Donor model instead of User
        if not requester:
            raise NotFound('Requester not found')
            
        # Create message
        message = f"We regret to inform you that no matching donors have been found yet for your " \
                 f"blood request (type {blood_request.blood_type}). We will continue searching " \
                 f"and notify you when a match is found."
        
        # Create notification record
        new_notification = Notification(
            donor_id=requester.id,  # Using donor_id instead of user_id
            request_id=blood_request.id,
            message=message,
            status='Pending'
        )
        
        # Send SMS
        recipient = requester.phone
        response = africastalking.SMS.send([recipient], message)
        
        # Update status based on response
        if response.get("statusCode") == "200":
            new_notification.status = 'Sent'
        else:
            new_notification.status = 'Failed'
            
        db.session.add(new_notification)
        db.session.commit()
        
        return jsonify(new_notification.to_dict()), 201
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

# Batch notify all donors for a specific blood request
@notification_blueprint.route('/batch-notify-request/<int:request_id>', methods=['POST'])
def batch_notify_request(request_id):
    try:
        # Get the blood request
        blood_request = BloodRequest.query.get(request_id)
        if not blood_request:
            raise NotFound('Blood request not found')
            
        # Get all matches for this request that haven't been notified yet
        pending_matches = DonorMatch.query.filter_by(
            request_id=request_id,
            status='Pending'
        ).all()
        
        if not pending_matches:
            return jsonify({'message': 'No pending matches to notify'}), 200
            
        notifications_sent = 0
        notifications_failed = 0
        
        for match in pending_matches:
            # Get the donor
            donor = Donor.query.get(match.donor_id)
            if not donor:
                continue
                
            # Create message
            message = f"Hello {donor.name}, you have been matched with a blood request. " \
                     f"Blood type needed: {blood_request.blood_type}, " \
                     f"Urgency: {blood_request.urgency_level}. " \
                     f"Please respond if you can donate."
            
            # Create notification record
            new_notification = Notification(
                donor_id=donor.id,
                request_id=blood_request.id,
                message=message,
                status='Pending'
            )
            
            # Send SMS
            recipient = donor.phone
            response = africastalking.SMS.send([recipient], message)
            
            # Update status based on response
            if response.get("statusCode") == "200":
                new_notification.status = 'Sent'
                # Also update the match status
                match.status = 'Notified'
                match.notified_at = datetime.utcnow()
                notifications_sent += 1
            else:
                new_notification.status = 'Failed'
                notifications_failed += 1
                
            db.session.add(new_notification)
            
        db.session.commit()
        
        return jsonify({
            'message': f'Sent {notifications_sent} notifications, {notifications_failed} failed',
            'request_id': request_id
        }), 200
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

# Check for unmatched requests and send notifications
@notification_blueprint.route('/check-unmatched-requests', methods=['POST'])
def check_unmatched_requests():
    try:
        # Get blood requests that have no matches
        unmatched_requests = db.session.query(BloodRequest).outerjoin(
            DonorMatch, BloodRequest.id == DonorMatch.request_id
        ).filter(
            BloodRequest.status == 'Pending',
            DonorMatch.id == None
        ).all()
        
        if not unmatched_requests:
            return jsonify({'message': 'No unmatched requests found'}), 200
            
        notifications_sent = 0
        
        for request in unmatched_requests:
            # Get the requester (using Donor model)
            requester = Donor.query.get(request.requester_id)
            if not requester:
                continue
                
            # Create message
            message = f"We regret to inform you that no matching donors have been found yet for your " \
                     f"blood request (type {request.blood_type}). We will continue searching " \
                     f"and notify you when a match is found."
            
            # Create notification record
            new_notification = Notification(
                donor_id=requester.id,  # Using donor_id instead of user_id
                request_id=request.id,
                message=message,
                status='Pending'
            )
            
            # Send SMS
            recipient = requester.phone
            response = africastalking.SMS.send([recipient], message)
            
            # Update status based on response
            if response.get("statusCode") == "200":
                new_notification.status = 'Sent'
                notifications_sent += 1
            else:
                new_notification.status = 'Failed'
                
            db.session.add(new_notification)
            
        db.session.commit()
        
        return jsonify({
            'message': f'Sent {notifications_sent} notifications for unmatched requests',
            'unmatched_requests': len(unmatched_requests)
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
