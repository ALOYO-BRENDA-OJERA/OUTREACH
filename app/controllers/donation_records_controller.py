from flask import Blueprint, request, jsonify
from app.models import Donor
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest

# Define Blueprint for the donor controller
donation_blueprint = Blueprint('donor', __name__)

# GET all donors
@donation_blueprint.route('/donors', methods=['GET'])
def get_donors():
    try:
        donors = Donor.query.all()  # Fetch all donors
        return jsonify([donor.to_dict() for donor in donors]), 200  # Return as JSON
    except SQLAlchemyError:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle database errors

# GET a specific donor by ID
@donation_blueprint.route('/donors/<int:id>', methods=['GET'])
def get_donor(id):
    try:
        donor = Donor.query.get(id)  # Fetch donor by ID
        if not donor:
            raise NotFound('Donor not found')
        return jsonify(donor.to_dict()), 200  # Return donor record as JSON
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # If donor not found
    except SQLAlchemyError:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# POST a new donor
@donation_blueprint.route('/donors', methods=['POST'])
def create_donor():
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')

        # Validate incoming data
        required_fields = ['name', 'age', 'blood_type', 'phone', 'city']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f'Missing required field: {field}')
        
        # Create a new donor record
        new_donor = Donor(
            name=data['name'],
            age=data['age'],
            blood_type=data['blood_type'],
            phone=data['phone'],
            email=data.get('email'),
            city=data['city'],
            location=data.get('location'),
            availability_status=data.get('availability_status', True)  # Default is True
        )
        
        db.session.add(new_donor)
        db.session.commit()  # Commit the transaction
        
        return jsonify(new_donor.to_dict()), 201  # Return the new donor record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except SQLAlchemyError:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# PUT to update an existing donor
@donation_blueprint.route('/donors/<int:id>', methods=['PUT'])
def update_donor(id):
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')
        
        # Find the donor record by ID
        donor = Donor.query.get(id)
        if not donor:
            raise NotFound('Donor not found')
        
        # Update the donor record with new data
        for field in data:
            setattr(donor, field, data[field])

        db.session.commit()  # Commit the changes
        
        return jsonify(donor.to_dict()), 200  # Return updated donor record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# DELETE a donor by ID
@donation_blueprint.route('/donors/<int:id>', methods=['DELETE'])
def delete_donor(id):
    try:
        donor = Donor.query.get(id)
        if not donor:
            raise NotFound('Donor not found')
        
        db.session.delete(donor)  # Delete the donor record
        db.session.commit()  # Commit the changes
        
        return jsonify({'message': 'Donor deleted successfully'}), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error
