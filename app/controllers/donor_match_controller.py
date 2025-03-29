from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app.models.donor_match_model import DonorMatch
from app.models.donor_model import Donor
from app.models.blood_request_model import BloodRequest
from app import db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, BadRequest
import requests
from geopy.distance import geodesic

# Define Blueprint for the Donor Match controller
donor_match_bp = Blueprint('donor_match_bp', __name__, url_prefix='/api/v1/donor_matches')

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

@donor_match_bp.route('/', methods=['GET'])
def get_donor_matches():
    try:
        matches = DonorMatch.query.all()
        matches_data = []
        for match in matches:
            match_data = match.to_dict()
            donor = Donor.query.get(match.donor_id)
            blood_request = BloodRequest.query.get(match.request_id)
            
            if donor:
                match_data['donor_details'] = {
                    'name': donor.name,
                    'blood_type': donor.blood_type,
                    'location': donor.location,
                    'contact': donor.phone,
                    'availability_status': donor.availability_status,
                    'last_donation_date': donor.last_donation_date.isoformat() if donor.last_donation_date else None
                }
            if blood_request:
                match_data['request_details'] = {
                    'patient_name': blood_request.name,  # Changed from patient_name
                    'blood_type': blood_request.blood_type,
                    'hospital': blood_request.hospital.name if blood_request.hospital else None,  # Changed from hospital_name
                    'urgency': blood_request.urgency_level
                }
            matches_data.append(match_data)
            
        return jsonify(matches_data), 200
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500

@donor_match_bp.route('/<int:id>', methods=['GET'])
def get_donor_match(id):
    try:
        match = DonorMatch.query.get(id)
        if not match:
            raise NotFound('Donor match not found')
        
        match_data = match.to_dict()
        donor = Donor.query.get(match.donor_id)
        blood_request = BloodRequest.query.get(match.request_id)
        
        if donor:
            match_data['donor_details'] = {
                'name': donor.name,
                'blood_type': donor.blood_type,
                'location': donor.location,
                'contact': donor.phone,
                'availability_status': donor.availability_status,
                'last_donation_date': donor.last_donation_date.isoformat() if donor.last_donation_date else None
            }
        
        if blood_request:
            match_data['request_details'] = {
                'patient_name': blood_request.name,  # Changed
                'blood_type': blood_request.blood_type,
                'hospital': blood_request.hospital.name if blood_request.hospital else None,  # Changed
                'urgency': blood_request.urgency_level,
                'location': blood_request.location
            }
            
            if blood_request.location and donor and donor.location:
                try:
                    req_lat, req_long = map(float, blood_request.location.split(','))
                    donor_lat, donor_long = map(float, donor.location.split(','))
                    distance = geodesic((req_lat, req_long), (donor_lat, donor_long)).km
                    match_data['distance_km'] = round(distance, 2)
                except:
                    pass
        
        return jsonify(match_data), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500

@donor_match_bp.route('/auto-match/<int:request_id>', methods=['POST'])
def auto_match_donors(request_id):
    try:
        blood_request = BloodRequest.query.get(request_id)
        if not blood_request:
            raise NotFound('Blood request not found')
        
        compatible_types = get_compatible_blood_types(blood_request.blood_type)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        # Base query for eligible donors
        base_query = Donor.query.filter(
            Donor.blood_type.in_(compatible_types),
            Donor.availability_status == True,
            (Donor.last_donation_date == None) | 
            (Donor.last_donation_date < cutoff_date)
        )
        
        donors_to_match = []
        if blood_request.location:
            try:
                req_lat, req_long = map(float, blood_request.location.split(','))
                all_donors = base_query.filter(Donor.location.isnot(None)).all()
                
                nearby_donors = []
                for donor in all_donors:
                    try:
                        donor_lat, donor_long = map(float, donor.location.split(','))
                        distance = geodesic((req_lat, req_long), (donor_lat, donor_long)).km
                        if distance <= 50:
                            donor.distance = distance
                            nearby_donors.append(donor)
                    except:
                        continue
                
                nearby_donors.sort(key=lambda x: x.distance)
                donors_to_match.extend(nearby_donors)
                
                other_donors = base_query.filter(
                    ~Donor.id.in_([d.id for d in nearby_donors])
                ).all()
                donors_to_match.extend(other_donors)
            except:
                donors_to_match = base_query.all()
        else:
            donors_to_match = base_query.all()
        
        matches_created = []
        for donor in donors_to_match:
            existing_match = DonorMatch.query.filter_by(
                request_id=blood_request.id,
                donor_id=donor.id
            ).first()
            
            if not existing_match:
                new_match = DonorMatch(
                    request_id=blood_request.id,
                    donor_id=donor.id,
                    status='Pending',
                    notified_at=datetime.utcnow()
                )
                db.session.add(new_match)
                matches_created.append((new_match, donor))
        
        db.session.commit()
        
        response = {
            'request_details': {
                'request_id': blood_request.id,
                'patient_name': blood_request.name,  # Changed
                'blood_type': blood_request.blood_type,
                'location': blood_request.location,
                'hospital': blood_request.hospital.name if blood_request.hospital else None,  # Changed
                'urgency': blood_request.urgency_level
            },
            'matches': [{
                'match_id': match.id,
                'donor_id': donor.id,
                'donor_name': donor.name,
                'donor_blood_type': donor.blood_type,
                'donor_location': donor.location,
                'donor_contact': donor.phone,
                'donor_availability': donor.availability_status,
                'last_donation_date': donor.last_donation_date.isoformat() if donor.last_donation_date else None,
                'status': match.status,
                'match_date': match.notified_at.isoformat(),
                'distance_km': getattr(donor, 'distance', None)
            } for match, donor in matches_created]
        }
        
        # Send notifications
        for match, donor in matches_created:
            try:
                message = f"Hello {donor.name}, you've been matched with a blood request. " \
                         f"Blood type needed: {blood_request.blood_type}, " \
                         f"Hospital: {blood_request.hospital.name if blood_request.hospital else 'Unknown'}, " f"Urgency: {blood_request.urgency_level}."
                
                requests.post(
                    "http://localhost:5000/api/v1/notifications/",
                    json={
                        'donor_id': donor.id,
                        'request_id': blood_request.id,
                        'message': message
                    }
                )
                
                match.status = 'Notified'
                db.session.commit()
            except Exception as e:
                print(f"Error sending notification: {str(e)}")
        
        return jsonify(response), 201
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@donor_match_bp.route('/for-request/<int:request_id>', methods=['GET'])
def get_matches_for_request(request_id):
    try:
        blood_request = BloodRequest.query.get(request_id)
        if not blood_request:
            raise NotFound('Blood request not found')
        
        matches = DonorMatch.query.filter_by(request_id=request_id).all()
        
        response = {
            'request_details': {
                'patient_name': blood_request.name,  # Changed
                'blood_type': blood_request.blood_type,
                'hospital': blood_request.hospital.name if blood_request.hospital else None,  # Changed
                'urgency': blood_request.urgency_level
            },
            'matches': []
        }
        
        for match in matches:
            donor = Donor.query.get(match.donor_id)
            if not donor:
                continue
                
            match_info = {
                'match_id': match.id,
                'donor_name': donor.name,
                'donor_blood_type': donor.blood_type,
                'donor_location': donor.location,
                'donor_availability': donor.availability_status,
                'status': match.status,
                'matched_at': match.notified_at.isoformat()
            }
            
            if blood_request.location and donor.location:
                try:
                    req_lat, req_long = map(float, blood_request.location.split(','))
                    donor_lat, donor_long = map(float, donor.location.split(','))
                    distance = geodesic((req_lat, req_long), (donor_lat, donor_long)).km
                    match_info['distance_km'] = round(distance, 2)
                except:
                    pass
            
            response['matches'].append(match_info)
        
        return jsonify(response), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred'}), 500

@donor_match_bp.route('/<int:id>', methods=['PUT'])
def update_donor_match(id):
    try:
        data = request.get_json()
        if not data:
            raise BadRequest('No input data provided')
            
        match = DonorMatch.query.get(id)
        if not match:
            raise NotFound('Donor match not found')
            
        previous_status = match.status
        
        if 'status' in data:
            match.status = data['status']
        
        db.session.commit()
        
        if 'status' in data and previous_status != data['status']:
            try:
                donor = Donor.query.get(match.donor_id)
                blood_request = BloodRequest.query.get(match.request_id)
                
                if donor and blood_request:
                    if data['status'] == 'Accepted':
                        message = f"Thank you for accepting to donate for {blood_request.name} at {blood_request.hospital.name if blood_request.hospital else 'the hospital'}."  # Changed
                        blood_request.status = 'Matched'
                    elif data['status'] == 'Declined':
                        message = f"You declined the donation request for {blood_request.name}."  # Changed
                    elif data['status'] == 'Completed':
                        message = f"Thank you for your donation! You helped save a life at {blood_request.hospital.name if blood_request.hospital else 'the hospital'}."  # Changed
                    else:
                        message = f"Your donation status has been updated to: {data['status']}"
                    
                    db.session.commit()
                    
                    requests.post(
                        "http://localhost:5000/api/v1/notifications/",
                        json={
                            'donor_id': donor.id,
                            'request_id': blood_request.id,
                            'message': message
                        }
                    )
            except Exception as e:
                print(f"Error handling status change: {str(e)}")
        
        return jsonify(match.to_dict()), 200
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

@donor_match_bp.route('/<int:id>', methods=['DELETE'])
def delete_donor_match(id):
    try:
        match = DonorMatch.query.get(id)
        if not match:
            raise NotFound('Donor match not found')
            
        db.session.delete(match)
        db.session.commit()
            
        return jsonify({'message': 'Donor match deleted successfully'}), 200
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500