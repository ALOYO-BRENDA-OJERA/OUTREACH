from flask import Blueprint, request, jsonify
from app.models.blood_request_model import BloodRequest
from app.models.hospital_model import Hospital
from app import db
from werkzeug.exceptions import NotFound, BadRequest
from sqlalchemy.exc import SQLAlchemyError

blood_request_bp = Blueprint('blood_request', __name__, url_prefix='/api/v1/blood_requests')

# GET all blood requests
@blood_request_bp.route('/', methods=['GET'])
def get_blood_requests():

    try:
        blood_requests = BloodRequest.query.all()
        return jsonify([request.to_dict() for request in blood_requests]), 200
    except SQLAlchemyError:
        return jsonify({'error': 'Database error occurred'}), 500

# GET a specific blood request by ID
@blood_request_bp.route('/<int:id>', methods=['GET'])
def get_blood_request(id):
    try:
        blood_request = BloodRequest.query.get(id)
        if not blood_request:
            raise NotFound('Blood request not found')
        return jsonify(blood_request.to_dict()), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError:
        return jsonify({'error': 'Database error occurred'}), 500

# POST a new blood request
@blood_request_bp.route('/create_blood_request', methods=['POST'])
def create_blood_request():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest('No input data provided')
        
        # Validate incoming data
        required_fields = ['name', 'city', 'contact_number', 'hospital_id', 'blood_type', 'urgency_level']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f'Missing required field: {field}')
        
        # Verify hospital exists
        hospital = Hospital.query.get(data['hospital_id'])
        if not hospital:
            raise BadRequest(f"Hospital with ID {data['hospital_id']} not found")
        
        # Create a new blood request
        new_request = BloodRequest(
            name=data['name'],
            city=data['city'],
            location=data.get('location'),
            contact_number=data['contact_number'],
            hospital_id=data['hospital_id'],
            blood_type=data['blood_type'],
            units_needed=data.get('units_needed', 1),
            urgency_level=data['urgency_level'],
            status=data.get('status', 'Open')
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return jsonify(new_request.to_dict()), 201
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error occurred: {str(e)}'}), 500

# PUT to update an existing blood request
@blood_request_bp.route('/<int:id>', methods=['PUT'])
def update_blood_request(id):
    try:
        data = request.get_json()
        if not data:
            raise BadRequest('No input data provided')
        
        # Find the blood request
        blood_request = BloodRequest.query.get(id)
        if not blood_request:
            raise NotFound('Blood request not found')
        
        # Update fields
        if 'name' in data:
            blood_request.name = data['name']
        if 'city' in data:
            blood_request.city = data['city']
        if 'location' in data:
            blood_request.location = data['location']
        if 'contact_number' in data:
            blood_request.contact_number = data['contact_number']
        if 'hospital_id' in data:
            # Verify hospital exists
            hospital = Hospital.query.get(data['hospital_id'])
            if not hospital:
                raise BadRequest(f"Hospital with ID {data['hospital_id']} not found")
            blood_request.hospital_id = data['hospital_id']
        if 'blood_type' in data:
            blood_request.blood_type = data['blood_type']
        if 'units_needed' in data:
            blood_request.units_needed = data['units_needed']
        if 'urgency_level' in data:
            blood_request.urgency_level = data['urgency_level']
        if 'status' in data:
            blood_request.status = data['status']
        
        db.session.commit()
        
        return jsonify(blood_request.to_dict()), 200
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

# DELETE a blood request
@blood_request_bp.route('/<int:id>', methods=['DELETE'])
def delete_blood_request(id):
    try:
        blood_request = BloodRequest.query.get(id)
        if not blood_request:
            raise NotFound('Blood request not found')
        
        db.session.delete(blood_request)
        db.session.commit()
        
        return jsonify({'message': 'Blood request deleted successfully'}), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    
    
    # In your blood request controller
@blood_request_bp.route('/<int:id>', methods=['GET'])
def get_blood_request(id):
    try:
        request = BloodRequest.query.get(id)
        if not request:
            raise NotFound('Blood request not found')
            
        # Get the match count
        match_count = DonorMatch.query.filter_by(request_id=id).count()
        
        response = request.to_dict()
        response['match_count'] = match_count
        
        return jsonify(response), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500

