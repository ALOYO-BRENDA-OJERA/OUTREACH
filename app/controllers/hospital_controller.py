from flask import Blueprint, request, jsonify
from app.models.hospital_model import Hospital
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest

# Define Blueprint for the controller with a unique name
hospital_bp = Blueprint('hospital_bp', __name__)

# GET all hospitals
@hospital_bp.route('/hospitals', methods=['GET'])
def get_hospitals():
    try:
        hospitals = Hospital.query.all()  # Fetch all hospitals
        return jsonify([hospital.to_dict() for hospital in hospitals]), 200  # Return as JSON
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle database errors

# GET a specific hospital by ID
@hospital_bp.route('/hospitals/<int:id>', methods=['GET'])
def get_hospital(id):
    try:
        hospital = Hospital.query.get(id)  # Fetch hospital by ID
        if not hospital:
            raise NotFound('Hospital not found')
        return jsonify(hospital.to_dict()), 200  # Return hospital record as JSON
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # If hospital not found
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# POST a new hospital
@hospital_bp.route('/hospitals', methods=['POST'])
def create_hospital():
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')

        # Validate incoming data
        required_fields = ['name', 'city', 'contact_number']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f'Missing required field: {field}')
        
        # Create a new hospital record
        new_hospital = Hospital(
            name=data['name'],
            city=data['city'],
            location=data.get('location'),  # Optional field
            contact_number=data['contact_number']
        )
        
        db.session.add(new_hospital)
        db.session.commit()  # Commit the transaction
        
        return jsonify(new_hospital.to_dict()), 201  # Return the new hospital record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# PUT to update an existing hospital
@hospital_bp.route('/hospitals/<int:id>', methods=['PUT'])
def update_hospital(id):
    try:
        data = request.get_json()  # Get JSON data from the request
        if not data:
            raise BadRequest('No input data provided')
        
        # Find the hospital record by ID
        hospital = Hospital.query.get(id)
        if not hospital:
            raise NotFound('Hospital not found')
        
        # Update the hospital record with new data
        if 'name' in data:
            hospital.name = data['name']
        if 'city' in data:
            hospital.city = data['city']
        if 'location' in data:
            hospital.location = data['location']
        if 'contact_number' in data:
            hospital.contact_number = data['contact_number']

        db.session.commit()  # Commit the changes
        
        return jsonify(hospital.to_dict()), 200  # Return updated hospital record as JSON
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error

# DELETE a hospital by ID
@hospital_bp.route('/hospitals/<int:id>', methods=['DELETE'])
def delete_hospital(id):
    try:
        hospital = Hospital.query.get(id)
        if not hospital:
            raise NotFound('Hospital not found')
        
        db.session.delete(hospital)  # Delete the hospital record
        db.session.commit()  # Commit the changes
        
        return jsonify({'message': 'Hospital deleted successfully'}), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404  # Handle not found error
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        return jsonify({'error': 'Database error occurred'}), 500  # Handle DB error
