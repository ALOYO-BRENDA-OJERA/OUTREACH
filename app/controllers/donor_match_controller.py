from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models.donor_match_model import DonorMatch
from app.models.donor_model import Donor
from app.models.blood_request_model import BloodRequest
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest
import requests

# Define Blueprint for the Donor Match controller
donor_match_bp = Blueprint('donor_match_bp', __name__, url_prefix='/api/v1/donor_matches')

# GET all donor matches
@donor_match_bp.route('/', methods=['GET'])
def get_donor_matches():
    try:
        matches = DonorMatch.query.all()  # Fetch all donor match records
        return jsonify([match.to_dict() for match in matches]), 200  # Return as JSON
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle database errors

# GET a specific donor match by ID
@donor_match_bp.route('/<int:id>', methods=['GET'])
def get_donor_match(id):
    try:
        match = DonorMatch.query.get(id)  # Fetch donor match by ID
        if not match:
            raise NotFound('Donor match not found')
        return jsonify(match.to_dict()), 200  # Return donor match record as JSON
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # If donor match is not found
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# POST a new donor match
@donor_match_bp.route('/create_match', methods=['POST'])
def create_donor_match():
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')
            
        # Validate incoming data
        if 'request_id' not in data or 'donor_id' not in data:
            raise BadRequest('Missing required fields: request_id or donor_id')
            
        # Fetch the associated blood request and donor to ensure they exist
        blood_request = BloodRequest.query.get(data['request_id'])
        donor = Donor.query.get(data['donor_id'])
            
        if not blood_request or not donor:
            raise NotFound('Blood request or Donor not found')
            
        # Create a new donor match record object
        new_match = DonorMatch(
            request_id=data['request_id'],
            donor_id=data['donor_id'],
            status=data.get('status', 'Pending'),  # Default status is 'Pending'
            notified_at=datetime.utcnow()
        )
            
        db.session.add(new_match)
        db.session.commit()  # Commit the transaction
        
        # Send notification to the donor about the match
        try:
            # Create message
            message = f"Hello {donor.name}, you have been matched with a blood request. " \
                     f"Blood type needed: {blood_request.blood_type}, " \
                     f"Urgency: {blood_request.urgency_level}. " \
                     f"Please respond if you can donate."
            
            # Prepare notification data
            notification_data = {
                'donor_id': donor.id,
                'request_id': blood_request.id,
                'message': message
            }
            
            # Send the notification
            notification_response = requests.post(
                "http://localhost:5000/api/v1/notifications/",
                json=notification_data
            )
            
            # Update match status if notification was sent successfully
            if notification_response.status_code == 201:
                new_match.status = 'Notified'
                db.session.commit()
        except Exception as e:
            # Log the error but don't fail the match creation
            print(f"Error sending notification: {str(e)}")
            
        return jsonify(new_match.to_dict()), 201  # Return the new donor match record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# PUT to update an existing donor match
@donor_match_bp.route('/<int:id>', methods=['PUT'])
def update_donor_match(id):
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')
            
        # Find the donor match record by ID
        match = DonorMatch.query.get(id)
        if not match:
            raise NotFound('Donor match not found')
            
        # Get the previous status to check for status changes
        previous_status = match.status
            
        # Update the status if provided
        if 'status' in data:
            match.status = data['status']
        if 'notified_at' in data:
            match.notified_at = datetime.strptime(data['notified_at'], '%Y-%m-%d %H:%M:%S')
            
        db.session.commit()  # Commit the changes
        
        # Send notifications based on status changes
        if 'status' in data and previous_status != data['status']:
            try:
                # Get the donor and blood request
                donor = Donor.query.get(match.donor_id)
                blood_request = BloodRequest.query.get(match.request_id)
                
                if donor and blood_request:
                    # Different messages based on the new status
                    if data['status'] == 'Accepted':
                        # Notify the donor that they've accepted
                        donor_message = f"Thank you for accepting the blood donation request. " \
                                       f"The blood bank will contact you with further details."
                        
                        # Notify the requester that a donor has accepted
                        requester = Donor.query.get(blood_request.requester_id)
                        if requester:
                            requester_message = f"Good news! A donor has accepted to donate for your blood request. " \
                                              f"The blood bank will contact you with further details."
                            
                            # Send notification to requester
                            requester_notification = {
                                'donor_id': requester.id,
                                'request_id': blood_request.id,
                                'message': requester_message
                            }
                            
                            requests.post(
                                "http://localhost:5000/api/v1/notifications/",
                                json=requester_notification
                            )
                        
                        # Also update the blood request status
                        blood_request.status = 'Matched'
                        db.session.commit()
                        
                    elif data['status'] == 'Declined':
                        # Notify the donor that they've declined
                        donor_message = f"You have declined the blood donation request. " \
                                       f"Thank you for your consideration."
                        
                        # Try to find another match for this request
                        try:
                            # Find potential matches
                            compatible_types = get_compatible_blood_types(blood_request.blood_type)
                            potential_donors = Donor.query.filter(
                                Donor.blood_type.in_(compatible_types),
                                Donor.is_available == True,
                                Donor.id != donor.id  # Exclude the donor who declined
                            ).all()
                            
                            # Create a new match with the first available donor
                            if potential_donors:
                                new_donor = potential_donors[0]
                                new_match_data = {
                                    'request_id': blood_request.id,
                                    'donor_id': new_donor.id
                                }
                                
                                requests.post(
                                    "http://localhost:5000/api/v1/donor_matches/create_match",
                                    json=new_match_data
                                )
                        except Exception as e:
                            print(f"Error finding new match: {str(e)}")
                    
                    elif data['status'] == 'Completed':
                        # Notify the donor that donation is complete
                        donor_message = f"Thank you for your blood donation! " \
                                       f"Your generosity helps save lives."
                        
                        # Notify the requester that donation is complete
                        requester = Donor.query.get(blood_request.requester_id)
                        if requester:
                            requester_message = f"Good news! The blood donation for your request has been completed. " \
                                              f"Thank you for using our service."
                            
                            # Send notification to requester
                            requester_notification = {
                                'donor_id': requester.id,
                                'request_id': blood_request.id,
                                'message': requester_message
                            }
                            
                            requests.post(
                                "http://localhost:5000/api/v1/notifications/",
                                json=requester_notification
                            )
                        
                        # Update the blood request status
                        blood_request.status = 'Completed'
                        db.session.commit()
                    
                    else:
                        # Default message for other status changes
                        donor_message = f"Your blood donation match status has been updated to: {data['status']}."
                    
                    # Send notification to the donor
                    donor_notification = {
                        'donor_id': donor.id,
                        'request_id': blood_request.id,
                        'message': donor_message
                    }
                    
                    requests.post(
                        "http://localhost:5000/api/v1/notifications/",
                        json=donor_notification
                    )
            except Exception as e:
                # Log the error but don't fail the update operation
                print(f"Error sending status change notification: {str(e)}")
            
        return jsonify(match.to_dict()), 200  # Return updated donor match record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# DELETE a donor match by ID
@donor_match_bp.route('/<int:id>', methods=['DELETE'])
def delete_donor_match(id):
    try:
        match = DonorMatch.query.get(id)
        if not match:
            raise NotFound('Donor match not found')
            
        db.session.delete(match)  # Delete the donor match record
        db.session.commit()  # Commit the changes
            
        return jsonify({'message': 'Donor match deleted successfully'}), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# Helper function to get compatible blood types
def get_compatible_blood_types(blood_type):
    """Return list of blood types compatible with the given blood type"""
    compatibility = {
        'O-': ['O-'],
        'O+': ['O-', 'O+'],
        'A-': ['O-', 'A-'],
        'A+': ['O-', 'O+', 'A-', 'A+'],
        'B-': ['O-', 'B-'],
        'B+': ['O-', 'O+', 'B-', 'B+'],
        'AB-': ['O-', 'A-', 'B-', 'AB-'],
        'AB+': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
    }
    return compatibility.get(blood_type, [])

# Find potential matches for a specific blood request
@donor_match_bp.route('/find-matches/<int:request_id>', methods=['GET'])
def find_potential_matches(request_id):
    try:
        # Get the blood request
        blood_request = BloodRequest.query.get(request_id)
        if not blood_request:
            raise NotFound('Blood request not found')
            
        # Find compatible blood types
        compatible_types = get_compatible_blood_types(blood_request.blood_type)
            
        # Find donors with compatible blood type who are available
        potential_donors = Donor.query.filter(
            Donor.blood_type.in_(compatible_types),
            Donor.is_available == True
        ).all()
            
        # You could add more filtering logic here (distance calculation, etc.)
            
        return jsonify([donor.to_dict() for donor in potential_donors]), 200
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500
    
    
    # Automatically create matches for all pending blood requests
@donor_match_bp.route('/batch-match', methods=['POST'])
def batch_match_donors():
    try:
        # Get all pending blood requests
        pending_requests = BloodRequest.query.filter_by(status='Pending').all()
        matches_created = 0
        requests_with_no_matches = []
            
        for request in pending_requests:
            # Find compatible donors
            compatible_types = get_compatible_blood_types(request.blood_type)
            potential_donors = Donor.query.filter(
                Donor.blood_type.in_(compatible_types),
                Donor.is_available == True
            ).all()
            
            if not potential_donors:
                # No matches found for this request
                requests_with_no_matches.append(request.id)
                continue
                
            # Create matches for each potential donor
            matches_for_this_request = 0
            for donor in potential_donors:
                # Check if match already exists
                existing_match = DonorMatch.query.filter_by(
                    request_id=request.id,
                    donor_id=donor.id
                ).first()
                    
                if not existing_match:
                    new_match = DonorMatch(
                        request_id=request.id,
                        donor_id=donor.id,
                        status='Pending',
                        notified_at=datetime.utcnow()
                    )
                    db.session.add(new_match)
                    matches_created += 1
                    matches_for_this_request += 1
            
            db.session.commit()
            
            # Send notifications for each new match
            if matches_for_this_request > 0:
                # Get all new matches for this request
                new_matches = DonorMatch.query.filter_by(
                    request_id=request.id,
                    status='Pending'
                ).all()
                
                for match in new_matches:
                    try:
                        # Get the donor and blood request
                        donor = Donor.query.get(match.donor_id)
                        blood_request = BloodRequest.query.get(match.request_id)
                        
                        if donor and blood_request:
                            # Create message
                            message = f"Hello {donor.name}, you have been matched with a blood request. " \
                                    f"Blood type needed: {blood_request.blood_type}, " \
                                    f"Urgency: {blood_request.urgency_level}. " \
                                    f"Please respond if you can donate."
                            
                            # Prepare notification data
                            notification_data = {
                                'donor_id': donor.id,
                                'request_id': blood_request.id,
                                'message': message
                            }
                            
                            # Send the notification
                            notification_response = requests.post(
                                "http://localhost:5000/api/v1/notifications/",
                                json=notification_data
                            )
                            
                            # Update match status if notification was sent successfully
                            if notification_response.status_code == 201:
                                match.status = 'Notified'
                                db.session.commit()
                    except Exception as e:
                        # Log the error but continue with other notifications
                        print(f"Error sending notification to donor {match.donor_id}: {str(e)}")
        
        # Send notifications for requests with no matches
        for request_id in requests_with_no_matches:
            try:
                # Get the blood request
                blood_request = BloodRequest.query.get(request_id)
                if blood_request and hasattr(blood_request, 'requester_id'):
                    # Get the requester
                    requester = Donor.query.get(blood_request.requester_id)
                    if requester:
                        # Create message
                        message = f"We regret to inform you that no matching donors have been found yet for your " \
                                f"blood request (type {blood_request.blood_type}). We will continue searching " \
                                f"and notify you when a match is found."
                        
                        # Prepare notification data
                        notification_data = {
                            'donor_id': requester.id,
                            'request_id': blood_request.id,
                            'message': message
                        }
                        
                        # Send the notification
                        requests.post(
                            "http://localhost:5000/api/v1/notifications/",
                            json=notification_data
                        )
            except Exception as e:
                # Log the error but continue with other notifications
                print(f"Error sending no-match notification for request {request_id}: {str(e)}")
                
        return jsonify({
            'message': f'Created {matches_created} new potential matches',
            'requests_with_no_matches': len(requests_with_no_matches)
        }), 201
            
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500



# # In your blood request controller
# @blood_request_bp.route('/<int:id>', methods=['GET'])
# def get_blood_request(id):
#     try:
#         request = BloodRequest.query.get(id)
#         if not request:
#             raise NotFound('Blood request not found')
            
#         # Get the match count
#         match_count = DonorMatch.query.filter_by(request_id=id).count()
        
#         response = request.to_dict()
#         response['match_count'] = match_count
        
#         return jsonify(response), 200
#     except NotFound as e:
#         return jsonify({'error': str(e)}), 404
#     except SQLAlchemyError as e:
#         return jsonify({'error': 'Database error occurred'}), 500
