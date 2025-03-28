from flask import Blueprint, request, jsonify
from app.models.hospital_model import Hospital
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Blueprint for the controller with a unique name
hospital_bp = Blueprint('hospital_bp', __name__, url_prefix='/api/v1/hospitals')

# GET all hospitals
@hospital_bp.route('/get_hospitals', methods=['GET'])
def get_hospitals():
    try:
        logger.info("Attempting to fetch all hospitals")
        hospitals = Hospital.query.all()  # Fetch all hospitals
        logger.info(f"Successfully retrieved {len(hospitals)} hospitals")
        return jsonify([hospital.to_dict() for hospital in hospitals]), 200  # Return as JSON
    except SQLAlchemyError as e:
        error_msg = f"Database error in get_hospitals: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500  # Handle database errors

# GET a specific hospital by ID
@hospital_bp.route('/hospitals/<int:id>', methods=['GET'])
def get_hospital(id):
    try:
        logger.info(f"Attempting to fetch hospital with ID: {id}")
        hospital = Hospital.query.get(id)  # Fetch hospital by ID
        if not hospital:
            logger.warning(f"Hospital with ID {id} not found")
            raise NotFound(f'Hospital with ID {id} not found')
        logger.info(f"Successfully retrieved hospital: {hospital.name}")
        return jsonify(hospital.to_dict()), 200  # Return hospital record as JSON
    except NotFound as e:
        logger.warning(str(e))
        return jsonify({'error': str(e)}), 404  # If hospital not found
    except SQLAlchemyError as e:
        error_msg = f"Database error in get_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500  # Handle DB error

# POST a new hospital
@hospital_bp.route('/create_hospitals', methods=['POST'])
def create_hospital():
    try:
        logger.info("Attempting to create a new hospital")
        data = request.get_json()  # Get JSON data from the request
        
        # Log the received data (excluding sensitive information)
        logger.info(f"Received data: {data}")
        
        if not data:
            logger.warning("No input data provided in request")
            raise BadRequest('No input data provided')
        
        # Validate incoming data
        required_fields = ['name', 'city', 'contact_number']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field in request: {field}")
                raise BadRequest(f'Missing required field: {field}')
        
        # Create a new hospital record
        logger.info("Creating new hospital record")
        new_hospital = Hospital(
            name=data['name'],
            city=data['city'],
            location=data.get('location'),  # Optional field
            contact_number=data['contact_number']
        )
        
        logger.info("Adding hospital to database session")
        db.session.add(new_hospital)
        
        logger.info("Committing transaction")
        db.session.commit()  # Commit the transaction
        
        logger.info(f"Successfully created hospital: {new_hospital.name} with ID: {new_hospital.id}")
        return jsonify(new_hospital.to_dict()), 201  # Return the new hospital record as JSON
    
    except BadRequest as e:
        logger.warning(f"Bad request error: {str(e)}")
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        error_msg = f"Database error in create_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500  # Handle DB error
    
    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        error_msg = f"Unexpected error in create_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

# PUT to update an existing hospital
@hospital_bp.route('/hospitals/<int:id>', methods=['PUT'])
def update_hospital(id):
    try:
        logger.info(f"Attempting to update hospital with ID: {id}")
        data = request.get_json()  # Get JSON data from the request
        
        logger.info(f"Received update data: {data}")
        
        if not data:
            logger.warning("No input data provided in update request")
            raise BadRequest('No input data provided')
        
        # Find the hospital record by ID
        hospital = Hospital.query.get(id)
        if not hospital:
            logger.warning(f"Hospital with ID {id} not found for update")
            raise NotFound(f'Hospital with ID {id} not found')
        
        logger.info(f"Found hospital to update: {hospital.name}")
        
        # Update the hospital record with new data
        if 'name' in data:
            hospital.name = data['name']
        if 'city' in data:
            hospital.city = data['city']
        if 'location' in data:
            hospital.location = data['location']
        if 'contact_number' in data:
            hospital.contact_number = data['contact_number']
        
        logger.info("Committing update transaction")
        db.session.commit()  # Commit the changes
        
        logger.info(f"Successfully updated hospital with ID: {id}")
        return jsonify(hospital.to_dict()), 200  # Return updated hospital record as JSON
    
    except BadRequest as e:
        logger.warning(f"Bad request error in update: {str(e)}")
        return jsonify({'error': str(e)}), 400  # Handle bad request error
    
    except NotFound as e:
        logger.warning(str(e))
        return jsonify({'error': str(e)}), 404  # Handle not found error
    
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        error_msg = f"Database error in update_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500  # Handle DB error
    
    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        error_msg = f"Unexpected error in update_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

# DELETE a hospital by ID
@hospital_bp.route('/hospitals/<int:id>', methods=['DELETE'])
def delete_hospital(id):
    try:
        logger.info(f"Attempting to delete hospital with ID: {id}")
        hospital = Hospital.query.get(id)
        if not hospital:
            logger.warning(f"Hospital with ID {id} not found for deletion")
            raise NotFound(f'Hospital with ID {id} not found')
        
        logger.info(f"Found hospital to delete: {hospital.name}")
        
        db.session.delete(hospital)  # Delete the hospital record
        logger.info("Committing delete transaction")
        db.session.commit()  # Commit the changes
        
        logger.info(f"Successfully deleted hospital with ID: {id}")
        return jsonify({'message': 'Hospital deleted successfully'}), 200
    
    except NotFound as e:
        logger.warning(str(e))
        return jsonify({'error': str(e)}), 404  # Handle not found error
    
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of DB error
        error_msg = f"Database error in delete_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500  # Handle DB error
    
    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        error_msg = f"Unexpected error in delete_hospital: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
