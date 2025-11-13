from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import openai
import sqlite3
import json
from datetime import datetime
import os
import csv
import io
import time

app = Flask(__name__)
CORS(app)

# IMPORTANT: Set your OpenAI API key as environment variable
openai.api_key = os.getenv('OPENAI_API_KEY', 'your-api-key-here')

# Database setup
def init_db():
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            final_idea TEXT,
            submitted BOOLEAN DEFAULT 0,
            submit_time TIMESTAMP,
            p1_title_keystroke_count INTEGER DEFAULT 0,
            p1_title_active_typing_seconds REAL DEFAULT 0,
            p1_title_first_edit_time TIMESTAMP,
            p1_title_last_edit_time TIMESTAMP,
            p1_description_keystroke_count INTEGER DEFAULT 0,
            p1_description_active_typing_seconds REAL DEFAULT 0,
            p1_description_first_edit_time TIMESTAMP,
            p1_description_last_edit_time TIMESTAMP,
            p2_title_keystroke_count INTEGER DEFAULT 0,
            p2_title_active_typing_seconds REAL DEFAULT 0,
            p2_title_first_edit_time TIMESTAMP,
            p2_title_last_edit_time TIMESTAMP,
            p2_description_keystroke_count INTEGER DEFAULT 0,
            p2_description_active_typing_seconds REAL DEFAULT 0,
            p2_description_first_edit_time TIMESTAMP,
            p2_description_last_edit_time TIMESTAMP,
            total_title_keystroke_count INTEGER DEFAULT 0,
            total_title_active_typing_seconds REAL DEFAULT 0,
            title_first_edit_time TIMESTAMP,
            title_last_edit_time TIMESTAMP,
            total_description_keystroke_count INTEGER DEFAULT 0,
            total_description_active_typing_seconds REAL DEFAULT 0,
            description_first_edit_time TIMESTAMP,
            description_last_edit_time TIMESTAMP,
            UNIQUE(team_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tokens_used INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            idea_text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_page1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            q1 TEXT,
            q2 TEXT,
            q3 TEXT,
            q4 TEXT,
            q5 TEXT,
            q6 TEXT,
            q7 TEXT,
            q8 TEXT,
            q9 TEXT,
            q10 TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_page2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            employment_status TEXT,
            major_field TEXT,
            major_other TEXT,
            age INTEGER,
            gender TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_page3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            first_last_name TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Store active team sessions
active_teams = {}
team_approvals = {}  # Track approvals: {team_id: {1: bool, 2: bool}}
online_participants = {}  # Track online participants: {team_id: {participant_id: last_heartbeat_time}}

# HTML Template
HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Team Brainstorming Session</title>
    <style>
        /* Version 2.6 - Layout Fixes */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            overflow: hidden;
        }

        .login-screen {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .login-box {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 100%;
            padding: 40px;
        }

        .login-box h1 {
            color: #333;
            margin-bottom: 20px;
            font-size: 28px;
        }

        .consent-box {
            background: #f0f7ff;
            border: 2px solid #3b82f6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }

        .consent-box h2 {
            color: #1e40af;
            font-size: 18px;
            margin-bottom: 12px;
        }

        .consent-box p {
            color: #1e3a8a;
            line-height: 1.6;
            font-size: 14px;
        }

        .input-group {
            margin-bottom: 20px;
        }

        .input-group label {
            display: block;
            color: #555;
            font-weight: 500;
            margin-bottom: 8px;
        }

        .input-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
        }

        .input-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            width: 100%;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }

        .btn:hover {
            background: #5568d3;
        }

        .main-container {
            display: none;
            height: 100vh;
            flex-direction: row;
        }

        .main-container.active {
            display: flex;
        }

        .left-panel {
            width: 50%;
            display: flex;
            flex-direction: column;
            background: white;
            border-right: 2px solid #e0e0e0;
        }

        .instructions-button {
            background: #10a37f;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        .instructions-button:hover {
            background: #0d8a6a;
        }

        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }

        .left-top-section {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .timer-display {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            padding: 6px 12px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
        }

        .timer-display.warning {
            color: #dc2626;
            border-color: #dc2626;
        }

        .online-status {
            display: flex;
            gap: 8px;
            align-items: center;
            font-size: 12px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #9ca3af;
        }

        .status-dot.online {
            background: #10b981;
        }

        .right-panel {
            width: 50%;
            display: flex;
            flex-direction: column;
            background: #fafafa;
        }

        .chat-header {
            background: #667eea;
            color: white;
            padding: 20px;
        }

        .chat-header h2 {
            font-size: 20px;
        }

        .team-info {
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f9fafb;
        }

        .message {
            margin-bottom: 16px;
            display: flex;
            gap: 12px;
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
            overflow: hidden;
        }

        .message-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .message.user .message-avatar {
            background: #667eea;
            color: white;
        }

        .message.assistant .message-avatar {
            background: #10a37f;
            padding: 0;
        }

        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.6;
        }

        .message-content strong {
            font-weight: 600;
        }

        .message-content ul, .message-content ol {
            margin: 16px 0 !important;
            padding-left: 28px !important;
            display: block !important;
        }

        .message-content li {
            margin: 8px 0 !important;
            display: list-item !important;
            line-height: 1.6 !important;
        }
        
        .message-content li::marker {
            font-weight: bold;
        }

        .message-content p {
            margin: 8px 0;
        }

        .message.user .message-content {
            background: #667eea;
            color: white;
        }

        .message.assistant .message-content {
            background: white;
            color: #333;
            border: 1px solid #e5e7eb;
        }

        .message-meta {
            font-size: 11px;
            color: #999;
            margin-top: 4px;
        }

        .typing-indicator {
            display: none;
            padding: 12px 16px;
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            width: fit-content;
            margin: 10px 20px;
        }

        .typing-indicator.active {
            display: block;
        }

        .typing-indicator span {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #999;
            margin-right: 4px;
            animation: typing 1.4s infinite;
        }

        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }

        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 12px;
        }

        .input-area input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 15px;
        }

        .send-btn {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }

        .ideas-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 20px;
            border-bottom: 2px solid #e0e0e0;
            overflow: hidden;
        }

        .ideas-header {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            flex-shrink: 0;
        }

        .ideas-list {
            flex: 1;
            overflow-y: auto;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }

        .idea-item {
            background: #f0f7ff;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid #667eea;
        }

        .idea-meta {
            font-size: 11px;
            color: #666;
            margin-bottom: 5px;
        }

        .idea-input {
            width: 100%;
            padding: 6px 8px;
            border: 2px solid #e0e0e0;
            border-radius: 4px;
            font-size: 13px;
            margin-bottom: 6px;
            flex-shrink: 0;
        }

        .final-input-group {
            margin-bottom: 8px;
        }

        .final-input-label {
            font-weight: 600;
            font-size: 13px;
            color: #555;
            margin-bottom: 4px;
            display: block;
        }

        .word-counter {
            font-size: 11px;
            color: #999;
            font-weight: normal;
        }

        .word-counter.warning {
            color: #ef4444;
            font-weight: 600;
        }

        .final-title-input {
            width: 100%;
            padding: 8px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 13px;
        }

        .final-title-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .final-description-textarea {
            width: 100%;
            min-height: 50px;
            max-height: 50px;
            padding: 8px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 13px;
            font-family: inherit;
            resize: none;
        }

        .final-description-textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .add-idea-btn {
            padding: 10px 20px;
            background: #10b981;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            flex-shrink: 0;
        }

        .final-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 10px;
            overflow-y: visible;
            height: 70%;
        }

        .final-textarea {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 15px;
            resize: none;
            margin-bottom: 15px;
            font-family: inherit;
            overflow-y: auto;
        }

        .submit-btn {
            padding: 8px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            flex-shrink: 0;
            margin-top: 6px;
        }

        .submit-btn:hover:not(:disabled) {
            background: #dc2626;
        }

        .submit-btn:disabled {
            background: #9ca3af;
            cursor: not-allowed;
            opacity: 0.6;
        }

        .approval-section {
            margin: 8px 0 6px 0;
            padding: 6px 10px;
            background: #f0f9ff;
            border: 1px solid #3b82f6;
            border-radius: 4px;
            flex-shrink: 0;
        }

        .approval-header {
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 4px;
            font-size: 11px;
        }

        .approval-checkboxes {
            display: flex;
            flex-direction: row;
            gap: 12px;
        }

        .approval-item {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: white;
            border-radius: 3px;
            border: 1px solid #e5e7eb;
        }

        .approval-item input[type="checkbox"] {
            width: 16px;
            height: 16px;
            cursor: pointer;
            margin: 0;
        }

        .approval-item input[type="checkbox"]:disabled {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .approval-item label {
            cursor: pointer;
            font-size: 12px;
            margin: 0;
        }

        .approval-item.disabled label {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .thank-you-screen {
            display: none;
            min-height: 100vh;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 40px;
        }

        .thank-you-screen.active {
            display: flex;
        }

        .thank-you-box {
            background: white;
            border-radius: 16px;
            padding: 60px;
            max-width: 600px;
        }

        .thank-you-box h1 {
            font-size: 36px;
            color: #333;
            margin-bottom: 20px;
        }

        .thank-you-box p {
            font-size: 18px;
            color: #666;
            line-height: 1.6;
        }

        .instructions-screen {
            display: none;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .instructions-screen.active {
            display: flex;
        }

        .instructions-box {
            background: white;
            border-radius: 16px;
            padding: 50px;
            max-width: 800px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-height: 90vh;
            overflow-y: auto;
            cursor: default;
        }

        .instructions-box h1 {
            font-size: 32px;
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }

        .instructions-box p {
            font-size: 18px;
            color: #444;
            line-height: 1.8;
            margin-bottom: 20px;
        }

        .go-back-btn {
            display: block;
            width: 200px;
            margin: 30px auto 0;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        .go-back-btn:hover {
            background: #5568d3;
        }

        /* Survey and Wait Screens */
        .wait-screen, .survey-screen, .comprehension-screen {
            display: none;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .wait-screen.active, .survey-screen.active, .comprehension-screen.active {
            display: flex;
        }

        .wait-box, .survey-box, .comprehension-box {
            background: white;
            border-radius: 16px;
            padding: 50px;
            max-width: 1000px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-height: 90vh;
            overflow-y: auto;
            cursor: default;
        }

        /* Comprehension Questions Styles */
        .comprehension-question {
            margin-bottom: 25px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
        }

        .comprehension-question label {
            font-weight: 500;
            margin-bottom: 12px;
            display: block;
            color: #444;
            font-size: 14px;
            line-height: 1.5;
        }

        .radio-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
        }

        .radio-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .radio-option:hover {
            background: #e5e7eb;
        }

        .radio-option input[type="radio"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        .radio-option label {
            cursor: pointer;
            margin: 0 !important;
            font-weight: normal !important;
        }

        /* Modal for hints */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            justify-content: center;
            align-items: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 12px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }

        .modal-header {
            font-size: 22px;
            font-weight: 600;
            color: #dc2626;
            margin-bottom: 20px;
        }

        .modal-body {
            margin-bottom: 25px;
        }

        .hint-item {
            background: #fef2f2;
            border-left: 4px solid #dc2626;
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 4px;
        }

        .hint-item strong {
            color: #991b1b;
        }

        .hint-text {
            color: #7f1d1d;
            margin-top: 5px;
            line-height: 1.5;
        }

        .modal-footer {
            text-align: right;
        }

        .modal-btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }

        .modal-btn:hover {
            background: #5568d3;
        }

            display: none;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .wait-screen.active, .survey-screen.active {
            display: flex;
        }

        .wait-box, .survey-box {
            background: white;
            border-radius: 16px;
            padding: 50px;
            max-width: 1000px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-height: 90vh;
            overflow-y: auto;
            cursor: default;
        }

        .wait-box p {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }

        .survey-box h2 {
            font-size: 24px;
            color: #333;
            margin-bottom: 30px;
        }

        .survey-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }

        .survey-question {
            margin-bottom: 20px;
        }

        .survey-question label {
            display: block;
            color: #444;
            font-size: 14px;
            margin-bottom: 10px;
            line-height: 1.5;
        }

        .survey-question select, .survey-question input, .survey-question textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }

        .survey-question textarea {
            min-height: 80px;
            resize: vertical;
        }

        .survey-question input:focus, .survey-question select:focus, .survey-question textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .continue-btn {
            display: block;
            width: 200px;
            margin: 30px auto 0;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        .continue-btn:hover {
            background: #5568d3;
        }

        .survey-single-column {
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <div class="login-screen" id="loginScreen">
        <div class="login-box">
            <h1>Team Brainstorming Session</h1>
            
            <p style="color: #555; margin-bottom: 30px; font-size: 16px; line-height: 1.6;">
                Please enter the Team and Participant ID that the experimenter provided you.
            </p>

            <div class="input-group">
                <label for="teamId">Team ID</label>
                <input type="text" id="teamId" placeholder="Enter your team ID">
            </div>

            <div class="input-group">
                <label for="participantId">Participant ID</label>
                <input type="text" id="participantId" placeholder="Enter your participant ID">
            </div>

            <button class="btn" onclick="startStudy()">Start Session</button>
        </div>
    </div>

    <!-- Comprehension Questions Screen -->
    <div class="comprehension-screen" id="comprehensionScreen">
        <div class="comprehension-box">
            <h2>Please answer the following questions.</h2>
            
            <div class="comprehension-question">
                <label>1. The ideas you come up with need to be feasible and fully functional.</label>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="q1_true" name="q1" value="True">
                        <label for="q1_true">True</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="q1_false" name="q1" value="False">
                        <label for="q1_false">False</label>
                    </div>
                </div>
            </div>

            <div class="comprehension-question">
                <label>2. You will be evaluated based on the number of ideas you generate.</label>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="q2_true" name="q2" value="True">
                        <label for="q2_true">True</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="q2_false" name="q2" value="False">
                        <label for="q2_false">False</label>
                    </div>
                </div>
            </div>

            <div class="comprehension-question">
                <label>3. You will be evaluated based on the final idea you submit.</label>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="q3_true" name="q3" value="True">
                        <label for="q3_true">True</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="q3_false" name="q3" value="False">
                        <label for="q3_false">False</label>
                    </div>
                </div>
            </div>

            <div class="comprehension-question">
                <label>4. If you receive 15 points for Quality, and 10 points for Originality of your idea, your final points will be calculated as:</label>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="q4_a" name="q4" value="a">
                        <label for="q4_a">a) 60% × 15 + 40% × 10 = 13</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="q4_b" name="q4" value="b">
                        <label for="q4_b">b) 40% × 15 + 60% × 10 = 12</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="q4_c" name="q4" value="c">
                        <label for="q4_c">c) 50% × 15 + 50% × 10 = 12.5</label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="q4_d" name="q4" value="d">
                        <label for="q4_d">d) 15 + 10 = 25</label>
                    </div>
                </div>
            </div>

            <button class="continue-btn" onclick="checkComprehension()">Continue</button>
        </div>
    </div>

    <!-- Modal for hints -->
    <div class="modal" id="hintModal">
        <div class="modal-content">
            <div class="modal-header">Please Review Your Answers</div>
            <div class="modal-body" id="hintContent"></div>
            <div class="modal-footer">
                <button class="modal-btn" onclick="closeHintModal()">Review Answers</button>
            </div>
        </div>
    </div>

    <!-- Wait Screen 1 (After Comprehension) -->
    <div class="wait-screen" id="waitScreen1">
        <div class="wait-box">
            <p>Please wait before you continue with the rest of the experiment, the experimenter will give you further instructions.</p>
            <button class="continue-btn" onclick="goToMainSession()">Continue</button>
        </div>
    </div>

    <div class="main-container" id="mainContainer">
        <div class="left-panel">
            <div class="top-bar">
                <div class="left-top-section">
                    <button class="instructions-button" onclick="showInstructions()">Instructions</button>
                    <div class="timer-display" id="timerDisplay">30:00</div>
                    <div class="online-status">
                        <div class="status-indicator">
                            <div class="status-dot" id="status1"></div>
                            <span>P1</span>
                        </div>
                        <div class="status-indicator">
                            <div class="status-dot" id="status2"></div>
                            <span>P2</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="chat-header">
                <h2>ChatGPT Assistant</h2>
                <div class="team-info" id="teamInfo"></div>
            </div>

            <div class="messages" id="messages"></div>

            <div class="typing-indicator" id="typingIndicator">
                <span></span>
                <span></span>
                <span></span>
            </div>

            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Ask ChatGPT..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </div>
        </div>

        <div class="right-panel">
            <div class="ideas-section">
                <div class="ideas-header">Possible Ideas</div>
                <div class="ideas-list" id="ideasList"></div>
                <input type="text" id="ideaInput" class="idea-input" 
                       placeholder="Add a new idea..." onkeypress="if(event.key==='Enter') addIdea()">
                <button class="add-idea-btn" onclick="addIdea()">+ Add Idea</button>
            </div>

            <div class="final-section">
                <div class="ideas-header">Final Idea</div>
                
                <div class="final-input-group">
                    <label class="final-input-label">
                        Title 
                        <span class="word-counter" id="titleCounter">0/5 words</span>
                    </label>
                    <input type="text" id="finalTitle" class="final-title-input" 
                           placeholder="Enter title (max 5 words)">
                </div>
                
                <div class="final-input-group">
                    <label class="final-input-label">
                        Description
                        <span class="word-counter" id="descCounter">0/80 words</span>
                    </label>
                    <textarea id="finalDescription" class="final-description-textarea" 
                              placeholder="Enter description (max 80 words)"></textarea>
                </div>
                
                <div class="approval-section">
                    <div class="approval-header">Both participants must approve:</div>
                    <div class="approval-checkboxes">
                        <div class="approval-item" id="approval1Container">
                            <input type="checkbox" id="approval1" onchange="handleApproval(1)">
                            <label for="approval1">Participant 1</label>
                        </div>
                        <div class="approval-item" id="approval2Container">
                            <input type="checkbox" id="approval2" onchange="handleApproval(2)">
                            <label for="approval2">Participant 2</label>
                        </div>
                    </div>
                </div>
                
                <button class="submit-btn" id="submitBtn" onclick="submitFinal()" disabled>Submit Final Idea</button>
            </div>
        </div>
    </div>

    <!-- Wait Screen -->
    <div class="wait-screen" id="waitScreen">
        <div class="wait-box">
            <p>Please wait before you continue with the rest of the experiment, the experimenter will give you further instructions.</p>
            <button class="continue-btn" onclick="goToSurveyPage1()">Continue</button>
        </div>
    </div>

    <!-- Survey Page 1 -->
    <div class="survey-screen" id="surveyPage1">
        <div class="survey-box">
            <h2>Please answer the following questions.</h2>
            <div class="survey-columns">
                <div>
                    <div class="survey-question">
                        <label>1. I use Generative AI tools (e.g. ChatGPT) to support my academic work (e.g. assignments, studying, brainstorming, explanations).</label>
                        <select id="q1">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>2. I use Generative AI tools for personal or non-academic purposes (e.g. creative writing, daily tasks, recommendations, hobbies).</label>
                        <select id="q2">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>3. Generative AI tools help me save time when completing tasks.</label>
                        <select id="q3">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>4. Generative AI tools improve the quality of my work (e.g. clarity, structure, completeness).</label>
                        <select id="q4">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>5. I believe learning to use Generative AI responsibly is an important skill for my future career.</label>
                        <select id="q5">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                </div>
                <div>
                    <div class="survey-question">
                        <label>6. I understand that Generative AI tools can produce output that is factually inaccurate.</label>
                        <select id="q6">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>7. I am aware that Generative AI tools may generate biased or unfair information.</label>
                        <select id="q7">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>8. I am concerned that relying too much on Generative AI tools may reduce my own learning or skill development.</label>
                        <select id="q8">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>9. I am unsure about what types of AI use are allowed or considered acceptable for my academic work.</label>
                        <select id="q9">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                    <div class="survey-question">
                        <label>10. Overall, I find Generative AI tools to be valuable in my work and daily tasks.</label>
                        <select id="q10">
                            <option value="">Select an answer</option>
                            <option value="Strongly Disagree">Strongly Disagree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Neither Disagree nor Agree">Neither Disagree nor Agree</option>
                            <option value="Agree">Agree</option>
                            <option value="Strongly Agree">Strongly Agree</option>
                        </select>
                    </div>
                </div>
            </div>
            <button class="continue-btn" onclick="submitSurveyPage1()">Continue</button>
        </div>
    </div>

    <!-- Survey Page 2 -->
    <div class="survey-screen" id="surveyPage2">
        <div class="survey-box">
            <h2>Please answer the following questions.</h2>
            <div class="survey-single-column">
                <div class="survey-question">
                    <label>What is your employment status?</label>
                    <select id="employmentStatus">
                        <option value="">Select an answer</option>
                        <option value="Undergraduate student">Undergraduate student</option>
                        <option value="Graduate student">Graduate student</option>
                    </select>
                </div>
                <div class="survey-question">
                    <label>What is your major field?</label>
                    <select id="majorField" onchange="toggleMajorOther()">
                        <option value="">Select an answer</option>
                        <option value="STEM">STEM (Science, Technology, Engineering and Mathematics)</option>
                        <option value="Business and Economics">Business and Economics</option>
                        <option value="Arts and Humanities">Arts and Humanities</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
                <div class="survey-question" id="majorOtherDiv" style="display: none;">
                    <label>If you chose "Other", please specify your major.</label>
                    <input type="text" id="majorOther" />
                </div>
                <div class="survey-question">
                    <label>What is your age (in years)?</label>
                    <input type="number" id="age" min="18" max="100" />
                </div>
                <div class="survey-question">
                    <label>To which gender do you most identify?</label>
                    <select id="gender">
                        <option value="">Select an answer</option>
                        <option value="Female">Female</option>
                        <option value="Male">Male</option>
                        <option value="Transgender Female">Transgender Female</option>
                        <option value="Transgender Male">Transgender Male</option>
                        <option value="Gender Variant / Non-Conforming">Gender Variant / Non-Conforming</option>
                        <option value="Other">Other</option>
                        <option value="Prefer not to answer">Prefer not to answer</option>
                    </select>
                </div>
            </div>
            <button class="continue-btn" onclick="submitSurveyPage2()">Continue</button>
        </div>
    </div>

    <!-- Survey Page 3 -->
    <div class="survey-screen" id="surveyPage3">
        <div class="survey-box">
            <h2>Please answer the following questions to receive your check. You should enter the address where you would want your check to be mailed.</h2>
            <div class="survey-single-column">
                <div class="survey-question">
                    <label>First and Last Name:</label>
                    <input type="text" id="firstLastName" />
                </div>
                <div class="survey-question">
                    <label>Address (line 1 – street and number):</label>
                    <input type="text" id="addressLine1" />
                </div>
                <div class="survey-question">
                    <label>Address (optional line 2 – apartment # or additional information):</label>
                    <input type="text" id="addressLine2" />
                </div>
                <div class="survey-question">
                    <label>City:</label>
                    <input type="text" id="city" />
                </div>
                <div class="survey-question">
                    <label>State (2 letter abbreviation):</label>
                    <input type="text" id="state" maxlength="2" style="text-transform: uppercase;" />
                </div>
                <div class="survey-question">
                    <label>Postal Code:</label>
                    <input type="text" id="postalCode" maxlength="5" pattern="[0-9]{5}" />
                </div>
            </div>
            <button class="continue-btn" onclick="submitSurveyPage3()">Continue</button>
        </div>
    </div>

    <div class="thank-you-screen" id="thankYouScreen">
        <div class="thank-you-box">
            <h1>🎉 Thank You!</h1>
            <p>Your team's submission has been recorded.<br>
            Thank you for participating in this study!</p>
        </div>
    </div>

    <div class="instructions-screen" id="instructionsScreen">
        <div class="instructions-box">
            <h1>Task Instructions</h1>
            <p>
                You have 30 minutes to complete the following task: Assume that you have been hired by a mobile applications developer to come up with new app ideas for the college student market. The developer is interested in any mobile app idea that could be especially appealing or useful to college students in the United States. These apps might address unmet needs faced by students or provide better solutions to existing challenges. The ideas are conceptual only—they do not need to exist yet or be fully feasible.
            </p>
            <p>
                Your final idea submission should include a descriptive title (no more than 5 words), followed by a brief explanation of the idea in no more than 80 words.
            </p>
            <button class="go-back-btn" onclick="goBackFromInstructions()">Go Back</button>
        </div>
    </div>

    <script>
        let teamId = '';
        let participantId = '';
        let lastMessageId = 0;
        let lastIdeaId = 0;
        let pollInterval;
        let timerInterval;
        let timeRemaining = 30 * 60; // 30 minutes in seconds
        let onlineParticipants = {};
        const API_BASE = window.location.origin;

        // Comprehension questions correct answers
        const correctAnswers = {
            q1: 'False',
            q2: 'False',
            q3: 'True',
            q4: 'a'
        };

        const hints = {
            q1: 'The ideas are conceptual only—they do not need to exist yet or be fully feasible.',
            q2: 'Generating several ideas might be helpful for brainstorming, but you will be evaluated based on the final idea you submit.',
            q3: 'Evaluations will be made based on the final idea you submit to the system.',
            q4: 'The final score is calculated as 40% × Originality Score + 60% × Quality Score.'
        };

        function checkComprehension() {
            const answers = {
                q1: document.querySelector('input[name="q1"]:checked')?.value,
                q2: document.querySelector('input[name="q2"]:checked')?.value,
                q3: document.querySelector('input[name="q3"]:checked')?.value,
                q4: document.querySelector('input[name="q4"]:checked')?.value
            };

            // Check if all questions are answered
            const unanswered = Object.keys(answers).filter(q => !answers[q]);
            if (unanswered.length > 0) {
                alert('Please answer all questions before continuing.');
                return;
            }

            // Check for incorrect answers
            const incorrectQuestions = [];
            Object.keys(correctAnswers).forEach(q => {
                if (answers[q] !== correctAnswers[q]) {
                    incorrectQuestions.push(q);
                }
            });

            if (incorrectQuestions.length > 0) {
                // Show hints modal
                showHints(incorrectQuestions);
            } else {
                // All correct, proceed to wait screen
                document.getElementById('comprehensionScreen').classList.remove('active');
                document.getElementById('waitScreen1').classList.add('active');
            }
        }

        function showHints(incorrectQuestions) {
            const hintContent = document.getElementById('hintContent');
            hintContent.innerHTML = '';

            incorrectQuestions.forEach((q, index) => {
                const questionNum = q.replace('q', '');
                const hintDiv = document.createElement('div');
                hintDiv.className = 'hint-item';
                hintDiv.innerHTML = `
                    <strong>Question ${questionNum}:</strong>
                    <div class="hint-text">${hints[q]}</div>
                `;
                hintContent.appendChild(hintDiv);
            });

            document.getElementById('hintModal').classList.add('active');
        }

        function closeHintModal() {
            document.getElementById('hintModal').classList.remove('active');
        }

        function goToMainSession() {
            // Start the session and timer NOW
            fetch(API_BASE + '/api/start_session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({team_id: teamId, participant_id: participantId})
            })
            .then(response => response.json())
            .then(data => {
                // Disable the other participant's checkbox
                const otherParticipant = participantId === '1' ? '2' : '1';
                const otherCheckbox = document.getElementById(`approval${otherParticipant}`);
                const otherContainer = document.getElementById(`approval${otherParticipant}Container`);
                
                otherCheckbox.disabled = true;
                otherContainer.classList.add('disabled');
                
                loadMessages();
                loadIdeas();
                loadFinalIdea();
                loadApprovals();
                
                // Start timer and online status updates
                startTimer();
                updateOnlineStatus();
                sendHeartbeat();
                
                pollInterval = setInterval(() => {
                    loadMessages();
                    loadIdeas();
                    loadFinalIdea();
                    loadApprovals();
                    updateOnlineStatus();
                    sendHeartbeat();
                }, 2000);
            });

            document.getElementById('waitScreen1').classList.remove('active');
            document.getElementById('mainContainer').classList.add('active');
            document.getElementById('teamInfo').textContent = `Team: ${teamId} | You: ${participantId}`;
        }



        function loadTimer() {
            fetch(API_BASE + `/api/get_timer/${teamId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.time_remaining !== undefined) {
                        timeRemaining = data.time_remaining;
                        updateTimerDisplay();
                    }
                })
                .catch(err => {
                    console.error('Error loading timer:', err);
                });
        }

        function startTimer() {
            // Load initial time from server FIRST, then start the countdown
            fetch(API_BASE + `/api/get_timer/${teamId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.time_remaining !== undefined) {
                        timeRemaining = data.time_remaining;
                        updateTimerDisplay();

                        // NOW start the countdown interval with synchronized time
                        timerInterval = setInterval(() => {
                            timeRemaining--;
                            updateTimerDisplay();

                            if (timeRemaining <= 0) {
                                clearInterval(timerInterval);
                                alert('Time is up! Please submit your final idea.');
                            }
                        }, 1000);

                        // Sync with server every 10 seconds to prevent drift
                        setInterval(() => {
                            loadTimer();
                        }, 10000);
                    }
                })
                .catch(err => {
                    console.error('Error starting timer:', err);
                });
        }

        function updateTimerDisplay() {
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            const timerElement = document.getElementById('timerDisplay');
            timerElement.textContent = display;
            
            // Add warning color if less than 5 minutes
            if (timeRemaining <= 5 * 60) {
                timerElement.classList.add('warning');
            }
        }

        function updateOnlineStatus() {
            fetch(API_BASE + `/api/online_status/${teamId}`)
                .then(response => response.json())
                .then(data => {
                    onlineParticipants = data.online || {};
                    
                    // Update status dots
                    const status1 = document.getElementById('status1');
                    const status2 = document.getElementById('status2');
                    
                    if (onlineParticipants['1']) {
                        status1.classList.add('online');
                    } else {
                        status1.classList.remove('online');
                    }
                    
                    if (onlineParticipants['2']) {
                        status2.classList.add('online');
                    } else {
                        status2.classList.remove('online');
                    }
                });
        }

        function sendHeartbeat() {
            fetch(API_BASE + '/api/heartbeat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({team_id: teamId, participant_id: participantId})
            });
        }

        function showInstructions() {
            document.getElementById('mainContainer').classList.remove('active');
            document.getElementById('instructionsScreen').classList.add('active');
        }

        function goBackFromInstructions() {
            document.getElementById('instructionsScreen').classList.remove('active');
            document.getElementById('mainContainer').classList.add('active');
        }

        function startStudy() {
            const teamInput = document.getElementById('teamId').value.trim();
            const participantInput = document.getElementById('participantId').value.trim();
            
            if (!teamInput || !participantInput) {
                alert('Please enter both Team ID and Participant ID');
                return;
            }

            // Validate Team ID is an integer
            if (!Number.isInteger(Number(teamInput)) || Number(teamInput) <= 0) {
                alert('Team ID must be a positive integer');
                return;
            }

            // Validate Participant ID is either 1 or 2
            if (participantInput !== '1' && participantInput !== '2') {
                alert('Participant ID must be either 1 or 2');
                return;
            }

            teamId = teamInput;
            participantId = participantInput;

            // Go to comprehension screen instead of main session
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('comprehensionScreen').classList.add('active');
        }

        function loadMessages() {
            fetch(API_BASE + `/api/messages/${teamId}?since=${lastMessageId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.messages && data.messages.length > 0) {
                        data.messages.forEach(msg => {
                            addMessageToUI(msg.role, msg.content, msg.participant_id, msg.id);
                            lastMessageId = Math.max(lastMessageId, msg.id);
                        });
                    }
                });
        }

        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;

            input.value = '';
            document.getElementById('typingIndicator').classList.add('active');
            
            fetch(API_BASE + '/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({team_id: teamId, participant_id: participantId, message: message})
            })
            .finally(() => {
                document.getElementById('typingIndicator').classList.remove('active');
            });
        }

        function addMessageToUI(role, content, participant, messageId) {
            if (document.getElementById(`msg-${messageId}`)) return;
            
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.id = `msg-${messageId}`;
            messageDiv.className = `message ${role}`;
            
            const logo = role === 'assistant' ? 
                '<img src="https://cdn.oaistatic.com/_next/static/media/apple-touch-icon.59f2e898.png">' : '👤';
            
            const label = role === 'user' && participant ? `Participant ${participant}` : '';
            const time = new Date().toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit',
                hour12: true 
            });
            
            const formattedContent = role === 'assistant' ? formatMarkdown(content) : escapeHtml(content);
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${logo}</div>
                <div>
                    <div class="message-content">${formattedContent}</div>
                    <div class="message-meta">${label} ${time}</div>
                </div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function formatMarkdown(text) {
            // First, ensure proper line breaks around numbered lists
            // Handle pattern: "text: 1. item" -> "text:\n1. item"
            text = text.replace(/:\s*(\d+\.)/g, ':\n$1');
            
            // Handle pattern: "text 1. item" where 1. starts a list after a sentence
            text = text.replace(/([.!?])\s+(\d+\.\s+\*\*)/g, '$1\n\n$2');
            
            let html = text;
            
            // Bold text
            html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            
            // Process line by line
            const lines = html.split('\n');
            let result = '';
            let inList = false;
            let listType = null;
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                
                // Check for numbered list item
                if (/^\d+\.\s+/.test(line)) {
                    // Start new list if not in one
                    if (!inList) {
                        result += '<br><ol style="margin: 12px 0; padding-left: 28px;">';
                        inList = true;
                        listType = 'ol';
                    }
                    const content = line.replace(/^\d+\.\s+/, '');
                    result += `<li style="margin: 8px 0; line-height: 1.6;">${content}</li>`;
                }
                // Check for bullet list item  
                else if (/^[-*]\s+/.test(line)) {
                    if (!inList) {
                        result += '<br><ul style="margin: 12px 0; padding-left: 28px;">';
                        inList = true;
                        listType = 'ul';
                    }
                    const content = line.replace(/^[-*]\s+/, '');
                    result += `<li style="margin: 8px 0; line-height: 1.6;">${content}</li>`;
                }
                // Regular text
                else {
                    // Close list if we were in one
                    if (inList) {
                        result += `</${listType}><br>`;
                        inList = false;
                        listType = null;
                    }
                    result += `<p style="margin: 10px 0;">${line}</p>`;
                }
            }
            
            // Close any open list
            if (inList) {
                result += `</${listType}>`;
            }
            
            return result;
        }

        function loadIdeas() {
            fetch(API_BASE + `/api/ideas/${teamId}?since=${lastIdeaId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.ideas && data.ideas.length > 0) {
                        data.ideas.forEach(idea => {
                            addIdeaToUI(idea.id, idea.participant_id, idea.idea_text, idea.timestamp);
                            lastIdeaId = Math.max(lastIdeaId, idea.id);
                        });
                    }
                });
        }

        function addIdea() {
            const input = document.getElementById('ideaInput');
            const idea = input.value.trim();
            if (!idea) return;

            input.value = '';
            fetch(API_BASE + '/api/add_idea', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({team_id: teamId, participant_id: participantId, idea_text: idea})
            });
        }

        function addIdeaToUI(id, participant, text, timestamp) {
            if (document.getElementById(`idea-${id}`)) return;
            
            const ideasList = document.getElementById('ideasList');
            const ideaDiv = document.createElement('div');
            ideaDiv.id = `idea-${id}`;
            ideaDiv.className = 'idea-item';
            
            // SQLite CURRENT_TIMESTAMP returns UTC time
            // Parse as UTC and convert to local time
            // Format: "YYYY-MM-DD HH:MM:SS"
            const date = new Date(timestamp + ' UTC');
            const timeStr = date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit',
                hour12: true 
            });
            
            ideaDiv.innerHTML = `
                <div class="idea-meta">Participant ${participant} - ${timeStr}</div>
                <div>${escapeHtml(text)}</div>
            `;
            ideasList.appendChild(ideaDiv);
        }

        let lastSavedTitle = '';
        let lastSavedDescription = '';
        let isUserEditingTitle = false;
        let isUserEditingDesc = false;
        let titleEditTimeout;
        let descEditTimeout;

        // Typing metrics tracking
        let typingMetrics = {
            title: {
                keystrokeCount: 0,
                activeTypingSeconds: 0,
                firstEditTime: null,
                lastEditTime: null,
                lastKeystrokeTime: null,
                sessionStartTime: null
            },
            description: {
                keystrokeCount: 0,
                activeTypingSeconds: 0,
                firstEditTime: null,
                lastEditTime: null,
                lastKeystrokeTime: null,
                sessionStartTime: null
            }
        };

        const TYPING_SESSION_TIMEOUT = 5000; // 5 seconds

        function trackKeystroke(field) {
            const metric = typingMetrics[field];
            const now = new Date().toISOString();
            const nowTime = Date.now();
            
            // Increment keystroke count
            metric.keystrokeCount++;
            
            // Set first edit time if not set
            if (!metric.firstEditTime) {
                metric.firstEditTime = now;
            }
            
            // Always update last edit time
            metric.lastEditTime = now;
            
            // Handle typing session
            if (metric.lastKeystrokeTime && (nowTime - metric.lastKeystrokeTime) < TYPING_SESSION_TIMEOUT) {
                // Continue current session
                if (metric.sessionStartTime) {
                    // Session is active
                }
            } else {
                // Start new session
                if (metric.sessionStartTime) {
                    // End previous session and add its duration
                    const sessionDuration = (metric.lastKeystrokeTime - metric.sessionStartTime) / 1000;
                    metric.activeTypingSeconds += sessionDuration;
                }
                metric.sessionStartTime = nowTime;
            }
            
            metric.lastKeystrokeTime = nowTime;
            
            // Send metrics to server
            sendTypingMetrics(field);
        }

        function endTypingSession(field) {
            const metric = typingMetrics[field];
            if (metric.sessionStartTime && metric.lastKeystrokeTime) {
                const sessionDuration = (metric.lastKeystrokeTime - metric.sessionStartTime) / 1000;
                metric.activeTypingSeconds += sessionDuration;
                metric.sessionStartTime = null;
                sendTypingMetrics(field);
            }
        }

        function sendTypingMetrics(field) {
            const metric = typingMetrics[field];
            
            fetch(API_BASE + '/api/typing_metrics', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: teamId,
                    participant_id: participantId,
                    field: field,
                    keystroke_count: metric.keystrokeCount,
                    active_typing_seconds: metric.activeTypingSeconds,
                    first_edit_time: metric.firstEditTime,
                    last_edit_time: metric.lastEditTime
                })
            });
        }

        // Check for ended sessions periodically
        setInterval(() => {
            ['title', 'description'].forEach(field => {
                const metric = typingMetrics[field];
                if (metric.sessionStartTime && metric.lastKeystrokeTime) {
                    const timeSinceLastKeystroke = Date.now() - metric.lastKeystrokeTime;
                    if (timeSinceLastKeystroke >= TYPING_SESSION_TIMEOUT) {
                        endTypingSession(field);
                    }
                }
            });
        }, 1000);

        document.getElementById('finalTitle').addEventListener('keydown', function(e) {
            // Track all keystrokes including backspace, delete, etc.
            if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Delete') {
                trackKeystroke('title');
            }
        });
        let approvals = {1: false, 2: false};

        function countWords(text) {
            return text.trim().split(/\s+/).filter(word => word.length > 0).length;
        }

        function loadFinalIdea() {
            fetch(API_BASE + `/api/final_idea/${teamId}`)
                .then(response => response.json())
                .then(data => {
                    const serverTitle = data.title || '';
                    const serverDesc = data.description || '';
                    const titleInput = document.getElementById('finalTitle');
                    const descTextarea = document.getElementById('finalDescription');
                    
                    if (!isUserEditingTitle && serverTitle !== titleInput.value) {
                        titleInput.value = serverTitle;
                        updateWordCount('title');
                    }
                    
                    if (!isUserEditingDesc && serverDesc !== descTextarea.value) {
                        descTextarea.value = serverDesc;
                        updateWordCount('description');
                    }
                });
        }

        function updateWordCount(type) {
            if (type === 'title') {
                const titleInput = document.getElementById('finalTitle');
                const words = countWords(titleInput.value);
                const counter = document.getElementById('titleCounter');
                counter.textContent = `${words}/5 words`;
                counter.classList.toggle('warning', words > 5);
            } else {
                const descTextarea = document.getElementById('finalDescription');
                const words = countWords(descTextarea.value);
                const counter = document.getElementById('descCounter');
                counter.textContent = `${words}/80 words`;
                counter.classList.toggle('warning', words > 80);
            }
        }

        document.getElementById('finalTitle').addEventListener('focus', function() {
            isUserEditingTitle = true;
        });

        document.getElementById('finalTitle').addEventListener('blur', function() {
            setTimeout(() => { isUserEditingTitle = false; }, 500);
        });

        document.getElementById('finalTitle').addEventListener('input', function() {
            isUserEditingTitle = true;
            
            // Enforce 5 word limit
            const words = countWords(this.value);
            if (words > 5) {
                // Truncate to 5 words
                const wordArray = this.value.trim().split(/\s+/);
                this.value = wordArray.slice(0, 5).join(' ');
            }
            
            updateWordCount('title');
            
            clearTimeout(titleEditTimeout);
            titleEditTimeout = setTimeout(() => {
                isUserEditingTitle = false;
            }, 3000);
            
            clearTimeout(this.saveTimer);
            this.saveTimer = setTimeout(() => {
                saveFinalIdea();
            }, 1000);
        });

        document.getElementById('finalDescription').addEventListener('keydown', function(e) {
            // Track all keystrokes including backspace, delete, etc.
            if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Delete') {
                trackKeystroke('description');
            }
        });

        document.getElementById('finalDescription').addEventListener('focus', function() {
            isUserEditingDesc = true;
        });

        document.getElementById('finalDescription').addEventListener('blur', function() {
            setTimeout(() => { isUserEditingDesc = false; }, 500);
        });

        document.getElementById('finalDescription').addEventListener('input', function() {
            isUserEditingDesc = true;
            
            // Enforce 80 word limit
            const words = countWords(this.value);
            if (words > 80) {
                // Truncate to 80 words
                const wordArray = this.value.trim().split(/\s+/);
                this.value = wordArray.slice(0, 80).join(' ');
            }
            
            updateWordCount('description');
            
            clearTimeout(descEditTimeout);
            descEditTimeout = setTimeout(() => {
                isUserEditingDesc = false;
            }, 3000);
            
            clearTimeout(this.saveTimer);
            this.saveTimer = setTimeout(() => {
                saveFinalIdea();
            }, 1000);
        });

        function saveFinalIdea() {
            const title = document.getElementById('finalTitle').value;
            const description = document.getElementById('finalDescription').value;
            
            fetch(API_BASE + '/api/update_final', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: teamId, 
                    title: title,
                    description: description
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('[Final Idea Save] Saved:', data);
            });
        }

        function handleApproval(participantNum) {
            const checkbox = document.getElementById(`approval${participantNum}`);
            
            console.log('[Approval] Participant', participantId, 'trying to check box', participantNum);
            
            // Only allow own checkbox
            if (participantNum.toString() !== participantId) {
                checkbox.checked = approvals[participantNum];
                alert('You can only approve with your own checkbox!');
                return;
            }
            
            const isChecked = checkbox.checked;
            
            // Save to backend
            fetch(API_BASE + '/api/set_approval', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: teamId, 
                    participant_id: participantNum,
                    approved: isChecked
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('[Approval] Saved to server:', data);
                if (data.approvals) {
                    approvals = {
                        1: data.approvals['1'] || false,
                        2: data.approvals['2'] || false
                    };
                    updateApprovalUI();
                    checkApprovals();
                }
            });
        }

        function updateApprovalUI() {
            document.getElementById('approval1').checked = approvals[1];
            document.getElementById('approval2').checked = approvals[2];
        }

        function loadApprovals() {
            fetch(API_BASE + `/api/get_approvals/${teamId}`)
                .then(response => response.json())
                .then(data => {
                    // Check if someone submitted
                    if (data.submitted) {
                        console.log('[Approval] Session submitted, redirecting to wait screen');
                        clearInterval(pollInterval);
                        clearInterval(timerInterval);
                        document.getElementById('mainContainer').style.display = 'none';
                        document.getElementById('waitScreen').classList.add('active');
                        return;
                    }
                    
                    if (data.approvals) {
                        approvals = {
                            1: data.approvals['1'] || false,
                            2: data.approvals['2'] || false
                        };
                        updateApprovalUI();
                        checkApprovals();
                    }
                });
        }

        function checkApprovals() {
            const submitBtn = document.getElementById('submitBtn');
            const bothApproved = approvals[1] && approvals[2];
            
            console.log('[Approval] Checking approvals - P1:', approvals[1], 'P2:', approvals[2], 'Both:', bothApproved);
            
            submitBtn.disabled = !bothApproved;
            
            if (bothApproved) {
                console.log('[Approval] Both approved! Submit button enabled');
            }
        }

        function submitFinal() {
            console.log('[Submit] Submit button clicked');
            
            const title = document.getElementById('finalTitle').value.trim();
            const description = document.getElementById('finalDescription').value.trim();
            
            if (!title || !description) {
                alert('Please enter both title and description before submitting');
                return;
            }

            const titleWords = countWords(title);
            const descWords = countWords(description);
            
            if (titleWords > 5) {
                alert('Title must be 5 words or less (currently ' + titleWords + ' words)');
                return;
            }
            
            if (descWords > 80) {
                alert('Description must be 80 words or less (currently ' + descWords + ' words)');
                return;
            }

            console.log('[Submit] Checking approvals:', approvals);
            
            if (!approvals[1] || !approvals[2]) {
                alert('Both participants must approve before submitting');
                return;
            }

            if (confirm('Are you sure you want to submit? This will end the session for both participants.')) {
                const finalIdea = `Title: ${title}\n\nDescription: ${description}`;
                
                fetch(API_BASE + '/api/submit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        team_id: teamId, 
                        final_idea: finalIdea,
                        title: title,
                        description: description
                    })
                })
                .then(() => {
                    // Stop timer and polling
                    clearInterval(pollInterval);
                    clearInterval(timerInterval);
                    
                    // Go to wait screen
                    document.getElementById('mainContainer').style.display = 'none';
                    document.getElementById('waitScreen').classList.add('active');
                });
            }
        }

        // Survey navigation functions
        function goToSurveyPage1() {
            document.getElementById('waitScreen').classList.remove('active');
            document.getElementById('surveyPage1').classList.add('active');
        }

        function toggleMajorOther() {
            const majorField = document.getElementById('majorField').value;
            const majorOtherDiv = document.getElementById('majorOtherDiv');
            if (majorField === 'Other') {
                majorOtherDiv.style.display = 'block';
            } else {
                majorOtherDiv.style.display = 'none';
            }
        }

        function submitSurveyPage1() {
            // Validate all questions are answered
            const questions = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10'];
            for (let q of questions) {
                if (!document.getElementById(q).value) {
                    alert('Please answer all questions before continuing');
                    return;
                }
            }

            // Collect responses
            const responses = {};
            questions.forEach(q => {
                responses[q] = document.getElementById(q).value;
            });

            // Send to server
            fetch(API_BASE + '/api/survey_page1', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: teamId,
                    participant_id: participantId,
                    ...responses
                })
            })
            .then(() => {
                document.getElementById('surveyPage1').classList.remove('active');
                document.getElementById('surveyPage2').classList.add('active');
            });
        }

        function submitSurveyPage2() {
            // Validate required fields
            const employmentStatus = document.getElementById('employmentStatus').value;
            const majorField = document.getElementById('majorField').value;
            const age = document.getElementById('age').value;
            const gender = document.getElementById('gender').value;

            if (!employmentStatus || !majorField || !age || !gender) {
                alert('Please answer all required questions before continuing');
                return;
            }

            // Validate age is integer
            const ageInt = parseInt(age);
            if (isNaN(ageInt) || ageInt < 18 || ageInt > 100) {
                alert('Please enter a valid age between 18 and 100');
                return;
            }

            // If "Other" major selected, require specification
            const majorOther = document.getElementById('majorOther').value.trim();
            if (majorField === 'Other' && !majorOther) {
                alert('Please specify your major field');
                return;
            }

            // Send to server
            fetch(API_BASE + '/api/survey_page2', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: teamId,
                    participant_id: participantId,
                    employment_status: employmentStatus,
                    major_field: majorField,
                    major_other: majorOther,
                    age: ageInt,
                    gender: gender
                })
            })
            .then(() => {
                document.getElementById('surveyPage2').classList.remove('active');
                document.getElementById('surveyPage3').classList.add('active');
            });
        }

        function submitSurveyPage3() {
            // Validate required fields
            const firstLastName = document.getElementById('firstLastName').value.trim();
            const addressLine1 = document.getElementById('addressLine1').value.trim();
            const addressLine2 = document.getElementById('addressLine2').value.trim();
            const city = document.getElementById('city').value.trim();
            const state = document.getElementById('state').value.trim().toUpperCase();
            const postalCode = document.getElementById('postalCode').value.trim();

            if (!firstLastName || !addressLine1 || !city || !state || !postalCode) {
                alert('Please fill in all required fields');
                return;
            }

            // Validate state is 2 letters
            if (state.length !== 2 || !/^[A-Z]{2}$/.test(state)) {
                alert('State must be a 2-letter abbreviation (e.g., MI, CA, NY)');
                return;
            }

            // Validate postal code is exactly 5 digits
            if (!/^\d{5}$/.test(postalCode)) {
                alert('Postal Code must be exactly 5 digits');
                return;
            }

            // Send to server
            fetch(API_BASE + '/api/survey_page3', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: teamId,
                    participant_id: participantId,
                    first_last_name: firstLastName,
                    address_line1: addressLine1,
                    address_line2: addressLine2,
                    city: city,
                    state: state,
                    postal_code: postalCode
                })
            })
            .then(() => {
                document.getElementById('surveyPage3').classList.remove('active');
                document.getElementById('thankYouScreen').classList.add('active');
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/start_session', methods=['POST'])
def start_session():
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    
    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO teams (team_id) VALUES (?)', (team_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    
    if team_id not in active_teams:
        active_teams[team_id] = {'messages': []}
    
    return jsonify({'success': True, 'team_id': team_id, 'participant_id': participant_id})

@app.route('/api/messages/<team_id>', methods=['GET'])
def get_messages(team_id):
    since_id = request.args.get('since', 0, type=int)
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, role, content, participant_id, timestamp
        FROM messages WHERE team_id = ? AND id > ? ORDER BY id ASC
    ''', (team_id, since_id))
    rows = c.fetchall()
    conn.close()
    
    messages = [{'id': r[0], 'role': r[1], 'content': r[2], 'participant_id': r[3], 'timestamp': r[4]} for r in rows]
    return jsonify({'messages': messages})

@app.route('/api/chat', methods=['POST'])
def chat():
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
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (team_id, participant_id, role, content) VALUES (?, ?, ?, ?)',
              (team_id, participant_id, 'user', user_message))
    conn.commit()
    conn.close()
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=team_session['messages'],
            temperature=0.7,
            max_tokens=1000
        )
        
        assistant_message = response['choices'][0]['message']['content']
        tokens_used = response['usage']['total_tokens']
        
        team_session['messages'].append({'role': 'assistant', 'content': assistant_message})
        
        conn = sqlite3.connect('study_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO messages (team_id, participant_id, role, content, tokens_used) VALUES (?, ?, ?, ?, ?)',
                  (team_id, None, 'assistant', assistant_message, tokens_used))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'response': assistant_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ideas/<team_id>', methods=['GET'])
def get_ideas(team_id):
    since_id = request.args.get('since', 0, type=int)
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, participant_id, idea_text, timestamp
        FROM ideas WHERE team_id = ? AND id > ? ORDER BY id ASC
    ''', (team_id, since_id))
    rows = c.fetchall()
    conn.close()
    
    ideas = [{'id': r[0], 'participant_id': r[1], 'idea_text': r[2], 'timestamp': r[3]} for r in rows]
    return jsonify({'ideas': ideas})

@app.route('/api/add_idea', methods=['POST'])
def add_idea():
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    idea_text = data.get('idea_text')
    
    if not all([team_id, participant_id, idea_text]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO ideas (team_id, participant_id, idea_text) VALUES (?, ?, ?)',
              (team_id, participant_id, idea_text))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/final_idea/<team_id>', methods=['GET'])
def get_final_idea(team_id):
    # Check in-memory store first
    if team_id in active_teams and 'final_data' in active_teams[team_id]:
        return jsonify(active_teams[team_id]['final_data'])
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('SELECT final_idea FROM teams WHERE team_id = ?', (team_id,))
    row = c.fetchone()
    conn.close()
    
    return jsonify({
        'title': '',
        'description': '',
        'final_idea': row[0] if row and row[0] else ''
    })

@app.route('/api/update_final', methods=['POST'])
def update_final():
    data = request.json
    team_id = data.get('team_id')
    title = data.get('title', '')
    description = data.get('description', '')
    
    if not team_id:
        return jsonify({'error': 'Team ID required'}), 400
    
    # Store in memory for real-time sync
    if team_id not in active_teams:
        active_teams[team_id] = {'messages': []}
    
    active_teams[team_id]['final_data'] = {
        'title': title,
        'description': description
    }
    
    # Also update database
    final_idea_combined = f"Title: {title}\n\nDescription: {description}"
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('UPDATE teams SET final_idea = ? WHERE team_id = ?', (final_idea_combined, team_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    team_id = data.get('team_id')
    final_idea = data.get('final_idea')
    
    if not team_id or not final_idea:
        return jsonify({'error': 'Team ID and final idea required'}), 400
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        UPDATE teams 
        SET final_idea = ?, submitted = 1, submit_time = CURRENT_TIMESTAMP 
        WHERE team_id = ?
    ''', (final_idea, team_id))
    conn.commit()
    conn.close()
    
    # Mark as submitted in memory too for real-time sync
    if team_id in team_approvals:
        team_approvals[team_id]['submitted'] = True
    
    return jsonify({'success': True})

@app.route('/api/set_approval', methods=['POST'])
def set_approval():
    data = request.json
    team_id = data.get('team_id')
    participant_id = str(data.get('participant_id'))
    approved = data.get('approved', False)
    
    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400
    
    if team_id not in team_approvals:
        team_approvals[team_id] = {'1': False, '2': False}
    
    team_approvals[team_id][participant_id] = approved
    
    return jsonify({'success': True, 'approvals': team_approvals[team_id]})

@app.route('/api/get_approvals/<team_id>', methods=['GET'])
def get_approvals(team_id):
    if team_id not in team_approvals:
        team_approvals[team_id] = {'1': False, '2': False, 'submitted': False}
    
    return jsonify({
        'approvals': team_approvals[team_id],
        'submitted': team_approvals[team_id].get('submitted', False)
    })

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    team_id = data.get('team_id')
    participant_id = data.get('participant_id')
    
    if not team_id or not participant_id:
        return jsonify({'error': 'Team ID and Participant ID required'}), 400
    
    if team_id not in online_participants:
        online_participants[team_id] = {}
    
    online_participants[team_id][participant_id] = time.time()
    
    return jsonify({'success': True})

@app.route('/api/typing_metrics', methods=['POST'])
def update_typing_metrics():
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
    
    conn = sqlite3.connect('study_data.db')
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

@app.route('/api/online_status/<team_id>', methods=['GET'])
def get_online_status(team_id):
    if team_id not in online_participants:
        return jsonify({'online': {}})
    
    current_time = time.time()
    online = {}
    
    # Consider participant online if heartbeat received within last 5 seconds
    for participant_id, last_heartbeat in online_participants[team_id].items():
        online[participant_id] = (current_time - last_heartbeat) < 5
    
    return jsonify({'online': online})

@app.route('/api/get_timer/<team_id>', methods=['GET'])
def get_timer(team_id):
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('SELECT start_time FROM teams WHERE team_id = ?', (team_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return jsonify({'error': 'Team not found'}), 404
    
    # Parse the start time and calculate time remaining
    start_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
    elapsed_seconds = (datetime.now() - start_time).total_seconds()
    time_remaining = max(0, 30 * 60 - elapsed_seconds)  # 30 minutes total
    
    return jsonify({
        'start_time': row[0],
        'time_remaining': int(time_remaining)
    })

@app.route('/api/export/<team_id>', methods=['GET'])
def export_team_data(team_id):
    conn = sqlite3.connect('study_data.db')
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

@app.route('/api/survey_page1', methods=['POST'])
def save_survey_page1():
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
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO survey_page1 (team_id, participant_id, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, participant_id, data.get('q1'), data.get('q2'), data.get('q3'), data.get('q4'),
          data.get('q5'), data.get('q6'), data.get('q7'), data.get('q8'), data.get('q9'), data.get('q10')))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/survey_page2', methods=['POST'])
def save_survey_page2():
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
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO survey_page2 (team_id, participant_id, employment_status, major_field, major_other, age, gender)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, participant_id, employment_status, major_field, major_other, age_int, gender))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/survey_page3', methods=['POST'])
def save_survey_page3():
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
    
    conn = sqlite3.connect('study_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO survey_page3 (team_id, participant_id, first_last_name, address_line1, address_line2, city, state, postal_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team_id, participant_id, first_last_name, address_line1, address_line2, city, state, postal_code))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)