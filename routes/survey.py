"""Survey routes for collecting participant feedback."""
from flask import Blueprint, request, jsonify
from database import get_db_connection

bp = Blueprint('survey', __name__)

def init_module():
    """Initialize module."""
    pass


@bp.route('/api/survey_page1', methods=['POST'])
def save_survey_page1():
    """Save survey page 1 responses."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')

    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400

    # Validate participant_id to prevent SQL injection
    if participant_id not in ['1', '2']:
        return jsonify({'error': 'Invalid participant_id'}), 400

    # Validate all responses are from allowed values
    allowed_responses = ['Strongly Disagree', 'Disagree', 'Neither Disagree nor Agree', 'Agree', 'Strongly Agree']
    for i in range(1, 11):
        q_key = f'q{i}'
        if data.get(q_key) not in allowed_responses:
            return jsonify({'error': f'Invalid response for {q_key}'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO survey_page1 (team_id, participant_id, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, participant_id, data.get('q1'), data.get('q2'), data.get('q3'), data.get('q4'),
          data.get('q5'), data.get('q6'), data.get('q7'), data.get('q8'), data.get('q9'), data.get('q10')))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@bp.route('/api/survey_page2', methods=['POST'])
def save_survey_page2():
    """Save survey page 2 responses."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    employment_status = data.get('employment_status')
    major_field = data.get('major_field')
    major_other = data.get('major_other', '')
    age = data.get('age')
    gender = data.get('gender')

    if not all([team_id, participant_id, employment_status, major_field, age, gender]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate participant_id
    if participant_id not in ['1', '2']:
        return jsonify({'error': 'Invalid participant_id'}), 400

    # Validate employment_status
    if employment_status not in ['Undergraduate student', 'Graduate student']:
        return jsonify({'error': 'Invalid employment status'}), 400

    # Validate major_field
    if major_field not in ['STEM', 'Business and Economics', 'Arts and Humanities', 'Other']:
        return jsonify({'error': 'Invalid major field'}), 400

    # Validate age is integer
    try:
        age_int = int(age)
        if age_int < 18 or age_int > 100:
            return jsonify({'error': 'Age must be between 18 and 100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid age'}), 400

    # Validate gender
    valid_genders = ['Female', 'Male', 'Transgender Female', 'Transgender Male',
                     'Gender Variant / Non-Conforming', 'Other', 'Prefer not to answer']
    if gender not in valid_genders:
        return jsonify({'error': 'Invalid gender'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO survey_page2 (team_id, participant_id, employment_status, major_field, major_other, age, gender)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, participant_id, employment_status, major_field, major_other, age_int, gender))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@bp.route('/api/survey_page3', methods=['POST'])
def save_survey_page3():
    """Save survey page 3 responses (contact information)."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    first_last_name = data.get('first_last_name', '').strip()
    address_line1 = data.get('address_line1', '').strip()
    address_line2 = data.get('address_line2', '').strip()
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    postal_code = data.get('postal_code', '').strip()

    if not all([team_id, participant_id, first_last_name, address_line1, city, state, postal_code]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate participant_id
    if participant_id not in ['1', '2']:
        return jsonify({'error': 'Invalid participant_id'}), 400

    # Validate state is 2 letters
    if len(state) != 2 or not state.isalpha():
        return jsonify({'error': 'State must be 2 letters'}), 400

    # Validate postal code is exactly 5 digits
    if len(postal_code) != 5 or not postal_code.isdigit():
        return jsonify({'error': 'Postal code must be exactly 5 digits'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO survey_page3 (team_id, participant_id, first_last_name, address_line1, address_line2, city, state, postal_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, participant_id, first_last_name, address_line1, address_line2, city, state, postal_code))
    conn.commit()
    conn.close()

    return jsonify({'success': True})
