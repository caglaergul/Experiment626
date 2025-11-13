# Team Brainstorming Study Application

A Flask-based web application for conducting team brainstorming sessions with AI assistance (ChatGPT) and real-time collaboration features.

## Project Structure

The application has been refactored into a modular structure for better maintainability:

```
Experiment626/
├── app.py                    # Main application entry point
├── app_original.py           # Backup of original monolithic app.py
├── config.py                 # Configuration and environment variables
├── database.py               # Database initialization and utilities
├── study_data.db            # SQLite database (generated at runtime)
├── templates/
│   └── index.html           # Main HTML template with CSS and JavaScript
└── routes/
    ├── __init__.py          # Routes package initialization
    ├── session.py           # Session management routes
    ├── chat.py              # Chat and messaging with AI
    ├── ideas.py             # Ideas management and submission
    ├── status.py            # Online status, heartbeat, and timer
    ├── survey.py            # Survey data collection (3 pages)
    └── data.py              # Data export functionality
```

## Module Descriptions

### `app.py`
Main application entry point that:
- Initializes the Flask app and CORS
- Sets up the database
- Maintains global session state (active_teams, team_approvals, online_participants)
- Registers all route blueprints
- Starts the development server

### `config.py`
Configuration settings including:
- OpenAI API configuration (key, model, temperature, max tokens)
- Database configuration
- Session duration and heartbeat timeout
- Flask server settings (host, port, debug mode)

### `database.py`
Database layer with:
- Database connection utility function
- Schema initialization for 6 tables:
  - `teams` - Team session data and typing metrics
  - `messages` - Chat messages between participants and AI
  - `ideas` - Individual ideas submitted by participants
  - `survey_page1` - Team collaboration survey responses
  - `survey_page2` - Demographic information
  - `survey_page3` - Contact information for compensation

### `templates/index.html`
Complete frontend interface with:
- Login and consent screens
- Comprehension questions with validation
- Main brainstorming interface (split panel: chat + ideas)
- Real-time collaboration features
- Multi-page survey system
- Thank you screen

### Routes Modules

#### `routes/session.py`
- `/` - Render main application page
- `/api/start_session` - Initialize a new team session

#### `routes/chat.py`
- `/api/messages/<team_id>` - Get chat messages
- `/api/chat` - Send message and get AI response

#### `routes/ideas.py`
- `/api/ideas/<team_id>` - Get team ideas
- `/api/add_idea` - Submit a new idea
- `/api/final_idea/<team_id>` - Get final idea
- `/api/update_final` - Update final idea in real-time
- `/api/submit` - Submit final idea (ends session)
- `/api/set_approval` - Set participant approval
- `/api/get_approvals/<team_id>` - Get approval status

#### `routes/status.py`
- `/api/heartbeat` - Record participant heartbeat
- `/api/online_status/<team_id>` - Get online status
- `/api/get_timer/<team_id>` - Get remaining time
- `/api/typing_metrics` - Track typing activity

#### `routes/survey.py`
- `/api/survey_page1` - Save AI usage survey responses
- `/api/survey_page2` - Save demographic information
- `/api/survey_page3` - Save contact information

#### `routes/data.py`
- `/api/export/<team_id>` - Export team data as CSV

## Setup and Installation

1. **Install dependencies:**
   ```bash
   pip install flask flask-cors openai
   ```

2. **Set OpenAI API key:**
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   Open your browser to `http://localhost:5000`

## Configuration

Edit `config.py` to customize:
- OpenAI model and parameters
- Session duration (default: 30 minutes)
- Server host and port
- Debug mode

## Database

The application uses SQLite with automatic schema initialization. The database file `study_data.db` is created automatically on first run.

## Features

- **Team Collaboration**: Two participants work together in real-time
- **AI Assistant**: ChatGPT integration for brainstorming support
- **Idea Tracking**: Collect and manage multiple ideas
- **Real-time Sync**: Live updates of ideas, approvals, and online status
- **Typing Metrics**: Track participant engagement and activity
- **Timer**: 30-minute session countdown
- **Approval System**: Both participants must approve before submission
- **Survey System**: Multi-page post-session surveys
- **Data Export**: Export session data as CSV

## Benefits of Refactoring

The refactored structure provides:
- **Better organization**: Clear separation of concerns
- **Easier maintenance**: Changes are isolated to specific modules
- **Improved readability**: Smaller, focused files instead of one large file
- **Reusability**: Modules can be imported and tested independently
- **Scalability**: Easy to add new features or routes
- **Configuration management**: Centralized settings

## Original Code

The original monolithic `app.py` (3043 lines) has been preserved as `app_original.py` for reference.
