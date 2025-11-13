"""Routes package for Team Brainstorming Study application."""
from . import session, chat, ideas, status, survey, data

def register_routes(app, active_teams, team_approvals, online_participants):
    """Register all route blueprints with the Flask app."""
    # Pass shared state to route modules
    session.init_module(active_teams, team_approvals, online_participants)
    chat.init_module(active_teams)
    ideas.init_module()
    status.init_module(online_participants)
    survey.init_module()
    data.init_module()

    # Register blueprints
    app.register_blueprint(session.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(ideas.bp)
    app.register_blueprint(status.bp)
    app.register_blueprint(survey.bp)
    app.register_blueprint(data.bp)
