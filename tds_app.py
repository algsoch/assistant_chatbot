import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
import shutil
from datetime import datetime
import sys
import logging
import re
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tds_app")

# Try to import the question-answering system
try:
    from vicky_server import answer_question
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    sys.exit("Error: Could not import answer_question from vicky_server. Make sure the file exists in the same directory.")

app = FastAPI(title="TDS - Tools for Data Science",
              description="Interactive assistant for data science questions")

# Create directories for templates and static files if they don't exist
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
UPLOADS_DIR = Path("uploads")

for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Preloaded questions for both GA1 and GA2
PRELOADED_QUESTIONS = [
    # GA1 Questions
    {"id": "ga1-1", "text": "What is the output of code -s?", "category": "GA1"},
    {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
    {"id": "ga1-3", "text": "How to use npx and prettier with README.md?", "category": "GA1"},
    {"id": "ga1-4", "text": "Google Sheets formula with SEQUENCE and ARRAY_CONSTRAIN", "category": "GA1"},
    {"id": "ga1-5", "text": "Excel formula with SORTBY and TAKE", "category": "GA1"},
    {"id": "ga1-6", "text": "Find hidden input value on a webpage", "category": "GA1"},
    {"id": "ga1-7", "text": "How many Wednesdays are in a date range?", "category": "GA1"},
    {"id": "ga1-8", "text": "Extract data from CSV in a ZIP file", "category": "GA1"},
    
    # GA2 Questions
    {"id": "ga2-1", "text": "Write Python code to count pixels by brightness in an image", "category": "GA2"},
    {"id": "ga2-2", "text": "How to set up a git hook to enforce commit message format?", "category": "GA2"},
    {"id": "ga2-3", "text": "Join datasets using SQLModel in Python", "category": "GA2"},
    {"id": "ga2-4", "text": "Display a world map using Matplotlib", "category": "GA2"},
    {"id": "ga2-5", "text": "Create a MIDI file with a simple melody", "category": "GA2"},
    {"id": "ga2-6", "text": "Generate a fake dataset with scikit-learn", "category": "GA2"},
    {"id": "ga2-7", "text": "Download and visualize weather data", "category": "GA2"},
    {"id": "ga2-8", "text": "Create a simple interactive dashboard with Plotly", "category": "GA2"},
    {"id": "ga2-9", "text": "Create a FastAPI server for student data", "category": "GA2"},
    {"id": "ga2-10", "text": "Set up a Llama model with ngrok tunnel", "category": "GA2"}
]

# Create the HTML template file with enhanced styling and preloaded questions
with open(TEMPLATES_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS - Tools for Data Science</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #4c2882;
            --primary-light: #6b3eb6;
            --secondary-color: #37bb9c;
            --dark-color: #2c2c2c;
            --light-color: #f5f5f5;
            --success-color: #4CAF50;
            --error-color: #f44336;
            --warning-color: #ff9800;
            --text-color: #333;
            --border-radius: 8px;
            --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--light-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }
        
        header::after {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            background: radial-gradient(circle at top right, rgba(255,255,255,0.2), transparent);
            pointer-events: none;
        }
        
        h1 {
            margin: 0;
            font-size: 32px;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        }
        
        .subtitle {
            font-style: italic;
            opacity: 0.9;
            margin-top: 10px;
            font-weight: 300;
        }
        
        .header-buttons {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }
        
        .header-button {
            background-color: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .header-button:hover {
            background-color: rgba(255,255,255,0.3);
        }
        
        .main-section {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .chat-container {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .chat-box {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            background-color: white;
        }
        
        .message {
            padding: 12px 18px;
            border-radius: 18px;
            margin-bottom: 15px;
            max-width: 85%;
            word-wrap: break-word;
            position: relative;
            animation: fadeIn 0.3s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            background-color: #e3f2fd;
            margin-left: auto;
            border-top-right-radius: 4px;
            text-align: right;
        }
        
        .bot-message {
            background-color: #f5f5f5;
            margin-right: auto;
            border-top-left-radius: 4px;
            white-space: pre-wrap;
        }
        
        .bot-message.loading {
            background-color: #f0f0f0;
            color: #666;
        }
        
        .bot-message.loading::after {
            content: '⏳';
            margin-left: 5px;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.5; }
            50% { opacity: 1; }
            100% { opacity: 0.5; }
        }
        
        .input-area {
            padding: 15px;
            background-color: #f9f9f9;
            border-top: 1px solid #eee;
        }
        
        .input-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .question-input {
            flex-grow: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 16px;
            background-color: white;
            transition: var(--transition);
        }
        
        .question-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(76, 40, 130, 0.1);
        }
        
        .file-attach {
            position: relative;
        }
        
        .file-attach input[type="file"] {
            position: absolute;
            width: 0.1px;
            height: 0.1px;
            opacity: 0;
            overflow: hidden;
            z-index: -1;
        }
        
        .file-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: var(--secondary-color);
            color: white;
            border-radius: 50%;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .file-button:hover {
            background-color: #2ea58a;
        }
        
        .send-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            transition: var(--transition);
        }
        
        .send-button:hover {
            background-color: var(--primary-light);
        }
        
        .sidebar {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .sidebar-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            font-weight: bold;
        }
        
        .question-categories {
            display: flex;
            border-bottom: 1px solid #eee;
        }
        
        .category-tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            transition: var(--transition);
        }
        
        .category-tab.active {
            border-bottom-color: var(--primary-color);
            color: var(--primary-color);
        }
        
        .preloaded-questions {
            flex-grow: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .question-item {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .question-item:hover {
            background-color: #f5f5f5;
        }
        
        .question-item:last-child {
            border-bottom: none;
        }
        
        .file-upload-section {
            margin-top: 20px;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        
        .file-upload-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
        }
        
        .file-upload-content {
            padding: 20px;
        }
        
        .file-input-container {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .file-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            background-color: white;
        }
        
        .upload-button {
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: var(--transition);
        }
        
        .upload-button:hover {
            background-color: var(--primary-light);
        }
        
        .uploaded-files h4 {
            margin-top: 0;
            margin-bottom: 10px;
            color: var(--primary-color);
        }
        
        .uploaded-files ul {
            list-style: none;
            padding: 0;
        }
        
        .uploaded-files li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .uploaded-files li:last-child {
            border-bottom: none;
        }
        
        .uploaded-files a {
            color: var(--primary-color);
            text-decoration: none;
            font-size: 14px;
        }
        
        .status-bar {
            background-color: var(--primary-color);
            color: white;
            padding: 8px 15px;
            position: fixed;
            bottom: 0;
            width: 100%;
            text-align: center;
            font-size: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            z-index: 1000;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success-color);
            border-radius: 50%;
        }
        
        code {
            background-color: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }
        
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #eee;
            margin: 10px 0;
        }
        
        .code-block {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            margin: 10px 0;
            position: relative;
        }
        
        .code-block::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 8px;
            background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        .copy-button {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #ddd;
            border-radius: 3px;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .copy-button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        @media (max-width: 900px) {
            .main-section {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                height: 300px;
            }
            
            .status-bar {
                flex-direction: column;
                gap: 5px;
                padding: 5px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS - Tools for Data Science</h1>
            <div class="subtitle">Full support for Graded Assignments 1 & 2 is now available!</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
                <button class="header-button" onclick="location.href='/api/docs'">
                    <i class="fas fa-code"></i> API
                </button>
            </div>
        </header>
        
        <div class="main-section">
    <!-- Chat container (left side) -->
    <div class="chat-container">
        <div class="chat-box" id="chatBox">
            <!-- Initial welcome message -->
            <div class="message bot-message">
                <strong>Welcome to TDS - Tools for Data Science!</strong><br><br>
                I can help you with various data science tasks and questions, including all assignments for GA1 and GA2. 
                Try asking a question or select one of the preloaded examples from the sidebar.
            </div>
        </div>
        <div class="input-area">
            <form class="input-form" id="questionForm">
                <div class="file-attach">
                    <input type="file" id="fileInput" multiple />
                    <label for="fileInput" class="file-button">
                        <i class="fas fa-paperclip"></i>
                    </label>
                </div>
                <input type="text" class="question-input" id="questionInput" placeholder="Ask me anything about data science..." autocomplete="off" />
                <button type="submit" class="send-button">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </form>
        </div>
    </div>
    
    <!-- Sidebar with preloaded questions (right side) -->
    <div class="sidebar">
        <div class="sidebar-header">Graded Assignment Questions</div>
        <div class="question-categories">
            <div class="category-tab active" data-category="GA1">GA1</div>
            <div class="category-tab" data-category="GA2">GA2</div>
        </div>
        <div class="preloaded-questions" id="preloadedQuestions">
            <!-- Questions will be loaded here by JavaScript -->
        </div>
    </div>
</div>

<!-- File upload section -->
<div class="file-upload-section">
    <div class="file-upload-header">
        <i class="fas fa-cloud-upload-alt"></i> File Repository
    </div>
    <div class="file-upload-content">
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="file-input-container">
                <input type="file" class="file-input" id="fileUploadInput" multiple />
                <button type="submit" class="upload-button">Upload</button>
            </div>
        </form>
        <div class="uploaded-files">
            <h4>Uploaded Files</h4>
            <ul id="uploadedFilesList">
                <!-- List of uploaded files will appear here -->
            </ul>
        </div>
    </div>
</div>

<!-- Status bar -->
<div class="status-bar">
    <div class="status-indicator">
        <span class="status-dot"></span>
        <span>System Online</span>
    </div>
    <div>
        <i class="fas fa-server"></i> Full support for GA1 & GA2 enabled
    </div>
    <div>
        <i class="fas fa-code"></i> API Ready
    </div>
</div>

<script>
    // Preloaded questions data from server
    const preloadedQuestions = [
        // GA1 Questions
        {"id": "ga1-1", "text": "What is the output of code -s?", "category": "GA1"},
        {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
        {"id": "ga1-3", "text": "How to use npx and prettier with README.md?", "category": "GA1"},
        {"id": "ga1-4", "text": "Google Sheets formula with SEQUENCE and ARRAY_CONSTRAIN", "category": "GA1"},
        {"id": "ga1-5", "text": "Excel formula with SORTBY and TAKE", "category": "GA1"},
        {"id": "ga1-6", "text": "Find hidden input value on a webpage", "category": "GA1"},
        {"id": "ga1-7", "text": "How many Wednesdays are in a date range?", "category": "GA1"},
        {"id": "ga1-8", "text": "Extract data from CSV in a ZIP file", "category": "GA1"},
        
        // GA2 Questions
        {"id": "ga2-1", "text": "Write Python code to count pixels by brightness in an image", "category": "GA2"},
        {"id": "ga2-2", "text": "How to set up a git hook to enforce commit message format?", "category": "GA2"},
        {"id": "ga2-3", "text": "Join datasets using SQLModel in Python", "category": "GA2"},
        {"id": "ga2-4", "text": "Display a world map using Matplotlib", "category": "GA2"},
        {"id": "ga2-5", "text": "Create a MIDI file with a simple melody", "category": "GA2"},
        {"id": "ga2-6", "text": "Generate a fake dataset with scikit-learn", "category": "GA2"},
        {"id": "ga2-7", "text": "Download and visualize weather data", "category": "GA2"},
        {"id": "ga2-8", "text": "Create a simple interactive dashboard with Plotly", "category": "GA2"},
        {"id": "ga2-9", "text": "Create a FastAPI server for student data", "category": "GA2"},
        {"id": "ga2-10", "text": "Set up a Llama model with ngrok tunnel", "category": "GA2"}
    ];

    document.addEventListener('DOMContentLoaded', function() {
        const chatBox = document.getElementById('chatBox');
        const questionForm = document.getElementById('questionForm');
        const questionInput = document.getElementById('questionInput');
        const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
        const categoryTabs = document.querySelectorAll('.category-tab');
        const uploadForm = document.getElementById('uploadForm');
        const uploadedFilesList = document.getElementById('uploadedFilesList');
        
        // Initialize with GA1 questions
        displayPreloadedQuestions('GA1');
        
        // Handle category switching
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Update active tab
                categoryTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Display questions for the selected category
                displayPreloadedQuestions(this.dataset.category);
            });
        });
        
        // Display preloaded questions for a specific category
        function displayPreloadedQuestions(category) {
            preloadedQuestionsContainer.innerHTML = '';
            
            const filteredQuestions = preloadedQuestions.filter(q => q.category === category);
            
            filteredQuestions.forEach(question => {
                const questionItem = document.createElement('div');
                questionItem.className = 'question-item';
                questionItem.textContent = question.text;
                questionItem.addEventListener('click', () => {
                    questionInput.value = question.text;
                    // Optional: Auto-submit the question
                    // questionForm.dispatchEvent(new Event('submit'));
                });
                
                preloadedQuestionsContainer.appendChild(questionItem);
            });
        }
        
        // Handle question submission
        questionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const question = questionInput.value.trim();
            if (!question) return;
            
            // Add user message
            addMessage(question, 'user');
            
            // Add loading indicator
            const loadingMessageElement = addMessage('Thinking...', 'bot loading');
            
            // Clear input
            questionInput.value = '';
            
            // Send question to API
            fetch('/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: question })
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading indicator
                loadingMessageElement.remove();
                
                // Add bot response
                addMessage(data.answer, 'bot');
            })
            .catch(error => {
                // Remove loading indicator
                loadingMessageElement.remove();
                
                // Add error message
                addMessage('Sorry, there was an error processing your request. Please try again.', 'bot');
                console.error('Error:', error);
            });
        });
        
        // Handle file upload
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileUploadInput');
            if (!fileInput.files.length) return;
            
            const formData = new FormData();
            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append('files', fileInput.files[i]);
            }
            
            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Clear file input
                fileInput.value = '';
                
                // Refresh uploaded files list
                loadUploadedFiles();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error uploading files. Please try again.');
            });
        });
        
        // Function to add a message to the chat
        function addMessage(text, type) {
            const messageElement = document.createElement('div');
            messageElement.className = `message ${type}-message`;
            
            // Process code blocks if it's a bot message
            if (type === 'bot' || type === 'bot loading') {
                // Simple code block detection for ```code``` blocks
                text = text.replace(/```([^`]+)```/g, function(match, codeContent) {
                    return `<div class="code-block">${codeContent}<button class="copy-button">Copy</button></div>`;
                });
                
                // Inline code detection for `code`
                text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
            }
            
            messageElement.innerHTML = text;
            
            // Add copy functionality to code blocks
            if (type === 'bot') {
                setTimeout(() => {
                    messageElement.querySelectorAll('.copy-button').forEach(button => {
                        button.addEventListener('click', function() {
                            const codeBlock = this.parentNode;
                            const code = codeBlock.textContent.replace('Copy', '').trim();
                            
                            navigator.clipboard.writeText(code).then(() => {
                                this.textContent = 'Copied!';
                                setTimeout(() => { this.textContent = 'Copy'; }, 2000);
                            });
                        });
                    });
                }, 0);
            }
            
            chatBox.appendChild(messageElement);
            chatBox.scrollTop = chatBox.scrollHeight;
            
            return messageElement;
        }
        
        // Function to load uploaded files
        function loadUploadedFiles() {
            fetch('/api/files')
            .then(response => response.json())
            .then(data => {
                uploadedFilesList.innerHTML = '';
                
                if (data.files && data.files.length) {
                    data.files.forEach(file => {
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <span>${file.name}</span>
                            <div>
                                <a href="/files/${file.name}" target="_blank">View</a>
                                <a href="#" class="delete-file" data-file="${file.name}">Delete</a>
                            </div>
                        `;
                        uploadedFilesList.appendChild(li);
                    });
                    
                    // Add delete functionality
                    document.querySelectorAll('.delete-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const fileName = this.dataset.file;
                            
                            fetch(`/api/files/${fileName}`, { method: 'DELETE' })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    loadUploadedFiles();
                                } else {
                                    alert('Error deleting file');
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                alert('Error deleting file');
                            });
                        });
                    });
                } else {
                    uploadedFilesList.innerHTML = '<li>No files uploaded yet</li>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                uploadedFilesList.innerHTML = '<li>Error loading files</li>';
            });
        }
        
        // Load uploaded files on page load
        loadUploadedFiles();
    });
</script>
</body>
</html>
""")

# Mount static files directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve uploaded files
app.mount("/files", StaticFiles(directory=UPLOADS_DIR), name="files")

# Define API routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    with open(TEMPLATES_DIR / "index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/ask")
async def ask_question(request: Request):
    data = await request.json()
    question = data.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        # Call the question-answering system
        answer = answer_question(question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        return {"answer": f"Sorry, I encountered an error: {str(e)}"}

@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    uploaded_files = []
    for file in files:
        file_path = UPLOADS_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        uploaded_files.append(file.filename)
    
    return {"success": True, "files": uploaded_files}

@app.get("/api/files")
async def list_files():
    files = []
    for file_path in UPLOADS_DIR.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    
    return {"files": files}

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.remove(file_path)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# Files browser page
@app.get("/files", response_class=HTMLResponse)
async def files_page():
    files_html = """<!DOCTYPE html>
    <html>
    <head>
        <title>TDS - Files Repository</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #4c2882;
            }
            .file-list {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
            }
            .file-item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
            }
            .file-item:last-child {
                border-bottom: none;
            }
            .back-button {
                display: inline-block;
                margin-top: 20px;
                padding: 8px 15px;
                background-color: #4c2882;
                color: white;
                border-radius: 5px;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <h1>Files Repository</h1>
        <div class="file-list" id="fileList">
            Loading files...
        </div>
        <a href="/" class="back-button">Back to Dashboard</a>
        
        <script>
            // Fetch and display files
            fetch('/api/files')
                .then(response => response.json())
                .then(data => {
                    const fileList = document.getElementById('fileList');
                    if (data.files && data.files.length) {
                        fileList.innerHTML = '';
                        data.files.forEach(file => {
                            const fileItem = document.createElement('div');
                            fileItem.className = 'file-item';
                            fileItem.innerHTML = `
                                <span>${file.name}</span>
                                <a href="/files/${file.name}" target="_blank">View</a>
                            `;
                            fileList.appendChild(fileItem);
                        });
                    } else {
                        fileList.innerHTML = 'No files available';
                    }
                })
                .catch(error => {
                    console.error('Error fetching files:', error);
                    document.getElementById('fileList').innerHTML = 'Error loading files';
                });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=files_html)

# Start the server when the script is run directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)