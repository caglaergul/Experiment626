"""Data export routes."""
from flask import Blueprint, send_file
import csv
import io
from database import get_db_connection

bp = Blueprint('data', __name__)

def init_module():
    """Initialize module."""
    pass


@bp.route('/api/export/<team_id>', methods=['GET'])
def export_team_data(team_id):
    """Export all data for a team as CSV."""
    conn = get_db_connection()
    c = conn.cursor()

    # Get all data for the team
    c.execute('SELECT * FROM teams WHERE team_id = ?', (team_id,))
    team_data = c.fetchone()

    c.execute('SELECT * FROM messages WHERE team_id = ? ORDER BY timestamp', (team_id,))
    messages = c.fetchall()

    c.execute('SELECT * FROM ideas WHERE team_id = ? ORDER BY timestamp', (team_id,))
    ideas = c.fetchall()

    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write team info
    writer.writerow(['TEAM INFORMATION'])
    writer.writerow(['Team ID', 'Start Time', 'Final Idea', 'Submitted', 'Submit Time'])
    if team_data:
        writer.writerow(team_data[1:])
    writer.writerow([])

    # Write messages
    writer.writerow(['MESSAGES'])
    writer.writerow(['ID', 'Team ID', 'Participant ID', 'Role', 'Content', 'Timestamp', 'Tokens Used'])
    for msg in messages:
        writer.writerow(msg)
    writer.writerow([])

    # Write ideas
    writer.writerow(['IDEAS'])
    writer.writerow(['ID', 'Team ID', 'Participant ID', 'Idea Text', 'Timestamp'])
    for idea in ideas:
        writer.writerow(idea)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'team_{team_id}_data.csv'
    )
