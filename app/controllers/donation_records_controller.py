from flask import Blueprint, request, jsonify
from app.models.donation_record_model import DonationRecord
from app.models.donor_model import Donor
from app.models.hospital_model import Hospital
from app import db
from werkzeug.exceptions import NotFound, BadRequest
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime, timedelta
import traceback

# Define Blueprint for the donation record controller
donation_blueprint = Blueprint('donation', __name__, url_prefix='/api/v1/donor_records')

# GET all donation records
@donation_blueprint.route('/records', methods=['GET'])
def get_donation_records():
    try:
        donation_records = DonationRecord.query.all()
        if not donation_records:
            return jsonify({"message": "No donation records found", "data": []}), 200
        return jsonify([record.to_dict() for record in donation_records]), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# GET donation records for a specific donor
@donation_blueprint.route('/records/donor/<int:donor_id>', methods=['GET'])
def get_donor_donation_records(donor_id):
    try:
        # Check if donor exists
        donor = Donor.query.get(donor_id)
        if not donor:
            raise NotFound(f'Donor with ID {donor_id} not found')
            
        donation_records = DonationRecord.query.filter_by(donor_id=donor_id).all()
        if not donation_records:
            return jsonify({"message": f"No donation records found for donor ID {donor_id}", "data": []}), 200
        return jsonify([record.to_dict() for record in donation_records]), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# GET donation records for a specific hospital
@donation_blueprint.route('/records/hospital/<int:hospital_id>', methods=['GET'])
def get_hospital_donation_records(hospital_id):
    try:
        # Check if hospital exists
        hospital = Hospital.query.get(hospital_id)
        if not hospital:
            raise NotFound(f'Hospital with ID {hospital_id} not found')
            
        donation_records = DonationRecord.query.filter_by(hospital_id=hospital_id).all()
        if not donation_records:
            return jsonify({"message": f"No donation records found for hospital ID {hospital_id}", "data": []}), 200
        return jsonify([record.to_dict() for record in donation_records]), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# GET a specific donation record by ID
@donation_blueprint.route('/records/<int:id>', methods=['GET'])
def get_donation_record(id):
    try:
        donation_record = DonationRecord.query.get(id)
        if not donation_record:
            raise NotFound(f'Donation record with ID {id} not found')
        return jsonify(donation_record.to_dict()), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# POST a new donation record
@donation_blueprint.route('/create_record', methods=['POST'])
def create_donation_record():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest('No input data provided')
        
        # Validate required fields
        required_fields = ['donor_id', 'hospital_id', 'blood_type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise BadRequest(f'Missing required fields: {", ".join(missing_fields)}')
        
        # Validate data types
        if not isinstance(data['donor_id'], int):
            raise BadRequest('donor_id must be an integer')
        if not isinstance(data['hospital_id'], int):
            raise BadRequest('hospital_id must be an integer')
        if not isinstance(data['blood_type'], str):
            raise BadRequest('blood_type must be a string')
        
        # Verify donor exists
        donor = Donor.query.get(data['donor_id'])
        if not donor:
            raise NotFound(f"Donor with ID {data['donor_id']} not found")
        
        # Verify hospital exists
        hospital = Hospital.query.get(data['hospital_id'])
        if not hospital:
            raise NotFound(f"Hospital with ID {data['hospital_id']} not found")
        
        # Verify blood type matches donor's blood type
        if data['blood_type'] != donor.blood_type:
            raise BadRequest(f"Blood type {data['blood_type']} does not match donor's blood type {donor.blood_type}")
        
        # Check if donor is eligible to donate (not donated recently)
        recent_donation = DonationRecord.query.filter_by(donor_id=data['donor_id']).order_by(
            DonationRecord.donated_at.desc()
        ).first()
        
        current_time = datetime.utcnow()
        if recent_donation:
            # Make sure both datetimes are naive (no timezone info)
            next_eligible_naive = recent_donation.next_eligible_donation.replace(tzinfo=None) if recent_donation.next_eligible_donation.tzinfo else recent_donation.next_eligible_donation
            if next_eligible_naive > current_time:
                return jsonify({
                    'status': 'medical_restriction',
                    'message': 'Donor is not medically eligible to donate at this time',
                    'next_eligible_date': recent_donation.next_eligible_donation.isoformat(),
                    'days_until_eligible': (next_eligible_naive - current_time).days,
                    'info': 'Medical guidelines require a minimum waiting period between donations to ensure donor health'
                }), 200  # Using 200 instead of 400 as this is a valid medical response, not an error
        
        # Calculate next eligible donation date (56 days later by default)
        next_eligible = current_time + timedelta(days=56)
        date_adjusted = False
        provided_date = None
        
        # Override with provided date if it exists
        if 'next_eligible_donation' in data:
            try:
                if isinstance(data['next_eligible_donation'], str):
                    # Parse the string to datetime, ensuring it's naive (no timezone)
                    provided_date = datetime.fromisoformat(data['next_eligible_donation'].replace('Z', ''))
                    if provided_date.tzinfo:
                        provided_date = provided_date.replace(tzinfo=None)
                else:
                    provided_date = data['next_eligible_donation']
                    if provided_date.tzinfo:
                        provided_date = provided_date.replace(tzinfo=None)
                
                # Check if date is less than medical guideline
                min_date = current_time + timedelta(days=56)
                
                if provided_date < min_date:
                    # Auto-adjust to comply with medical guidelines
                    next_eligible = min_date
                    date_adjusted = True
                else:
                    next_eligible = provided_date
                    
            except ValueError:
                raise BadRequest('Invalid date format for next_eligible_donation. Use ISO format (YYYY-MM-DDTHH:MM:SS)')
        
        # Create donation record
        donation_record = DonationRecord(
            donor_id=data['donor_id'],
            hospital_id=data['hospital_id'],
            blood_type=data['blood_type'],
            next_eligible_donation=next_eligible
        )
        
        # Update donor availability status
        donor.availability_status = False
        
        db.session.add(donation_record)
        db.session.commit()
        
        # Prepare response
        response_data = {
            'message': 'Donation record created successfully',
            'data': donation_record.to_dict()
        }
        
        # Add medical note if date was adjusted
        if date_adjusted:
            response_data['medical_note'] = 'The next eligible donation date was adjusted to comply with the medical guideline of 56 days between donations.'
            response_data['provided_date'] = provided_date.isoformat() if provided_date else None
            response_data['adjusted_date'] = next_eligible.isoformat()
        
        return jsonify(response_data), 201
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': f'Database integrity error: {str(e)}'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        db.session.rollback()
        traceback_str = traceback.format_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}', 'traceback': traceback_str}), 500

# PUT to update an existing donation record
@donation_blueprint.route('/records/<int:id>', methods=['PUT'])
def update_donation_record(id):
    try:
        data = request.get_json()
        if not data:
            raise BadRequest('No input data provided')
        
        # Find the donation record by ID
        donation_record = DonationRecord.query.get(id)
        if not donation_record:
            raise NotFound(f'Donation record with ID {id} not found')
        
        # Validate data if provided
        if 'blood_type' in data:
            if not isinstance(data['blood_type'], str):
                raise BadRequest('blood_type must be a string')
            
            # If blood type is changed, verify it matches donor's blood type
            donor = Donor.query.get(donation_record.donor_id)
            if data['blood_type'] != donor.blood_type:
                raise BadRequest(f"Blood type {data['blood_type']} does not match donor's blood type {donor.blood_type}")
            
            donation_record.blood_type = data['blood_type']
            
        if 'next_eligible_donation' in data:
            try:
                current_time = datetime.utcnow()
                
                if isinstance(data['next_eligible_donation'], str):
                    # Parse the string to datetime, ensuring it's naive (no timezone)
                    provided_date = datetime.fromisoformat(data['next_eligible_donation'].replace('Z', ''))
                    if provided_date.tzinfo:
                        provided_date = provided_date.replace(tzinfo=None)
                else:
                    provided_date = data['next_eligible_donation']
                    if provided_date.tzinfo:
                        provided_date = provided_date.replace(tzinfo=None)
                
                # Ensure donated_at is naive for comparison
                donated_at = donation_record.donated_at
                if donated_at.tzinfo:
                    donated_at = donated_at.replace(tzinfo=None)
                
                # Ensure next_eligible is at least 56 days after donation date
                min_date = donated_at + timedelta(days=56)
                date_adjusted = False
                
                if provided_date < min_date:
                    # Auto-adjust to comply with medical guidelines
                    next_eligible = min_date
                    date_adjusted = True
                else:
                    next_eligible = provided_date
                
                donation_record.next_eligible_donation = next_eligible
                
                # Prepare response data for after commit
                response_data = {
                    'message': 'Donation record updated successfully',
                    'data': None  # Will be populated after commit
                }
                
                if date_adjusted:
                    response_data['medical_note'] = 'The next eligible donation date was adjusted to comply with the medical guideline of 56 days between donations.'
                    response_data['provided_date'] = provided_date.isoformat()
                    response_data['adjusted_date'] = next_eligible.isoformat()
                
            except ValueError:
                raise BadRequest('Invalid date format for next_eligible_donation. Use ISO format (YYYY-MM-DDTHH:MM:SS)')
        
        db.session.commit()
        
        # Get updated data after commit
        response_data = {
            'message': 'Donation record updated successfully',
            'data': donation_record.to_dict()
        }
        
        # Add medical note if date was adjusted (defined in the if block above)
        if 'medical_note' in locals().get('response_data', {}):
            response_data['medical_note'] = locals()['response_data']['medical_note']
            response_data['provided_date'] = locals()['response_data']['provided_date']
            response_data['adjusted_date'] = locals()['response_data']['adjusted_date']
        
        return jsonify(response_data), 200
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        db.session.rollback()
        traceback_str = traceback.format_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}', 'traceback': traceback_str}), 500

# DELETE a donation record
@donation_blueprint.route('/records/<int:id>', methods=['DELETE'])
def delete_donation_record(id):
    try:
        donation_record = DonationRecord.query.get(id)
        if not donation_record:
            raise NotFound(f'Donation record with ID {id} not found')
            
        # Store donor_id before deleting the record
        donor_id = donation_record.donor_id
            
        db.session.delete(donation_record)
            
        # Check if this was the donor's most recent donation
        # If so, update their availability status
        most_recent_donation = DonationRecord.query.filter_by(donor_id=donor_id).order_by(
            DonationRecord.donated_at.desc()
        ).first()
        
        # Get the donor
        donor = Donor.query.get(donor_id)
        
        # Update donor availability based on most recent donation
        if most_recent_donation:
            current_time = datetime.utcnow()
            next_eligible_naive = most_recent_donation.next_eligible_donation
            if next_eligible_naive.tzinfo:
                next_eligible_naive = next_eligible_naive.replace(tzinfo=None)
                
            # If the next eligible date is in the future, donor is not available
            donor.availability_status = next_eligible_naive <= current_time
        else:
            # If no donations left, donor is available
            donor.availability_status = True
            
        db.session.commit()
        
        return jsonify({
            'message': f'Donation record with ID {id} successfully deleted',
            'donor_status_updated': True,
            'donor_now_available': donor.availability_status
        }), 200
            
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        error_message = str(e)
        return jsonify({'error': f'Database error occurred: {error_message}'}), 500
    except Exception as e:
        db.session.rollback()
        traceback_str = traceback.format_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}', 'traceback': traceback_str}), 500
