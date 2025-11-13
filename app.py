"""
Team Brainstorming Study - Main Application

A Flask-based web application for conducting team brainstorming sessions
with AI assistance (ChatGPT) and real-time collaboration features.
"""
from flask import Flask
from flask_cors import CORS
from database import init_db
from routes import register_routes
from config import DEBUG, HOST, PORT

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

# Global state for active sessions
# These are shared across routes to maintain session state
active_teams = {}  # Store active team sessions: {team_id: {'messages': [], 'final_data': {}}}
team_approvals = {}  # Track approvals: {team_id: {'1': bool, '2': bool, 'submitted': bool}}
online_participants = {}  # Track online participants: {team_id: {participant_id: last_heartbeat_time}}

# Register all route blueprints
register_routes(app, active_teams, team_approvals, online_participants)

if __name__ == '__main__':
    print("=" * 60)
    print("Team Brainstorming Study - Server Starting")
    print("=" * 60)
    print(f"Server running on http://{HOST}:{PORT}")
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    app.run(host=HOST, port=PORT, debug=DEBUG)
