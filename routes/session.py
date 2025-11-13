"""Session management routes."""
from flask import Blueprint, request, jsonify, render_template
import sqlite3
from database import get_db_connection

bp = Blueprint('session', __name__)

# Module-level state (initialized by register_routes)
active_teams = None
team_approvals = None
online_participants = None

def init_module(teams, approvals, participants):
    """Initialize module with shared state."""
    global active_teams, team_approvals, online_participants
    active_teams = teams
    team_approvals = approvals
    online_participants = participants


@bp.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')


@bp.route('/api/start_session', methods=['POST'])
def start_session():
    """Start a new team brainstorming session."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')

    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO teams (team_id) VALUES (?)', (team_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        # Team already exists, which is fine
        pass
    conn.close()

    if team_id not in active_teams:
        active_teams[team_id] = {'messages': []}

    return jsonify({'success': True, 'team_id': team_id, 'participant_id': participant_id})
