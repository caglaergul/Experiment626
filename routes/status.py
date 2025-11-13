"""Online status, heartbeat, and timer routes."""
from flask import Blueprint, request, jsonify
from datetime import datetime
import time
from database import get_db_connection
from config import SESSION_DURATION_MINUTES, HEARTBEAT_TIMEOUT_SECONDS

bp = Blueprint('status', __name__)

# Module-level state
online_participants = None

def init_module(participants):
    """Initialize module with shared state."""
    global online_participants
    online_participants = participants


@bp.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Record a heartbeat from a participant."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')

    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400

    if team_id not in online_participants:
        online_participants[team_id] = {}

    online_participants[team_id][participant_id] = time.time()

    return jsonify({'success': True})


@bp.route('/api/online_status/<team_id>', methods=['GET'])
def get_online_status(team_id):
    """Get online status for all participants in a team."""
    if team_id not in online_participants:
        return jsonify({'online': {}})

    current_time = time.time()
    online = {}

    # Consider participant online if heartbeat received within last 5 seconds
    for participant_id, last_heartbeat in online_participants[team_id].items():
        online[participant_id] = (current_time - last_heartbeat) < HEARTBEAT_TIMEOUT_SECONDS

    return jsonify({'online': online})


@bp.route('/api/get_timer/<team_id>', methods=['GET'])
def get_timer(team_id):
    """Get the remaining time for a team's session."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT start_time FROM teams WHERE team_id = ?', (team_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return jsonify({'error': 'Team not found'}), 404

    # Parse the start time and calculate time remaining
    start_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
    elapsed_seconds = (datetime.now() - start_time).total_seconds()
    time_remaining = max(0, SESSION_DURATION_MINUTES * 60 - elapsed_seconds)

    return jsonify({
        'start_time': row[0],
        'time_remaining': int(time_remaining)
    })


@bp.route('/api/typing_metrics', methods=['POST'])
def update_typing_metrics():
    """Update typing metrics for a participant."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    field = data.get('field')  # 'title' or 'description'
    keystroke_count = data.get('keystroke_count', 0)
    active_typing_seconds = data.get('active_typing_seconds', 0)
    first_edit_time = data.get('first_edit_time')
    last_edit_time = data.get('last_edit_time')

    if not all([team_id, participant_id, field]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate field parameter to prevent SQL injection
    if field not in ['title', 'description']:
        return jsonify({'error': 'Invalid field parameter'}), 400

    # Validate participant_id to prevent SQL injection
    if participant_id not in ['1', '2']:
        return jsonify({'error': 'Invalid participant_id'}), 400

    # Safe: Use explicit mapping to avoid string interpolation in SQL
    # Mapping for participant-specific columns
    participant_field_columns = {
        ('1', 'title'): {
            'keystroke': 'p1_title_keystroke_count',
            'typing_seconds': 'p1_title_active_typing_seconds',
            'first_edit': 'p1_title_first_edit_time',
            'last_edit': 'p1_title_last_edit_time'
        },
        ('1', 'description'): {
            'keystroke': 'p1_description_keystroke_count',
            'typing_seconds': 'p1_description_active_typing_seconds',
            'first_edit': 'p1_description_first_edit_time',
            'last_edit': 'p1_description_last_edit_time'
        },
        ('2', 'title'): {
            'keystroke': 'p2_title_keystroke_count',
            'typing_seconds': 'p2_title_active_typing_seconds',
            'first_edit': 'p2_title_first_edit_time',
            'last_edit': 'p2_title_last_edit_time'
        },
        ('2', 'description'): {
            'keystroke': 'p2_description_keystroke_count',
            'typing_seconds': 'p2_description_active_typing_seconds',
            'first_edit': 'p2_description_first_edit_time',
            'last_edit': 'p2_description_last_edit_time'
        }
    }

    # Mapping for aggregate columns
    aggregate_field_columns = {
        'title': {
            'total_keystroke': 'total_title_keystroke_count',
            'total_typing_seconds': 'total_title_active_typing_seconds',
            'first_edit': 'title_first_edit_time',
            'last_edit': 'title_last_edit_time',
            'p1_keystroke': 'p1_title_keystroke_count',
            'p2_keystroke': 'p2_title_keystroke_count',
            'p1_typing_seconds': 'p1_title_active_typing_seconds',
            'p2_typing_seconds': 'p2_title_active_typing_seconds',
            'p1_first_edit': 'p1_title_first_edit_time',
            'p2_first_edit': 'p2_title_first_edit_time',
            'p1_last_edit': 'p1_title_last_edit_time',
            'p2_last_edit': 'p2_title_last_edit_time'
        },
        'description': {
            'total_keystroke': 'total_description_keystroke_count',
            'total_typing_seconds': 'total_description_active_typing_seconds',
            'first_edit': 'description_first_edit_time',
            'last_edit': 'description_last_edit_time',
            'p1_keystroke': 'p1_description_keystroke_count',
            'p2_keystroke': 'p2_description_keystroke_count',
            'p1_typing_seconds': 'p1_description_active_typing_seconds',
            'p2_typing_seconds': 'p2_description_active_typing_seconds',
            'p1_first_edit': 'p1_description_first_edit_time',
            'p2_first_edit': 'p2_description_first_edit_time',
            'p1_last_edit': 'p1_description_last_edit_time',
            'p2_last_edit': 'p2_description_last_edit_time'
        }
    }

    p_cols = participant_field_columns[(participant_id, field)]
    agg_cols = aggregate_field_columns[field]

    conn = get_db_connection()
    c = conn.cursor()

    # Update participant-specific metrics with hardcoded column names (safe from SQL injection)
    c.execute(f'''
        UPDATE teams
        SET {p_cols['keystroke']} = ?,
            {p_cols['typing_seconds']} = ?,
            {p_cols['first_edit']} = ?,
            {p_cols['last_edit']} = ?
        WHERE team_id = ?
    ''', (keystroke_count, active_typing_seconds, first_edit_time, last_edit_time, team_id))

    # Get both participants' data to calculate aggregates with hardcoded column names
    c.execute(f'''
        SELECT {agg_cols['p1_keystroke']}, {agg_cols['p2_keystroke']},
               {agg_cols['p1_typing_seconds']}, {agg_cols['p2_typing_seconds']},
               {agg_cols['p1_first_edit']}, {agg_cols['p2_first_edit']},
               {agg_cols['p1_last_edit']}, {agg_cols['p2_last_edit']}
        FROM teams WHERE team_id = ?
    ''', (team_id,))
    row = c.fetchone()

    if row:
        p1_keystrokes, p2_keystrokes, p1_typing, p2_typing, p1_first, p2_first, p1_last, p2_last = row

        # Calculate aggregates
        total_keystrokes = (p1_keystrokes or 0) + (p2_keystrokes or 0)
        total_typing = (p1_typing or 0) + (p2_typing or 0)

        # Find earliest first edit time
        first_times = [t for t in [p1_first, p2_first] if t]
        aggregate_first = min(first_times) if first_times else None

        # Find latest last edit time
        last_times = [t for t in [p1_last, p2_last] if t]
        aggregate_last = max(last_times) if last_times else None

        # Update aggregate metrics with hardcoded column names (safe from SQL injection)
        c.execute(f'''
            UPDATE teams
            SET {agg_cols['total_keystroke']} = ?,
                {agg_cols['total_typing_seconds']} = ?,
                {agg_cols['first_edit']} = ?,
                {agg_cols['last_edit']} = ?
            WHERE team_id = ?
        ''', (total_keystrokes, total_typing, aggregate_first, aggregate_last, team_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})
