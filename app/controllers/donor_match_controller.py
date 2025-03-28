from datetime import datetime
from flask import Blueprint, request, jsonify
# from app.models import DonorMatch, Donor, BloodRequest
from app.models.donor_match_model import DonorMatch
from app.models.donor_model import Donor
from app.models.blood_request_model import BloodRequest
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest

# Define Blueprint for the Donor Match controller
donor_match_bp = Blueprint('donor_match_bp', __name__)

# GET all donor matches
@donor_match_bp.route('/donormatches', methods=['GET'])
def get_donor_matches():
    try:
        matches = DonorMatch.query.all()  # Fetch all donor match records
        return jsonify([match.to_dict() for match in matches]), 200  # Return as JSON
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle database errors

# GET a specific donor match by ID
@donor_match_bp.route('/donormatches/<int:id>', methods=['GET'])
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
@donor_match_bp.route('/donormatches', methods=['POST'])
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
            status=data.get('status', 'Notified'),  # Default status is 'Notified'
            notified_at=datetime.utcnow()
        )
        
        db.session.add(new_match)
        db.session.commit()  # Commit the transaction
        
        return jsonify(new_match.to_dict()), 201  # Return the new donor match record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# PUT to update an existing donor match
@donor_match_bp.route('/donormatches/<int:id>', methods=['PUT'])
def update_donor_match(id):
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')
        
        # Find the donor match record by ID
        match = DonorMatch.query.get(id)
        if not match:
            raise NotFound('Donor match not found')
        
        # Update the status if provided
        if 'status' in data:
            match.status = data['status']
        if 'notified_at' in data:
            match.notified_at = datetime.strptime(data['notified_at'], '%Y-%m-%d %H:%M:%S')
        
        db.session.commit()  # Commit the changes
        
        return jsonify(match.to_dict()), 200  # Return updated donor match record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# DELETE a donor match by ID
@donor_match_bp.route('/donormatches/<int:id>', methods=['DELETE'])
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
