"""Ideas management routes."""
from flask import Blueprint, request, jsonify
from database import get_db_connection

bp = Blueprint('ideas', __name__)

# Module-level state
active_teams = {}
team_approvals = {}

def init_module():
    """Initialize module."""
    pass


@bp.route('/api/ideas/<team_id>', methods=['GET'])
def get_ideas(team_id):
    """Get all ideas for a team since a specific idea ID."""
    since_id = request.args.get('since', 0, type=int)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, participant_id, idea_text, timestamp
        FROM ideas WHERE team_id = ? AND id > ? ORDER BY id ASC
    ''', (team_id, since_id))
    rows = c.fetchall()
    conn.close()

    ideas = [{'id': r[0], 'participant_id': r[1], 'idea_text': r[2], 'timestamp': r[3]} for r in rows]
    return jsonify({'ideas': ideas})


@bp.route('/api/add_idea', methods=['POST'])
def add_idea():
    """Add a new idea for a team."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    idea_text = data.get('idea_text')

    if not all([team_id, participant_id, idea_text]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO ideas (team_id, participant_id, idea_text) VALUES (?, ?, ?)',
              (team_id, participant_id, idea_text))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@bp.route('/api/final_idea/<team_id>', methods=['GET'])
def get_final_idea(team_id):
    """Get the final idea for a team."""
    # Check in-memory store first
    from routes.session import active_teams
    if team_id in active_teams and 'final_data' in active_teams[team_id]:
        return jsonify(active_teams[team_id]['final_data'])

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT final_idea FROM teams WHERE team_id = ?', (team_id,))
    row = c.fetchone()
    conn.close()

    return jsonify({
        'title': '',
        'description': '',
        'final_idea': row[0] if row and row[0] else ''
    })


@bp.route('/api/update_final', methods=['POST'])
def update_final():
    """Update the final idea for a team."""
    data = request.json
    team_id = data.get('team_id')
    title = data.get('title', '')
    description = data.get('description', '')

    if not team_id:
        return jsonify({'error': 'Team ID required'}), 400

    # Store in memory for real-time sync
    from routes.session import active_teams
    if team_id not in active_teams:
        active_teams[team_id] = {'messages': []}

    active_teams[team_id]['final_data'] = {
        'title': title,
        'description': description
    }

    # Also update database
    final_idea_combined = f"Title: {title}\n\nDescription: {description}"
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE teams SET final_idea = ? WHERE team_id = ?', (final_idea_combined, team_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@bp.route('/api/submit', methods=['POST'])
def submit():
    """Submit the final idea for a team."""
    data = request.json
    team_id = data.get('team_id')
    final_idea = data.get('final_idea')

    if not team_id or not final_idea:
        return jsonify({'error': 'Team ID and final idea required'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE teams
        SET final_idea = ?, submitted = 1, submit_time = CURRENT_TIMESTAMP
        WHERE team_id = ?
    ''', (final_idea, team_id))
    conn.commit()
    conn.close()

    # Mark as submitted in memory too for real-time sync
    from routes.session import team_approvals
    if team_id in team_approvals:
        team_approvals[team_id]['submitted'] = True

    return jsonify({'success': True})


@bp.route('/api/set_approval', methods=['POST'])
def set_approval():
    """Set approval status for a participant."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = str(data.get('participant_id'))
    approved = data.get('approved', False)

    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400

    from routes.session import team_approvals
    if team_id not in team_approvals:
        team_approvals[team_id] = {'1': False, '2': False}

    team_approvals[team_id][participant_id] = approved

    return jsonify({'success': True, 'approvals': team_approvals[team_id]})


@bp.route('/api/get_approvals/<team_id>', methods=['GET'])
def get_approvals(team_id):
    """Get approval status for a team."""
    from routes.session import team_approvals
    if team_id not in team_approvals:
        team_approvals[team_id] = {'1': False, '2': False, 'submitted': False}

    return jsonify({
        'approvals': team_approvals[team_id],
        'submitted': team_approvals[team_id].get('submitted', False)
    })
