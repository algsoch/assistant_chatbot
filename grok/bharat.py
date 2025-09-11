import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import json
from pathlib import Path
import shutil
from datetime import datetime
import sys
import logging
import re
import tempfile
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tds_app")

# Try to import the question-answering system
try:
    from vicky_server import answer_question, QUESTIONS_DATA
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    sys.exit("Error: Could not import answer_question from vicky_server. Make sure the file exists in the same directory.")

app = FastAPI(title="TDS - Tools for Data Science",
              description="Interactive assistant for data science questions with accuracy testing")

# Create directories for templates and static files if they don't exist
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
UPLOADS_DIR = Path("uploads")
ACCURACY_DIR = Path("accuracy_tests")

for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, ACCURACY_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Create directory to store JavaScript and CSS files separately
JS_DIR = STATIC_DIR / "js"
CSS_DIR = STATIC_DIR / "css"

for directory in [JS_DIR, CSS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")

# Create a global registry for uploaded files
UPLOADED_FILES_REGISTRY = {}  # Maps unique IDs to actual file paths

# Create a global registry for accuracy tests
ACCURACY_TESTS = {}  # Maps test IDs to test data

# Function to load questions from vickys.json
def load_questions_from_json():
    """Load questions from vickys.json and organize them by category"""
    import json
    import os
    import re
    
    questions_by_category = {
        "GA1": [],
        "GA2": [],
        "GA3": [],
        "GA4": [],
        "GA5": []
    }
    
    try:
        # Load vickys.json file
        json_path = os.path.join("e:", "data science tool", "main", "grok", "vickys.json")
        if not os.path.exists(json_path):
            # Try alternative path
            json_path = "vickys.json"
            
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                questions_data = json.load(f)
            
            # Process each question
            for i, q_data in enumerate(questions_data):
                if "question" not in q_data:
                    continue
                    
                # Extract category from file path or use default
                category = "GA1"  # Default category
                if "file" in q_data:
                    # Extract GA category from file path using regex
                    match = re.search(r'GA(\d+)', q_data["file"])
                    if match:
                        category = f"GA{match.group(1)}"
                
                # Create a question ID
                question_id = f"{category.lower()}-{len(questions_by_category[category]) + 1}"
                
                # Add to the appropriate category
                questions_by_category[category].append({
                    "id": question_id,
                    "text": q_data["question"],
                    "category": category,
                    "file": q_data.get("file", "")  # Include file path if available
                })
        else:
            logger.warning(f"vickys.json not found at {json_path}")
            # Fall back to QUESTIONS_DATA if it exists
            if 'QUESTIONS_DATA' in globals():
                for i, q_data in enumerate(QUESTIONS_DATA):
                    if "question" not in q_data:
                        continue
                        
                    # Extract category from file path or use default
                    category = "GA1"  # Default category
                    if "file" in q_data:
                        # Extract GA category from file path using regex
                        match = re.search(r'GA(\d+)', q_data["file"])
                        if match:
                            category = f"GA{match.group(1)}"
                    
                    # Create a question ID
                    question_id = f"{category.lower()}-{len(questions_by_category[category]) + 1}"
                    
                    # Add to the appropriate category
                    questions_by_category[category].append({
                        "id": question_id,
                        "text": q_data["question"],
                        "category": category,
                        "file": q_data.get("file", "")
                    })
    
    except Exception as e:
        logger.error(f"Error loading questions from JSON: {e}")
        # Return empty lists as fallback
    
    return questions_by_category

# Create CSS file with styles
with open(CSS_DIR / "main.css", "w", encoding="utf-8") as f:
    f.write("""
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
    max-width: 1200px;
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
    position: relative;
}

.question-item:hover {
    background-color: #f5f5f5;
}

.question-item:last-child {
    border-bottom: none;
}

.ask-button {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.question-item:hover .ask-button {
    opacity: 1;
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
    display: flex;
    align-items: center;
    gap: 8px;
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
    margin-left: 10px;
}

.status-bar {
    background-color: var(--primary-color);
    color: white;
    padding: 8px 15px;
    position: fixed;
    bottom: 0;
    left: 0;
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

.files-table {
    width: 100%;
    background-color: white;
    border-collapse: collapse;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.files-table th, .files-table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
.files-table th {
    background-color: #4c2882;
    color: white;
}
.files-table tr:last-child td {
    border-bottom: none;
}
.files-table tr:hover {
    background-color: #f5f5f5;
}
.back-button {
    display: inline-block;
    margin-top: 20px;
    padding: 10px 20px;
    background-color: #4c2882;
    color: white;
    text-decoration: none;
    border-radius: 4px;
}

/* Accuracy testing styles */
.accuracy-testing {
    margin-top: 20px;
    background-color: white;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow);
    overflow: hidden;
}

.accuracy-header {
    padding: 15px;
    background-color: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    gap: 8px;
}

.accuracy-content {
    padding: 20px;
}

.test-info {
    margin-top: 15px;
    border: 1px solid #eee;
    padding: 15px;
    border-radius: var(--border-radius);
}

.test-info h4 {
    margin-top: 0;
    color: var(--primary-color);
}

.accuracy-result {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    font-weight: bold;
}

.accuracy-pass {
    color: var(--success-color);
}

.accuracy-fail {
    color: var(--error-color);
}

.accuracy-buttons {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

.accuracy-button {
    padding: 10px 15px;
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    font-weight: 500;
    transition: var(--transition);
}

.create-test-btn {
    background-color: var(--primary-color);
    color: white;
}

.run-tests-btn {
    background-color: var(--secondary-color);
    color: white;
}

.accuracy-table {
    width: 100%;
    margin-top: 15px;
    border-collapse: collapse;
}

.accuracy-table th, .accuracy-table td {
    padding: 10px;
    border: 1px solid #eee;
    text-align: left;
}

.accuracy-table th {
    background-color: #f9f9f9;
}

.accuracy-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
    color: white;
}

.badge-success {
    background-color: var(--success-color);
}

.badge-error {
    background-color: var(--error-color);
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
""")

# Create JS file for the app logic
with open(JS_DIR / "app.js", "w", encoding="utf-8") as f:
    f.write("""
document.addEventListener('DOMContentLoaded', function() {
    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    const categoryTabs = document.querySelectorAll('.category-tab');
    
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
        console.log("Loading questions for category:", category);
        preloadedQuestionsContainer.innerHTML = '';
        
        if (!window.preloadedQuestions || window.preloadedQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="error">Error loading questions. Please refresh.</div>';
            console.error("preloadedQuestions is empty or undefined");
            return;
        }
        
        const filteredQuestions = window.preloadedQuestions.filter(q => q.category === category);
        console.log(`Found ${filteredQuestions.length} questions for ${category}`);
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = 
                `<div class="notice">No questions available for ${category}</div>`;
            return;
        }
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            
            // Add the Ask button
            const askButton = document.createElement('button');
            askButton.className = 'ask-button';
            askButton.textContent = 'Ask';
            questionItem.appendChild(askButton);
            
            // Full item click handler
            questionItem.addEventListener('click', (e) => {
                // Don't trigger if clicking the button
                if (e.target !== askButton) {
                    questionInput.value = question.text;
                }
            });
            
            // Specific button click handler
            askButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent the item click event
                questionInput.value = question.text;
                // Auto-submit the question on button click
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Handle file upload links
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-link')) {
            if (!confirm('Are you sure you want to delete this file?')) {
                e.preventDefault();
            }
        }
    });
    
    // Function to send questions with file
    window.sendQuestionWithFile = function(event) {
        event.preventDefault();
        const question = document.getElementById('questionInput').value.trim();
        if (!question) return;
        
        // Display user question
        addMessage(question, 'user');
        
        // Clear input
        document.getElementById('questionInput').value = '';
        
        // Display loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('Thinking...', 'bot loading', loadingId);
        
        // Create form data
        const formData = new FormData();
        formData.append('question', question);
        
        // Add file if present
        const fileInput = document.getElementById('fileAttachment');
        if (fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
        }
        
        fetch('/ask_with_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            // Display answer
            if (data.success) {
                // Store the answer for potential accuracy testing
                window.lastQuestion = question;
                window.lastAnswer = data.answer;
                
                addMessage(data.answer || "No response received", 'bot');
                
                // Show add to accuracy test button
                const accuracyBtn = document.createElement('div');
                accuracyBtn.innerHTML = `
                    <button class="accuracy-button create-test-btn" onclick="showCreateTest()">
                        Add to Accuracy Tests
                    </button>
                `;
                chatBox.appendChild(accuracyBtn);
            } else {
                addMessage("Error: " + (data.error || "Unknown error occurred"), 'bot');
            }
        })
        .catch(error => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            console.error('Error:', error);
            addMessage("Sorry, there was an error processing your question.", 'bot');
        });
    };
    
    // Function to add a message to the chat
    window.addMessage = function(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        if (id) messageElement.id = id;
        
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
    
    // Check server status and update the status indicator
    fetch('/health')
        .then(response => {
            if (response.ok) {
                document.querySelector('.status-dot').style.backgroundColor = '#4CAF50'; // Green
            } else {
                document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
            }
        })
        .catch(() => {
            document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
        });
        
    // Load uploaded files list
    window.loadUploadedFiles = function() {
        fetch('/files')
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const filesList = doc.querySelector('.files-table tbody');
                if (filesList) {
                    const uploadedFilesList = document.getElementById('uploadedFilesList');
                    uploadedFilesList.innerHTML = '';
                    
                    Array.from(filesList.querySelectorAll('tr')).forEach(row => {
                        const fileId = row.cells[0].textContent;
                        const fileName = row.cells[1].textContent;
                        
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <span>${fileName} (ID: ${fileId})</span>
                            <div>
                                <a href="#" class="use-file" data-id="${fileId}">Use</a>
                                <a href="#" class="delete-file" data-id="${fileId}">Delete</a>
                            </div>
                        `;
                        uploadedFilesList.appendChild(li);
                    });
                    
                    // Add event listeners to use/delete links
                    document.querySelectorAll('.use-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const fileId = this.dataset.id;
                            questionInput.value += ` with ID ${fileId}`;
                            questionInput.focus();
                        });
                    });
                    
                    document.querySelectorAll('.delete-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            if (confirm('Are you sure you want to delete this file?')) {
                                const fileId = this.dataset.id;
                                fetch(`/delete-file/${fileId}`, { method: 'DELETE' })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.success) {
                                            loadUploadedFiles();
                                        }
                                    });
                            }
                        });
                    });
                }
            });
    };
    
    // Load uploaded files on page load
    loadUploadedFiles();
});

function debugForm() {
    const formData = new FormData();
    formData.append('question', 'Test question');
    
    fetch('/debug-form', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Debug data:', data);
        alert('Check console for debug info');
    });
}

// Accuracy testing functions
window.showCreateTest = function() {
    if (!window.lastQuestion || !window.lastAnswer) {
        alert('No recent question and answer to add to tests.');
        return;
    }
    
    const testModal = document.createElement('div');
    testModal.className = 'test-modal';
    testModal.innerHTML = `
        <div class="test-modal-content">
            <h3>Create Accuracy Test</h3>
            <div class="form-group">
                <label>Test Name:</label>
                <input type="text" id="testName" value="Test-${Date.now()}" class="form-control">
            </div>
            <div class="form-group">
                <label>Question:</label>
                <textarea id="testQuestion" class="form-control" rows="3">${window.lastQuestion}</textarea>
            </div>
            <div class="form-group">
                <label>Expected Answer:</label>
                <textarea id="testExpectedAnswer" class="form-control" rows="5">${window.lastAnswer}</textarea>
            </div>
            <div class="accuracy-buttons">
                <button class="accuracy-button create-test-btn" onclick="createAccuracyTest()">Save Test</button>
                <button class="accuracy-button" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(testModal);
};

window.closeModal = function() {
    const modal = document.querySelector('.test-modal');
    if (modal) {
        modal.remove();
    }
};

window.createAccuracyTest = function() {
    const testName = document.getElementById('testName').value;
    const testQuestion = document.getElementById('testQuestion').value;
    const testExpectedAnswer = document.getElementById('testExpectedAnswer').value;
    
    if (!testName || !testQuestion || !testExpectedAnswer) {
        alert('Please fill in all fields');
        return;
    }
    
    const testData = {
        name: testName,
        question: testQuestion,
        expected_answer: testExpectedAnswer
    };
    
    fetch('/accuracy/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Test created successfully!');
            closeModal();
        } else {
            alert('Error creating test: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error creating test:', error);
        alert('Error creating test. See console for details.');
    });
};

window.runAccuracyTests = function() {
    document.getElementById('testResults').innerHTML = '<div class="loading">Running tests...</div>';
    
    fetch('/accuracy/run')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let resultsHtml = `
                    <h4>Test Results</h4>
                    <div class="accuracy-result">
                        <span>Overall Accuracy: ${data.accuracy_rate}%</span>
                        <span>${data.passed_tests} / ${data.total_tests} tests passed</span>
                    </div>
                    <table class="accuracy-table">
                        <thead>
                            <tr>
                                <th>Test</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.results.forEach(result => {
                    resultsHtml += `
                        <tr>
                            <td>${result.name}</td>
                            <td>
                                <span class="accuracy-badge ${result.passed ? 'badge-success' : 'badge-error'}">
                                    ${result.passed ? 'PASS' : 'FAIL'}
                                </span>
                            </td>
                            <td>
                                <a href="#" onclick="viewTestDetails('${result.id}')">View</a> |
                                <a href="#" onclick="deleteTest('${result.id}')">Delete</a>
                            </td>
                        </tr>
                    `;
                });
                
                resultsHtml += `
                        </tbody>
                    </table>
                `;
                
                document.getElementById('testResults').innerHTML = resultsHtml;
            } else {
                document.getElementById('testResults').innerHTML = `
                    <div class="error">Error running tests: ${data.error}</div>
                `;
            }
        })
        .catch(error => {
            console.error('Error running tests:', error);
            document.getElementById('testResults').innerHTML = `
                <div class="error">Error running tests. See console for details.</div>
            `;
        });
};

window.viewTestDetails = function(testId) {
    fetch(`/accuracy/test/${testId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const testModal = document.createElement('div');
                testModal.className = 'test-modal';
                testModal.innerHTML = `
                    <div class="test-modal-content">
                        <h3>Test Details: ${data.test.name}</h3>
                        <div class="test-details">
                            <h4>Question:</h4>
                            <pre>${data.test.question}</pre>
                            
                            <h4>Expected Answer:</h4>
                            <pre>${data.test.expected_answer}</pre>
                            
                            ${data.test.actual_answer ? `
                                <h4>Actual Answer:</h4>
                                <pre>${data.test.actual_answer}</pre>
                                
                                <div class="accuracy-result ${data.test.passed ? 'accuracy-pass' : 'accuracy-fail'}">
                                    <span>${data.test.passed ? 'PASS' : 'FAIL'}</span>
                                </div>
                            ` : ''}
                        </div>
                        <div class="accuracy-buttons">
                            <button class="accuracy-button" onclick="closeModal()">Close</button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(testModal);
            } else {
                alert('Error fetching test details: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching test details:', error);
            alert('Error fetching test details. See console for details.');
        });
};

window.deleteTest = function(testId) {
    if (confirm('Are you sure you want to delete this test?')) {
        fetch(`/accuracy/test/${testId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Test deleted successfully!');
                runAccuracyTests();
            } else {
                alert('Error deleting test: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting test:', error);
            alert('Error deleting test. See console for details.');
        });
    }
};

// Function to initialize the accuracy testing section
window.initAccuracyTesting = function() {
    // Fetch existing tests
    runAccuracyTests();
};
""")

# Create JS file for preloaded questions
with open(JS_DIR / "preloaded-questions.js", "w", encoding="utf-8") as f:
    # Load questions from vickys.json
    questions_by_category = load_questions_from_json()
    
    # Flatten the questions by category into a single list
    js_questions = []
    for category, questions in questions_by_category.items():
        js_questions.extend(questions)
    
    # Write to the JS file
    f.write(f"// Auto-generated from vickys.json\n")
    f.write(f"window.preloadedQuestions = {json.dumps(js_questions, indent=2)};")

# Create the main template
with open(TEMPLATES_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS - Tools for Data Science</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/main.css">
    <script src="/static/js/preloaded-questions.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS - Tools for Data Science</h1>
            <div class="subtitle">Full support for Graded Assignments 1 to 5 is now available!</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
                <button class="header-button" onclick="location.href='/api/docs'">
                    <i class="fas fa-code"></i> API
                </button>
                <button class="header-button" onclick="location.href='/accuracy'">
                    <i class="fas fa-clipboard-check"></i> Accuracy Tests
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
                        I can help you with various data science tasks and questions, including all assignments for GA1 through GA5.
                        Try asking a question or select one of the preloaded examples from the sidebar.
                    </div>
                </div>
                <div class="input-area">
                    <form class="input-form" id="questionForm" enctype="multipart/form-data" onsubmit="sendQuestionWithFile(event)">
                        <div class="file-attach">
                            <input type="file" id="fileAttachment" name="file">
                            <label for="fileAttachment" class="file-button">
                                <i class="fas fa-paperclip"></i>
                            </label>
                        </div>
                        <input type="text" class="question-input" id="questionInput" placeholder="Ask me anything about data science..." autocomplete="off">
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
                    <div class="category-tab" data-category="GA3">GA3</div>
                    <div class="category-tab" data-category="GA4">GA4</div>
                    <div class="category-tab" data-category="GA5">GA5</div>
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
                <form class="file-input-container" action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" class="file-input" name="file">
                    <button type="submit" class="upload-button">Upload File</button>
                </form>
                <div class="uploaded-files">
                    <h4>Uploaded Files</h4>
                    <ul id="uploadedFilesList">
                        {% if files %}
                            {% for file in files %}
                                <li>
                                    <span>{{ file }}</span>
                                    <div>
                                        <a href="/use-file/{{ file }}">Use</a>
                                        <a href="/delete-file/{{ file }}" class="delete-link">Delete</a>
                                    </div>
                                </li>
                            {% endfor %}
                        {% else %}
                            <li>No files uploaded yet</li>
                        {% endif %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        <div class="status-indicator">
            <span class="status-dot"></span>
            <span>System Online</span>
        </div>
        <div>
            <i class="fas fa-server"></i> Full support for GA1-GA5 enabled
        </div>
        <div>
            <i class="fas fa-code"></i> API Ready
        </div>
    </div>

    <button onclick="debugForm()" style="margin-top:10px;">Debug Form Data</button>

    <script src="/static/js/app.js"></script>
</body>
</html>
""")

# Create the accuracy testing template
with open(TEMPLATES_DIR / "accuracy.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accuracy Testing - TDS</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Accuracy Testing</h1>
            <div class="subtitle">Evaluate answer quality through automated testing</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/'">
                    <i class="fas fa-home"></i> Home
                </button>
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
            </div>
        </header>
        
        <div class="accuracy-testing">
            <div class="accuracy-header">
                <i class="fas fa-clipboard-check"></i> Accuracy Tests
            </div>
            <div class="accuracy-content">
                <p>
                    This page allows you to create and run tests to verify the accuracy of answers provided by the system.
                    Add questions with their expected answers, then run the tests to check if the system produces the correct results.
                </p>
                
                <div class="accuracy-buttons">
                    <button class="accuracy-button create-test-btn" onclick="showCreateTest()">
                        <i class="fas fa-plus"></i> Create New Test
                    </button>
                    <button class="accuracy-button run-tests-btn" onclick="runAccuracyTests()">
                        <i class="fas fa-play"></i> Run All Tests
                    </button>
                </div>
                
                <div class="test-results" id="testResults">
                    <!-- Test results will appear here -->
                    <div class="loading">Loading tests...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="/static/js/preloaded-questions.js"></script>
    <script src="/static/js/app.js"></script>
    <script>
        // Initialize accuracy testing when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            initAccuracyTesting();
        });
    </script>
</body>
</html>
""")

# Define Pydantic models for API
class AccuracyTest(BaseModel):
    name: str
    question: str
    expected_answer: str
    file_id: Optional[str] = None
    
class AccuracyTestResult(BaseModel):
    id: str
    name: str
    passed: bool
    question: str
    expected_answer: str
    actual_answer: Optional[str] = None
    similarity_score: Optional[float] = None

def register_uploaded_file(original_filename, file_path):
    """Register an uploaded file so solution functions can access it"""
    # Generate a unique ID for this file
    import uuid
    file_id = str(uuid.uuid4())[:8]
    
    # Add to registry with metadata
    UPLOADED_FILES_REGISTRY[file_id] = {
        "original_name": original_filename,
        "path": file_path,
        "uploaded_at": datetime.now().isoformat(),
        "type": os.path.splitext(original_filename)[1].lower()
    }
    
    # Return the ID that can be used in queries
    return file_id

def create_accuracy_test(test_data: Dict[str, Any]) -> str:
    """Create a new accuracy test and return its ID"""
    import uuid
    test_id = str(uuid.uuid4())[:8]
    
    # Store the test data
    ACCURACY_TESTS[test_id] = {
        "id": test_id,
        "name": test_data["name"],
        "question": test_data["question"],
        "expected_answer": test_data["expected_answer"],
        "file_id": test_data.get("file_id"),
        "created_at": datetime.now().isoformat()
    }
    
    # Save to disk for persistence
    save_accuracy_tests()
    
    return test_id

def save_accuracy_tests():
    """Save the accuracy tests to disk"""
    try:
        with open(ACCURACY_DIR / "tests.json", "w", encoding="utf-8") as f:
            json.dump(ACCURACY_TESTS, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving accuracy tests: {e}")

def load_accuracy_tests():
    """Load accuracy tests from disk"""
    global ACCURACY_TESTS
    try:
        if (ACCURACY_DIR / "tests.json").exists():
            with open(ACCURACY_DIR / "tests.json", "r", encoding="utf-8") as f:
                ACCURACY_TESTS = json.load(f)
            logger.info(f"Loaded {len(ACCURACY_TESTS)} accuracy tests")
        else:
            logger.info("No accuracy tests file found. Starting with empty test set.")
    except Exception as e:
        logger.error(f"Error loading accuracy tests: {e}")

def run_accuracy_test(test_id: str) -> Dict[str, Any]:
    """Run a single accuracy test and return the result"""
    if test_id not in ACCURACY_TESTS:
        return {"error": "Test not found"}
    
    test = ACCURACY_TESTS[test_id]
    question = test["question"]
    
    # Check if the test uses a file
    if test.get("file_id") and test["file_id"] in UPLOADED_FILES_REGISTRY:
        file_info = UPLOADED_FILES_REGISTRY[test["file_id"]]
        question += f" [Using file: {file_info['path']}]"
    
    try:
        # Process the question
        actual_answer = answer_question(question)
        
        # Compare expected and actual answers
        expected = test["expected_answer"].strip().lower()
        actual = actual_answer.strip().lower()
        
        # Simple exact match first
        passed = expected == actual
        
        # If not an exact match, check for significant overlap
        if not passed:
            # Calculate similarity score (simple word overlap for now)
            expected_words = set(re.findall(r'\b\w+\b', expected))
            actual_words = set(re.findall(r'\b\w+\b', actual))
            
            if len(expected_words) > 0:
                similarity = len(expected_words.intersection(actual_words)) / len(expected_words)
                # Consider it passing if overlap is high enough
                if similarity > 0.8:
                    passed = True
            
        # Update the test with the results
        test["actual_answer"] = actual_answer
        test["passed"] = passed
        test["last_run"] = datetime.now().isoformat()
        
        # Save the updated test data
        save_accuracy_tests()
        
        return {
            "id": test_id,
            "name": test["name"],
            "passed": passed,
            "question": test["question"],
            "expected_answer": test["expected_answer"],
            "actual_answer": actual_answer
        }
    except Exception as e:
        logger.error(f"Error running accuracy test: {e}")
        return {
            "id": test_id,
            "name": test["name"],
            "passed": False,
            "question": test["question"],
            "expected_answer": test["expected_answer"],
            "actual_answer": str(e),
            "error": str(e)
        }

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Get list of uploaded files
    files = []
    if UPLOADS_DIR.exists():
        files = [f.name for f in UPLOADS_DIR.iterdir() if f.is_file()]
    
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "files": files}
    )

@app.get("/health")
async def health_check():
    """Endpoint to check if the server is running correctly"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    try:
        logger.info(f"Processing question: {question[:50]}...")
        
        # Check if the question references any uploaded files by ID
        file_ids = re.findall(r'\b([0-9a-f]{8})\b', question)
        
        # If we found file IDs, add their paths to the question
        if file_ids:
            for file_id in file_ids:
                if file_id in UPLOADED_FILES_REGISTRY:
                    # Add the actual file path to the question text
                    file_info = UPLOADED_FILES_REGISTRY[file_id]
                    file_ext = file_info["type"].lower()
                    
                    # Add appropriate context based on file type
                    if file_ext == ".zip":
                        question += f" The ZIP file is located at {file_info['path']}"
                    elif file_ext == ".md":
                        question += f" The README.md file is located at {file_info['path']}"
                    else:
                        # Generic handling for other file types
                        question += f" The file {file_info['original_name']} is located at {file_info['path']}"
        
        # Process the question with the augmented information
        answer = answer_question(question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing your question: {str(e)}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save uploaded file
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = UPLOADS_DIR / filename
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Register the file and get an ID
        file_id = register_uploaded_file(file.filename, str(file_path))
        
        logger.info(f"File uploaded: {filename} (ID: {file_id})")
        
        # Add a message to the chat interface about the uploaded file
        file_type = os.path.splitext(file.filename)[1].lower()
        usage_example = ""
        if file_type == ".zip":
            usage_example = f"Extract data from ZIP file with ID {file_id}"
        elif file_type == ".md":
            usage_example = f"Run npx prettier on README.md with ID {file_id}"
        
        return {
            "filename": filename,
            "file_id": file_id,
            "message": f"File uploaded successfully (ID: {file_id}). Example usage: '{usage_example}'"
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/use-file/{filename}")
async def use_file(filename: str, request: Request):
    # Redirect back to the chat interface with the filename in a query parameter
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return RedirectResponse(url=f"/?file={filename}")

@app.get("/files")
async def list_files(request: Request):
    """Show all uploaded files and their IDs"""
    files_info = []
    for file_id, info in UPLOADED_FILES_REGISTRY.items():
        files_info.append({
            "id": file_id,
            "name": info["original_name"],
            "type": info["type"],
            "uploaded_at": info["uploaded_at"]
        })
    
    return templates.TemplateResponse(
        "files.html",
        {"request": request, "files": files_info}
    )

# Create a template for the files page
with open(TEMPLATES_DIR / "files.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Uploaded Files - TDS</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Uploaded Files</h1>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/'">
                    <i class="fas fa-home"></i> Home
                </button>
            </div>
        </header>
        
        {% if files %}
        <table class="files-table">
            <thead>
                <tr>
                    <th>File ID</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Uploaded At</th>
                    <th>Usage Example</th>
                </tr>
            </thead>
            <tbody>
                {% for file in files %}
                <tr>
                    <td>{{ file.id }}</td>
                    <td>{{ file.name }}</td>
                    <td>{{ file.type }}</td>
                    <td># filepath: e:\data science tool\main\grok\bharat.py
import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import json
from pathlib import Path
import shutil
from datetime import datetime
import sys
import logging
import re
import tempfile
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tds_app")

# Try to import the question-answering system
try:
    from vicky_server import answer_question, QUESTIONS_DATA
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    sys.exit("Error: Could not import answer_question from vicky_server. Make sure the file exists in the same directory.")

app = FastAPI(title="TDS - Tools for Data Science",
              description="Interactive assistant for data science questions with accuracy testing")

# Create directories for templates and static files if they don't exist
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
UPLOADS_DIR = Path("uploads")
ACCURACY_DIR = Path("accuracy_tests")

for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, ACCURACY_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Create directory to store JavaScript and CSS files separately
JS_DIR = STATIC_DIR / "js"
CSS_DIR = STATIC_DIR / "css"

for directory in [JS_DIR, CSS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")

# Create a global registry for uploaded files
UPLOADED_FILES_REGISTRY = {}  # Maps unique IDs to actual file paths

# Create a global registry for accuracy tests
ACCURACY_TESTS = {}  # Maps test IDs to test data

# Function to load questions from vickys.json
def load_questions_from_json():
    """Load questions from vickys.json and organize them by category"""
    import json
    import os
    import re
    
    questions_by_category = {
        "GA1": [],
        "GA2": [],
        "GA3": [],
        "GA4": [],
        "GA5": []
    }
    
    try:
        # Load vickys.json file
        json_path = os.path.join("e:", "data science tool", "main", "grok", "vickys.json")
        if not os.path.exists(json_path):
            # Try alternative path
            json_path = "vickys.json"
            
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                questions_data = json.load(f)
            
            # Process each question
            for i, q_data in enumerate(questions_data):
                if "question" not in q_data:
                    continue
                    
                # Extract category from file path or use default
                category = "GA1"  # Default category
                if "file" in q_data:
                    # Extract GA category from file path using regex
                    match = re.search(r'GA(\d+)', q_data["file"])
                    if match:
                        category = f"GA{match.group(1)}"
                
                # Create a question ID
                question_id = f"{category.lower()}-{len(questions_by_category[category]) + 1}"
                
                # Add to the appropriate category
                questions_by_category[category].append({
                    "id": question_id,
                    "text": q_data["question"],
                    "category": category,
                    "file": q_data.get("file", "")  # Include file path if available
                })
        else:
            logger.warning(f"vickys.json not found at {json_path}")
            # Fall back to QUESTIONS_DATA if it exists
            if 'QUESTIONS_DATA' in globals():
                for i, q_data in enumerate(QUESTIONS_DATA):
                    if "question" not in q_data:
                        continue
                        
                    # Extract category from file path or use default
                    category = "GA1"  # Default category
                    if "file" in q_data:
                        # Extract GA category from file path using regex
                        match = re.search(r'GA(\d+)', q_data["file"])
                        if match:
                            category = f"GA{match.group(1)}"
                    
                    # Create a question ID
                    question_id = f"{category.lower()}-{len(questions_by_category[category]) + 1}"
                    
                    # Add to the appropriate category
                    questions_by_category[category].append({
                        "id": question_id,
                        "text": q_data["question"],
                        "category": category,
                        "file": q_data.get("file", "")
                    })
    
    except Exception as e:
        logger.error(f"Error loading questions from JSON: {e}")
        # Return empty lists as fallback
    
    return questions_by_category

# Create CSS file with styles
with open(CSS_DIR / "main.css", "w", encoding="utf-8") as f:
    f.write("""
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
    max-width: 1200px;
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
    position: relative;
}

.question-item:hover {
    background-color: #f5f5f5;
}

.question-item:last-child {
    border-bottom: none;
}

.ask-button {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.question-item:hover .ask-button {
    opacity: 1;
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
    display: flex;
    align-items: center;
    gap: 8px;
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
    margin-left: 10px;
}

.status-bar {
    background-color: var(--primary-color);
    color: white;
    padding: 8px 15px;
    position: fixed;
    bottom: 0;
    left: 0;
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

.files-table {
    width: 100%;
    background-color: white;
    border-collapse: collapse;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.files-table th, .files-table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
.files-table th {
    background-color: #4c2882;
    color: white;
}
.files-table tr:last-child td {
    border-bottom: none;
}
.files-table tr:hover {
    background-color: #f5f5f5;
}
.back-button {
    display: inline-block;
    margin-top: 20px;
    padding: 10px 20px;
    background-color: #4c2882;
    color: white;
    text-decoration: none;
    border-radius: 4px;
}

/* Accuracy testing styles */
.accuracy-testing {
    margin-top: 20px;
    background-color: white;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow);
    overflow: hidden;
}

.accuracy-header {
    padding: 15px;
    background-color: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    gap: 8px;
}

.accuracy-content {
    padding: 20px;
}

.test-info {
    margin-top: 15px;
    border: 1px solid #eee;
    padding: 15px;
    border-radius: var(--border-radius);
}

.test-info h4 {
    margin-top: 0;
    color: var(--primary-color);
}

.accuracy-result {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    font-weight: bold;
}

.accuracy-pass {
    color: var(--success-color);
}

.accuracy-fail {
    color: var(--error-color);
}

.accuracy-buttons {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

.accuracy-button {
    padding: 10px 15px;
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    font-weight: 500;
    transition: var(--transition);
}

.create-test-btn {
    background-color: var(--primary-color);
    color: white;
}

.run-tests-btn {
    background-color: var(--secondary-color);
    color: white;
}

.accuracy-table {
    width: 100%;
    margin-top: 15px;
    border-collapse: collapse;
}

.accuracy-table th, .accuracy-table td {
    padding: 10px;
    border: 1px solid #eee;
    text-align: left;
}

.accuracy-table th {
    background-color: #f9f9f9;
}

.accuracy-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
    color: white;
}

.badge-success {
    background-color: var(--success-color);
}

.badge-error {
    background-color: var(--error-color);
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
""")

# Create JS file for the app logic
with open(JS_DIR / "app.js", "w", encoding="utf-8") as f:
    f.write("""
document.addEventListener('DOMContentLoaded', function() {
    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    const categoryTabs = document.querySelectorAll('.category-tab');
    
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
        console.log("Loading questions for category:", category);
        preloadedQuestionsContainer.innerHTML = '';
        
        if (!window.preloadedQuestions || window.preloadedQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="error">Error loading questions. Please refresh.</div>';
            console.error("preloadedQuestions is empty or undefined");
            return;
        }
        
        const filteredQuestions = window.preloadedQuestions.filter(q => q.category === category);
        console.log(`Found ${filteredQuestions.length} questions for ${category}`);
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = 
                `<div class="notice">No questions available for ${category}</div>`;
            return;
        }
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            
            // Add the Ask button
            const askButton = document.createElement('button');
            askButton.className = 'ask-button';
            askButton.textContent = 'Ask';
            questionItem.appendChild(askButton);
            
            // Full item click handler
            questionItem.addEventListener('click', (e) => {
                // Don't trigger if clicking the button
                if (e.target !== askButton) {
                    questionInput.value = question.text;
                }
            });
            
            // Specific button click handler
            askButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent the item click event
                questionInput.value = question.text;
                // Auto-submit the question on button click
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Handle file upload links
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-link')) {
            if (!confirm('Are you sure you want to delete this file?')) {
                e.preventDefault();
            }
        }
    });
    
    // Function to send questions with file
    window.sendQuestionWithFile = function(event) {
        event.preventDefault();
        const question = document.getElementById('questionInput').value.trim();
        if (!question) return;
        
        // Display user question
        addMessage(question, 'user');
        
        // Clear input
        document.getElementById('questionInput').value = '';
        
        // Display loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('Thinking...', 'bot loading', loadingId);
        
        // Create form data
        const formData = new FormData();
        formData.append('question', question);
        
        // Add file if present
        const fileInput = document.getElementById('fileAttachment');
        if (fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
        }
        
        fetch('/ask_with_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            // Display answer
            if (data.success) {
                // Store the answer for potential accuracy testing
                window.lastQuestion = question;
                window.lastAnswer = data.answer;
                
                addMessage(data.answer || "No response received", 'bot');
                
                // Show add to accuracy test button
                const accuracyBtn = document.createElement('div');
                accuracyBtn.innerHTML = `
                    <button class="accuracy-button create-test-btn" onclick="showCreateTest()">
                        Add to Accuracy Tests
                    </button>
                `;
                chatBox.appendChild(accuracyBtn);
            } else {
                addMessage("Error: " + (data.error || "Unknown error occurred"), 'bot');
            }
        })
        .catch(error => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            console.error('Error:', error);
            addMessage("Sorry, there was an error processing your question.", 'bot');
        });
    };
    
    // Function to add a message to the chat
    window.addMessage = function(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        if (id) messageElement.id = id;
        
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
    
    // Check server status and update the status indicator
    fetch('/health')
        .then(response => {
            if (response.ok) {
                document.querySelector('.status-dot').style.backgroundColor = '#4CAF50'; // Green
            } else {
                document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
            }
        })
        .catch(() => {
            document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
        });
        
    // Load uploaded files list
    window.loadUploadedFiles = function() {
        fetch('/files')
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const filesList = doc.querySelector('.files-table tbody');
                if (filesList) {
                    const uploadedFilesList = document.getElementById('uploadedFilesList');
                    uploadedFilesList.innerHTML = '';
                    
                    Array.from(filesList.querySelectorAll('tr')).forEach(row => {
                        const fileId = row.cells[0].textContent;
                        const fileName = row.cells[1].textContent;
                        
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <span>${fileName} (ID: ${fileId})</span>
                            <div>
                                <a href="#" class="use-file" data-id="${fileId}">Use</a>
                                <a href="#" class="delete-file" data-id="${fileId}">Delete</a>
                            </div>
                        `;
                        uploadedFilesList.appendChild(li);
                    });
                    
                    // Add event listeners to use/delete links
                    document.querySelectorAll('.use-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const fileId = this.dataset.id;
                            questionInput.value += ` with ID ${fileId}`;
                            questionInput.focus();
                        });
                    });
                    
                    document.querySelectorAll('.delete-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            if (confirm('Are you sure you want to delete this file?')) {
                                const fileId = this.dataset.id;
                                fetch(`/delete-file/${fileId}`, { method: 'DELETE' })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.success) {
                                            loadUploadedFiles();
                                        }
                                    });
                            }
                        });
                    });
                }
            });
    };
    
    // Load uploaded files on page load
    loadUploadedFiles();
});

function debugForm() {
    const formData = new FormData();
    formData.append('question', 'Test question');
    
    fetch('/debug-form', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Debug data:', data);
        alert('Check console for debug info');
    });
}

// Accuracy testing functions
window.showCreateTest = function() {
    if (!window.lastQuestion || !window.lastAnswer) {
        alert('No recent question and answer to add to tests.');
        return;
    }
    
    const testModal = document.createElement('div');
    testModal.className = 'test-modal';
    testModal.innerHTML = `
        <div class="test-modal-content">
            <h3>Create Accuracy Test</h3>
            <div class="form-group">
                <label>Test Name:</label>
                <input type="text" id="testName" value="Test-${Date.now()}" class="form-control">
            </div>
            <div class="form-group">
                <label>Question:</label>
                <textarea id="testQuestion" class="form-control" rows="3">${window.lastQuestion}</textarea>
            </div>
            <div class="form-group">
                <label>Expected Answer:</label>
                <textarea id="testExpectedAnswer" class="form-control" rows="5">${window.lastAnswer}</textarea>
            </div>
            <div class="accuracy-buttons">
                <button class="accuracy-button create-test-btn" onclick="createAccuracyTest()">Save Test</button>
                <button class="accuracy-button" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(testModal);
};

window.closeModal = function() {
    const modal = document.querySelector('.test-modal');
    if (modal) {
        modal.remove();
    }
};

window.createAccuracyTest = function() {
    const testName = document.getElementById('testName').value;
    const testQuestion = document.getElementById('testQuestion').value;
    const testExpectedAnswer = document.getElementById('testExpectedAnswer').value;
    
    if (!testName || !testQuestion || !testExpectedAnswer) {
        alert('Please fill in all fields');
        return;
    }
    
    const testData = {
        name: testName,
        question: testQuestion,
        expected_answer: testExpectedAnswer
    };
    
    fetch('/accuracy/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Test created successfully!');
            closeModal();
        } else {
            alert('Error creating test: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error creating test:', error);
        alert('Error creating test. See console for details.');
    });
};

window.runAccuracyTests = function() {
    document.getElementById('testResults').innerHTML = '<div class="loading">Running tests...</div>';
    
    fetch('/accuracy/run')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let resultsHtml = `
                    <h4>Test Results</h4>
                    <div class="accuracy-result">
                        <span>Overall Accuracy: ${data.accuracy_rate}%</span>
                        <span>${data.passed_tests} / ${data.total_tests} tests passed</span>
                    </div>
                    <table class="accuracy-table">
                        <thead>
                            <tr>
                                <th>Test</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.results.forEach(result => {
                    resultsHtml += `
                        <tr>
                            <td>${result.name}</td>
                            <td>
                                <span class="accuracy-badge ${result.passed ? 'badge-success' : 'badge-error'}">
                                    ${result.passed ? 'PASS' : 'FAIL'}
                                </span>
                            </td>
                            <td>
                                <a href="#" onclick="viewTestDetails('${result.id}')">View</a> |
                                <a href="#" onclick="deleteTest('${result.id}')">Delete</a>
                            </td>
                        </tr>
                    `;
                });
                
                resultsHtml += `
                        </tbody>
                    </table>
                `;
                
                document.getElementById('testResults').innerHTML = resultsHtml;
            } else {
                document.getElementById('testResults').innerHTML = `
                    <div class="error">Error running tests: ${data.error}</div>
                `;
            }
        })
        .catch(error => {
            console.error('Error running tests:', error);
            document.getElementById('testResults').innerHTML = `
                <div class="error">Error running tests. See console for details.</div>
            `;
        });
};

window.viewTestDetails = function(testId) {
    fetch(`/accuracy/test/${testId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const testModal = document.createElement('div');
                testModal.className = 'test-modal';
                testModal.innerHTML = `
                    <div class="test-modal-content">
                        <h3>Test Details: ${data.test.name}</h3>
                        <div class="test-details">
                            <h4>Question:</h4>
                            <pre>${data.test.question}</pre>
                            
                            <h4>Expected Answer:</h4>
                            <pre>${data.test.expected_answer}</pre>
                            
                            ${data.test.actual_answer ? `
                                <h4>Actual Answer:</h4>
                                <pre>${data.test.actual_answer}</pre>
                                
                                <div class="accuracy-result ${data.test.passed ? 'accuracy-pass' : 'accuracy-fail'}">
                                    <span>${data.test.passed ? 'PASS' : 'FAIL'}</span>
                                </div>
                            ` : ''}
                        </div>
                        <div class="accuracy-buttons">
                            <button class="accuracy-button" onclick="closeModal()">Close</button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(testModal);
            } else {
                alert('Error fetching test details: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching test details:', error);
            alert('Error fetching test details. See console for details.');
        });
};

window.deleteTest = function(testId) {
    if (confirm('Are you sure you want to delete this test?')) {
        fetch(`/accuracy/test/${testId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Test deleted successfully!');
                runAccuracyTests();
            } else {
                alert('Error deleting test: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting test:', error);
            alert('Error deleting test. See console for details.');
        });
    }
};

// Function to initialize the accuracy testing section
window.initAccuracyTesting = function() {
    // Fetch existing tests
    runAccuracyTests();
};

# Create JS file for preloaded questions
with open(JS_DIR / "preloaded-questions.js", "w", encoding="utf-8") as f:
    # Load questions from vickys.json
    questions_by_category = load_questions_from_json()
    
    # Flatten the questions by category into a single list
    js_questions = []
    for category, questions in questions_by_category.items():
        js_questions.extend(questions)
    
    # Write to the JS file
    f.write(f"// Auto-generated from vickys.json\n")
    f.write(f"window.preloadedQuestions = {json.dumps(js_questions, indent=2)};")

# Create the main template
with open(TEMPLATES_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS - Tools for Data Science</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/main.css">
    <script src="/static/js/preloaded-questions.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS - Tools for Data Science</h1>
            <div class="subtitle">Full support for Graded Assignments 1 to 5 is now available!</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
                <button class="header-button" onclick="location.href='/api/docs'">
                    <i class="fas fa-code"></i> API
                </button>
                <button class="header-button" onclick="location.href='/accuracy'">
                    <i class="fas fa-clipboard-check"></i> Accuracy Tests
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
                        I can help you with various data science tasks and questions, including all assignments for GA1 through GA5.
                        Try asking a question or select one of the preloaded examples from the sidebar.
                    </div>
                </div>
                <div class="input-area">
                    <form class="input-form" id="questionForm" enctype="multipart/form-data" onsubmit="sendQuestionWithFile(event)">
                        <div class="file-attach">
                            <input type="file" id="fileAttachment" name="file">
                            <label for="fileAttachment" class="file-button">
                                <i class="fas fa-paperclip"></i>
                            </label>
                        </div>
                        <input type="text" class="question-input" id="questionInput" placeholder="Ask me anything about data science..." autocomplete="off">
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
                    <div class="category-tab" data-category="GA3">GA3</div>
                    <div class="category-tab" data-category="GA4">GA4</div>
                    <div class="category-tab" data-category="GA5">GA5</div>
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
                <form class="file-input-container" action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" class="file-input" name="file">
                    <button type="submit" class="upload-button">Upload File</button>
                </form>
                <div class="uploaded-files">
                    <h4>Uploaded Files</h4>
                    <ul id="uploadedFilesList">
                        {% if files %}
                            {% for file in files %}
                                <li>
                                    <span>{{ file }}</span>
                                    <div>
                                        <a href="/use-file/{{ file }}">Use</a>
                                        <a href="/delete-file/{{ file }}" class="delete-link">Delete</a>
                                    </div>
                                </li>
                            {% endfor %}
                        {% else %}
                            <li>No files uploaded yet</li>
                        {% endif %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        <div class="status-indicator">
            <span class="status-dot"></span>
            <span>System Online</span>
        </div>
        <div>
            <i class="fas fa-server"></i> Full support for GA1-GA5 enabled
        </div>
        <div>
            <i class="fas fa-code"></i> API Ready
        </div>
    </div>

    <button onclick="debugForm()" style="margin-top:10px;">Debug Form Data</button>

    <script src="/static/js/app.js"></script>
</body>
</html>
""")

# Create the accuracy testing template
with open(TEMPLATES_DIR / "accuracy.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accuracy Testing - TDS</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Accuracy Testing</h1>
            <div class="subtitle">Evaluate answer quality through automated testing</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/'">
                    <i class="fas fa-home"></i> Home
                </button>
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
            </div>
        </header>
        
        <div class="accuracy-testing">
            <div class="accuracy-header">
                <i class="fas fa-clipboard-check"></i> Accuracy Tests
            </div>
            <div class="accuracy-content">
                <p>
                    This page allows you to create and run tests to verify the accuracy of answers provided by the system.
                    Add questions with their expected answers, then run the tests to check if the system produces the correct results.
                </p>
                
                <div class="accuracy-buttons">
                    <button class="accuracy-button create-test-btn" onclick="showCreateTest()">
                        <i class="fas fa-plus"></i> Create New Test
                    </button>
                    <button class="accuracy-button run-tests-btn" onclick="runAccuracyTests()">
                        <i class="fas fa-play"></i> Run All Tests
                    </button>
                </div>
                
                <div class="test-results" id="testResults">
                    <!-- Test results will appear here -->
                    <div class="loading">Loading tests...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="/static/js/preloaded-questions.js"></script>
    <script src="/static/js/app.js"></script>
    <script>
        // Initialize accuracy testing when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            initAccuracyTesting();
        });
    </script>
</body>
</html>


# Create files.html template
with open(TEMPLATES_DIR / "files.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Uploaded Files - TDS</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Uploaded Files</h1>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/'">
                    <i class="fas fa-home"></i> Home
                </button>
            </div>
        </header>
        
        {% if files %}
        <table class="files-table">
            <thead>
                <tr>
                    <th>File ID</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Uploaded At</th>
                    <th>Usage Example</th>
                </tr>
            </thead>
            <tbody>
                {% for file in files %}
                <tr>
                    <td>{{ file.id }}</td>
                    <td>{{ file.name }}</td>
                    <td>{{ file.type }}</td>
                    <td>{{ file.uploaded_at }}</td>
                    <td>
                        {% if file.type == '.md' %}
                            Run npx prettier on README.md with ID {{ file.id }}
                        {% elif file.type == '.zip' %}
                            Extract data from ZIP file with ID {{ file.id }}
                        {% else %}
                            Process file with ID {{ file.id }}
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No files have been uploaded yet.</p>
        {% endif %}
        
        <a href="/" class="back-button">Back to Chat</a>
    </div>
</body>
</html>
""")

@app.post("/ask_with_file")
async def ask_question_with_file(request: Request, question: str = Form(...), file: Optional[UploadFile] = File(None)):
    try:
        logger.info(f"Processing question with file: {question[:50]}...")
        
        file_id = None
        if file:
            # Save the uploaded file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            
            # Add file context to the question
            question += f" [Using file: {file_path}]"
        
        # Process the question with the augmented information
        answer = answer_question(question)
        
        return {"success": True, "answer": answer, "file_id": file_id}
    except Exception as e:
        logger.error(f"Error processing question with file: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/delete-file/{file_id}")
async def delete_file(file_id: str):
    if file_id in UPLOADED_FILES_REGISTRY:
        try:
            file_path = UPLOADED_FILES_REGISTRY[file_id]["path"]
            os.remove(file_path)
            del UPLOADED_FILES_REGISTRY[file_id]
            return {"success": True}
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "File not found"}

@app.get("/accuracy", response_class=HTMLResponse)
async def accuracy_testing_page(request: Request):
    """Render the accuracy testing page"""
    return templates.TemplateResponse("accuracy.html", {"request": request})

@app.post("/accuracy/create")
async def create_test(test: AccuracyTest):
    try:
        test_id = create_accuracy_test(test.dict())
        return {"success": True, "test_id": test_id}
    except Exception as e:
        logger.error(f"Error creating accuracy test: {e}")
        return {"success": False, "error": str(e)}

@app.get("/accuracy/run")
async def run_tests():
    try:
        # Load the tests in case there are any new ones
        load_accuracy_tests()
        
        # Run all tests
        results = []
        passed_tests = 0
        
        if not ACCURACY_TESTS:
            return {"success": True, "results": [], "passed_tests": 0, "total_tests": 0, "accuracy_rate": 0}
        
        # Run each test
        for test_id in ACCURACY_TESTS:
            result = run_accuracy_test(test_id)
            if result.get("passed", False):
                passed_tests += 1
            results.append(result)
        
        # Calculate accuracy rate
        total_tests = len(results)
        accuracy_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        return {
            "success": True,
            "results": results,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "accuracy_rate": round(accuracy_rate, 2)
        }
    except Exception as e:
        logger.error(f"Error running accuracy tests: {e}")
        return {"success": False, "error": str(e)}

@app.get("/accuracy/test/{test_id}")
async def get_test_details(test_id: str):
    if test_id in ACCURACY_TESTS:
        return {"success": True, "test": ACCURACY_TESTS[test_id]}
    return {"success": False, "error": "Test not found"}

@app.delete("/accuracy/test/{test_id}")
async def delete_test(test_id: str):
    if test_id in ACCURACY_TESTS:
        try:
            del ACCURACY_TESTS[test_id]
            save_accuracy_tests()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error deleting accuracy test {test_id}: {e}")
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Test not found"}

@app.post("/debug-form")
async def debug_form(request: Request):
    """Debug form data - just returns what was received"""
    form_data = await request.form()
    form_dict = {key: form_data[key] for key in form_data}
    return {"received_form_data": form_dict}

@app.on_event("startup")
async def startup_event():
    """Execute on server startup"""
    # Ensure all necessary directories exist
    for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, ACCURACY_DIR]:
        directory.mkdir(exist_ok=True)
    
    # Load any saved accuracy tests
    load_accuracy_tests()
    
    # Log successful startup
    logger.info("Server started successfully")

# Run the app if executed directly
if __name__ == "__main__":
    # Configure the server
    port = 5000
    host = "0.0.0.0"  # Listen on all network interfaces
    
    print(f"Starting server at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    
    # Run with uvicorn
    uvicorn.run(app, host=host, port=port)