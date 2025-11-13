"""Chat and messaging routes."""
from flask import Blueprint, request, jsonify
import openai
from database import get_db_connection
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS

bp = Blueprint('chat', __name__)

# Module-level state
active_teams = None

def init_module(teams):
    """Initialize module with shared state."""
    global active_teams
    active_teams = teams
    # Set OpenAI API key
    openai.api_key = OPENAI_API_KEY


@bp.route('/api/messages/<team_id>', methods=['GET'])
def get_messages(team_id):
    """Get messages for a team since a specific message ID."""
    since_id = request.args.get('since', 0, type=int)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, role, content, participant_id, timestamp
        FROM messages WHERE team_id = ? AND id > ? ORDER BY id ASC
    ''', (team_id, since_id))
    rows = c.fetchall()
    conn.close()

    messages = [{'id': r[0], 'role': r[1], 'content': r[2], 'participant_id': r[3], 'timestamp': r[4]} for r in rows]
    return jsonify({'messages': messages})


@bp.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat message and get AI response."""
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    user_message = data.get('message')

    if not all([team_id, participant_id, user_message]):
        return jsonify({'error': 'Missing required fields'}), 400

    if team_id not in active_teams:
        active_teams[team_id] = {'messages': []}

    team_session = active_teams[team_id]
    team_session['messages'].append({'role': 'user', 'content': user_message})

    # Save user message to database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO messages (team_id, participant_id, role, content) VALUES (?, ?, ?, ?)',
              (team_id, participant_id, 'user', user_message))
    conn.commit()
    conn.close()

    try:
        # Get AI response
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=team_session['messages'],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )

        assistant_message = response['choices'][0]['message']['content']
        tokens_used = response['usage']['total_tokens']

        team_session['messages'].append({'role': 'assistant', 'content': assistant_message})

        # Save assistant message to database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO messages (team_id, participant_id, role, content, tokens_used) VALUES (?, ?, ?, ?, ?)',
                  (team_id, None, 'assistant', assistant_message, tokens_used))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'response': assistant_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
