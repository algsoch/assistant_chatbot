import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import glob
from pathlib import Path
import shutil
from datetime import datetime
import sys
import logging
import re
import json
import asyncio
from typing import Optional, List, Dict, Any
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("vicky_assistant")

# Try to import the question-answering system
try:
    from vicky_server import answer_question
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    
    # Provide fallback implementation for testing
    def answer_question(question):
        logger.warning("Using mock answer_question function!")
        return f"This is a mock answer for: {question}"
    
    logger.warning("Using mock answer_question function as fallback")

# Initialize FastAPI app
app = FastAPI(
    title="Vicky - Data Science Assistant",
    description="Advanced assistant for data science and graded assignments GA1-GA5",
    version="2.0.0"
)

# Create directories for templates and static files
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
STATIC_CSS_DIR = STATIC_DIR / "css"
STATIC_JS_DIR = STATIC_DIR / "js"
STATIC_IMG_DIR = STATIC_DIR / "img"
UPLOADS_DIR = Path("uploads")
CACHE_DIR = Path("cache")

# Create all required directories
for directory in [TEMPLATES_DIR, STATIC_DIR, STATIC_CSS_DIR, STATIC_JS_DIR, 
                 STATIC_IMG_DIR, UPLOADS_DIR, CACHE_DIR]:
    directory.mkdir(exist_ok=True)
    logger.info(f"Directory {directory} is ready")

# Function to extract questions from solution files and save to vickys.json
def extract_questions_to_json():
    """Extract questions from solution files and save to vickys.json"""
    ga_folders = ["GA1", "GA2", "GA3", "GA4", "GA5"]
    questions = []
    
    for ga in ga_folders:
        path = f"E://data science tool//{ga}//*.py"
        for file in glob.glob(path):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract docstring or comment block that might contain the question
                    question_match = re.search(r'"""(.*?)"""', content, re.DOTALL) or \
                                    re.search(r"'''(.*?)'''", content, re.DOTALL) or \
                                    re.search(r'/\*(.*?)\*/', content, re.DOTALL)
                    
                    if question_match:
                        question_text = question_match.group(1).strip()
                        # Limit to first 300 chars if too long
                        if len(question_text) > 300:
                            question_text = question_text[:297] + "..."
                        
                        questions.append({
                            "file": file.replace("\\", "//"),
                            "question": question_text
                        })
            except Exception as e:
                logger.error(f"Error processing {file}: {e}")
    
    # Save to JSON
    vickys_json_path = STATIC_DIR / "vickys.json"
    with open(vickys_json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2)
    
    logger.info(f"Extracted {len(questions)} questions to vickys.json")
    return questions

# Create vickys.json if it doesn't exist
vickys_json_path = STATIC_DIR / "vickys.json"
if not vickys_json_path.exists():
    sample_data = [
        {
            "file": "E://data science tool//GA5//first.py",
            "question": "You need to clean this Excel data and calculate the total margin for all transactions that satisfy the following criteria..."
        }
    ]
    # Try to extract real questions if possible
    try:
        questions = extract_questions_to_json()
        if not questions:  # If extraction failed, use sample data
            with open(vickys_json_path, "w", encoding="utf-8") as f:
                json.dump(sample_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to extract questions: {e}")
        with open(vickys_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2)

# Create CSS file
css_file_path = STATIC_CSS_DIR / "styles.css"
if not css_file_path.exists():
    with open(css_file_path, "w", encoding="utf-8") as f:
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

/* Container styles */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Header styles */
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

/* Vicky branding styles */
.vicky-header {
    display: flex;
    align-items: center;
    gap: 15px;
}

.vicky-logo {
    width: 60px;
    height: 60px;
    background-color: var(--secondary-color);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    color: white;
    font-weight: bold;
    box-shadow: 0 3px 5px rgba(0,0,0,0.2);
}

.vicky-info {
    flex-grow: 1;
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

/* Main section styles */
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

/* Sidebar styles */
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

/* Enhanced category tabs for GA1-GA5 */
.category-container {
    display: flex;
    overflow-x: auto;
    border-bottom: 1px solid #eee;
    scrollbar-width: thin;
}

.category-tab {
    flex: 0 0 auto;
    padding: 8px 15px;
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

.search-container {
    padding: 10px;
    background-color: #f5f5f5;
    border-bottom: 1px solid #eee;
}

.search-input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 15px;
    font-size: 14px;
}

.search-input:focus {
    outline: none;
    border-color: var(--primary-color);
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

.no-questions {
    padding: 15px;
    color: #666;
    font-style: italic;
    text-align: center;
}

/* File upload section */
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

/* Status bar */
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

/* Code styles */
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

/* Files table */
.files-table {
    width: 100%;
    background-color: white;
    border-collapse: collapse;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

.files-table th,
.files-table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

.files-table th {
    background-color: #f5f5f5;
    font-weight: 600;
    color: var(--primary-color);
}

.files-table tr:last-child td {
    border-bottom: none;
}

.files-table tr:hover {
    background-color: #f9f9f9;
}

.file-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

.file-actions a {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    text-decoration: none;
    color: white;
    background-color: var(--primary-color);
    transition: var(--transition);
}

.file-actions a:hover {
    background-color: var(--primary-light);
}

.file-actions .delete-btn {
    background-color: var(--error-color);
}

.file-actions .delete-btn:hover {
    background-color: #d32f2f;
}

/* File preview */
.file-preview-area {
    padding: 10px 15px;
    border-top: 1px solid #eee;
    background-color: #f9f9f9;
}

.file-preview {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background-color: white;
    border: 1px solid #ddd;
    border-radius: var(--border-radius);
}

.file-info {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
}

.remove-file {
    background: none;
    border: none;
    color: var(--error-color);
    font-size: 18px;
    cursor: pointer;
}

.remove-file:hover {
    color: #d32f2f;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main-section {
        grid-template-columns: 1fr;
    }
    
    .sidebar {
        height: auto;
        max-height: 300px;
    }
    
    .chat-container {
        height: 50vh;
    }
    
    .header-buttons {
        position: static;
        margin-top: 15px;
    }
    
    .vicky-header {
        flex-direction: column;
        text-align: center;
    }
    
    .status-bar {
        flex-direction: column;
        padding: 10px;
    }
}
""")

# Create main.js with enhanced functionality
js_file_path = STATIC_JS_DIR / "main.js"
if not js_file_path.exists():
    with open(js_file_path, "w", encoding="utf-8") as f:
        f.write("""
// Load questions from vickys.json
document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    const filePreview = document.getElementById('filePreview');
    const fileAttachment = document.getElementById('fileAttachment');
    const categoryTabs = document.querySelectorAll('.category-tab');
    
    // Enable file preview
    if (fileAttachment) {
        fileAttachment.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const fileInfo = document.createElement('div');
                fileInfo.className = 'file-preview';
                fileInfo.innerHTML = `<div class="file-info">
                    <i class="fas fa-file"></i> ${file.name} (${(file.size/1024).toFixed(1)} KB)
                    <button type="button" class="remove-file">×</button>
                </div>`;
                
                if (filePreview) {
                    filePreview.innerHTML = '';
                    filePreview.appendChild(fileInfo);
                    
                    // Add remove functionality
                    const removeButton = filePreview.querySelector('.remove-file');
                    if (removeButton) {
                        removeButton.addEventListener('click', function() {
                            fileAttachment.value = '';
                            filePreview.innerHTML = '';
                        });
                    }
                }
            }
        });
    }
    
    // Fetch questions from vickys.json
    fetch('/static/vickys.json')
        .then(response => response.json())
        .then(data => {
            // Process and organize questions by category
            const questionsByCategory = processQuestionsData(data);
            
            // Initialize with GA1 questions
            displayPreloadedQuestions('GA1', questionsByCategory);
            
            // Handle category switching
            categoryTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    categoryTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Display questions for the selected category
                    displayPreloadedQuestions(this.dataset.category, questionsByCategory);
                });
            });
            
            // Setup search functionality
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                searchInput.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    const activeCategory = document.querySelector('.category-tab.active').dataset.category;
                    
                    // Filter questions based on search term
                    displayFilteredQuestions(activeCategory, questionsByCategory, searchTerm);
                });
            }
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            // Fallback to empty message
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">Failed to load questions. Please try again later.</div>';
        });
    
    // Function to process the JSON data into categorized question objects
    function processQuestionsData(data) {
        const questionsByCategory = {
            'GA1': [], 'GA2': [], 'GA3': [], 'GA4': [], 'GA5': [], 'Other': []
        };
        
        data.forEach((item, index) => {
            if (item.file && item.question) {
                // Extract the category (GA1, GA2, etc.) from the file path
                const match = item.file.match(/GA(\d+)/i);
                const category = match ? `GA${match[1]}` : 'Other';
                
                // Create a shortened version of the question for display
                const shortQuestion = item.question.split('.')[0].substring(0, 80) + '...';
                
                const questionObj = {
                    id: `question-${index}`,
                    text: shortQuestion,
                    fullText: item.question,
                    file: item.file
                };
                
                // Add to appropriate category
                if (questionsByCategory[category]) {
                    questionsByCategory[category].push(questionObj);
                } else {
                    questionsByCategory['Other'].push(questionObj);
                }
            }
        });
        
        return questionsByCategory;
    }
    
    // Display questions from a specific category
    function displayPreloadedQuestions(category, questionsByCategory) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const questions = questionsByCategory[category] || [];
        
        if (questions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No questions available for this category.</div>';
            return;
        }
        
        questions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText; // For tooltip and search
            questionItem.dataset.file = question.file;
            
            questionItem.addEventListener('click', () => {
                questionInput.value = question.fullText.substring(0, 200) + '...';
                // Auto-submit the question on click if desired
                // questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Filter and display questions based on search term
    function displayFilteredQuestions(category, questionsByCategory, searchTerm) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const questions = questionsByCategory[category] || [];
        const filteredQuestions = questions.filter(q => 
            q.text.toLowerCase().includes(searchTerm) || 
            q.fullText.toLowerCase().includes(searchTerm)
        );
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No matching questions found.</div>';
            return;
        }
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText;
            questionItem.dataset.file = question.file;
            
            questionItem.addEventListener('click', () => {
                questionInput.value = question.fullText.substring(0, 200) + '...';
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Function to send questions with file
    window.sendQuestionWithFile = function(event) {
        event.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;
        
        // Display user question
        addMessage(question, 'user');
        
        // Clear input
        questionInput.value = '';
        
        // Display loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('Thinking...', 'bot loading', loadingId);
        
        // Create form data
        const formData = new FormData();
        formData.append('question', question);
        
        // Add file if present
        if (fileAttachment && fileAttachment.files.length > 0) {
            formData.append('file', fileAttachment.files[0]);
            
            // Clear file preview
            if (filePreview) {
                filePreview.innerHTML = '';
            }
            fileAttachment.value = '';
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
                addMessage(data.answer || "No response received", 'bot');
                
                // Save to session history
                saveToHistory(question, data.answer);
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
    function addMessage(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        if (id) messageElement.id = id;
        
        // Process code blocks if it's a bot message
        if (type === 'bot' || type === 'bot loading') {
            // Code block detection for ```code``` blocks
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
                # filepath: e:\data science tool\main\grok\vicky_main.py""")
import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import glob
from pathlib import Path
import shutil
from datetime import datetime
import sys
import logging
import re
import json
import asyncio
from typing import Optional, List, Dict, Any
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("vicky_assistant")

# Try to import the question-answering system
try:
    from vicky_server import answer_question
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    
    # Provide fallback implementation for testing
    def answer_question(question):
        logger.warning("Using mock answer_question function!")
        return f"This is a mock answer for: {question}"
    
    logger.warning("Using mock answer_question function as fallback")

# Initialize FastAPI app
app = FastAPI(
    title="Vicky - Data Science Assistant",
    description="Advanced assistant for data science and graded assignments GA1-GA5",
    version="2.0.0"
)

# Create directories for templates and static files
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
STATIC_CSS_DIR = STATIC_DIR / "css"
STATIC_JS_DIR = STATIC_DIR / "js"
STATIC_IMG_DIR = STATIC_DIR / "img"
UPLOADS_DIR = Path("uploads")
CACHE_DIR = Path("cache")

# Create all required directories
for directory in [TEMPLATES_DIR, STATIC_DIR, STATIC_CSS_DIR, STATIC_JS_DIR, 
                 STATIC_IMG_DIR, UPLOADS_DIR, CACHE_DIR]:
    directory.mkdir(exist_ok=True)
    logger.info(f"Directory {directory} is ready")

# Function to extract questions from solution files and save to vickys.json
def extract_questions_to_json():
    """Extract questions from solution files and save to vickys.json"""
    ga_folders = ["GA1", "GA2", "GA3", "GA4", "GA5"]
    questions = []
    
    for ga in ga_folders:
        path = f"E://data science tool//{ga}//*.py"
        for file in glob.glob(path):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract docstring or comment block that might contain the question
                    question_match = re.search(r'"""(.*?)"""', content, re.DOTALL) or \
                                    re.search(r"'''(.*?)'''", content, re.DOTALL) or \
                                    re.search(r'/\*(.*?)\*/', content, re.DOTALL)
                    
                    if question_match:
                        question_text = question_match.group(1).strip()
                        # Limit to first 300 chars if too long
                        if len(question_text) > 300:
                            question_text = question_text[:297] + "..."
                        
                        questions.append({
                            "file": file.replace("\\", "//"),
                            "question": question_text
                        })
            except Exception as e:
                logger.error(f"Error processing {file}: {e}")
    
    # Save to JSON
    vickys_json_path = STATIC_DIR / "vickys.json"
    with open(vickys_json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2)
    
    logger.info(f"Extracted {len(questions)} questions to vickys.json")
    return questions

# Create vickys.json if it doesn't exist
vickys_json_path = STATIC_DIR / "vickys.json"
if not vickys_json_path.exists():
    sample_data = [
        {
            "file": "E://data science tool//GA5//first.py",
            "question": "You need to clean this Excel data and calculate the total margin for all transactions that satisfy the following criteria..."
        }
    ]
    # Try to extract real questions if possible
    try:
        questions = extract_questions_to_json()
        if not questions:  # If extraction failed, use sample data
            with open(vickys_json_path, "w", encoding="utf-8") as f:
                json.dump(sample_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to extract questions: {e}")
        with open(vickys_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2)

# Create CSS file
css_file_path = STATIC_CSS_DIR / "styles.css"
if not css_file_path.exists():
    with open(css_file_path, "w", encoding="utf-8") as f:
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

/* Container styles */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Header styles */
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

/* Vicky branding styles */
.vicky-header {
    display: flex;
    align-items: center;
    gap: 15px;
}

.vicky-logo {
    width: 60px;
    height: 60px;
    background-color: var(--secondary-color);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    color: white;
    font-weight: bold;
    box-shadow: 0 3px 5px rgba(0,0,0,0.2);
}

.vicky-info {
    flex-grow: 1;
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

/* Main section styles */
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

/* Sidebar styles */
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

/* Enhanced category tabs for GA1-GA5 */
.category-container {
    display: flex;
    overflow-x: auto;
    border-bottom: 1px solid #eee;
    scrollbar-width: thin;
}

.category-tab {
    flex: 0 0 auto;
    padding: 8px 15px;
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

.search-container {
    padding: 10px;
    background-color: #f5f5f5;
    border-bottom: 1px solid #eee;
}

.search-input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 15px;
    font-size: 14px;
}

.search-input:focus {
    outline: none;
    border-color: var(--primary-color);
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

.no-questions {
    padding: 15px;
    color: #666;
    font-style: italic;
    text-align: center;
}

/* File upload section */
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

/* Status bar */
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

/* Code styles */
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

/* Files table */
.files-table {
    width: 100%;
    background-color: white;
    border-collapse: collapse;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

.files-table th,
.files-table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

.files-table th {
    background-color: #f5f5f5;
    font-weight: 600;
    color: var(--primary-color);
}

.files-table tr:last-child td {
    border-bottom: none;
}

.files-table tr:hover {
    background-color: #f9f9f9;
}

.file-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

.file-actions a {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    text-decoration: none;
    color: white;
    background-color: var(--primary-color);
    transition: var(--transition);
}

.file-actions a:hover {
    background-color: var(--primary-light);
}

.file-actions .delete-btn {
    background-color: var(--error-color);
}

.file-actions .delete-btn:hover {
    background-color: #d32f2f;
}

/* File preview */
.file-preview-area {
    padding: 10px 15px;
    border-top: 1px solid #eee;
    background-color: #f9f9f9;
}

.file-preview {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background-color: white;
    border: 1px solid #ddd;
    border-radius: var(--border-radius);
}

.file-info {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
}

.remove-file {
    background: none;
    border: none;
    color: var(--error-color);
    font-size: 18px;
    cursor: pointer;
}

.remove-file:hover {
    color: #d32f2f;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main-section {
        grid-template-columns: 1fr;
    }
    
    .sidebar {
        height: auto;
        max-height: 300px;
    }
    
    .chat-container {
        height: 50vh;
    }
    
    .header-buttons {
        position: static;
        margin-top: 15px;
    }
    
    .vicky-header {
        flex-direction: column;
        text-align: center;
    }
    
    .status-bar {
        flex-direction: column;
        padding: 10px;
    }
}
""")

# Create main.js with enhanced functionality
js_file_path = STATIC_JS_DIR / "main.js"
if not js_file_path.exists():
    with open(js_file_path, "w", encoding="utf-8") as f:
        f.write("""
// Load questions from vickys.json
document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    const filePreview = document.getElementById('filePreview');
    const fileAttachment = document.getElementById('fileAttachment');
    const categoryTabs = document.querySelectorAll('.category-tab');
    
    // Enable file preview
    if (fileAttachment) {
        fileAttachment.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const fileInfo = document.createElement('div');
                fileInfo.className = 'file-preview';
                fileInfo.innerHTML = `<div class="file-info">
                    <i class="fas fa-file"></i> ${file.name} (${(file.size/1024).toFixed(1)} KB)
                    <button type="button" class="remove-file">×</button>
                </div>`;
                
                if (filePreview) {
                    filePreview.innerHTML = '';
                    filePreview.appendChild(fileInfo);
                    
                    // Add remove functionality
                    const removeButton = filePreview.querySelector('.remove-file');
                    if (removeButton) {
                        removeButton.addEventListener('click', function() {
                            fileAttachment.value = '';
                            filePreview.innerHTML = '';
                        });
                    }
                }
            }
        });
    }
    
    // Fetch questions from vickys.json
    fetch('/static/vickys.json')
        .then(response => response.json())
        .then(data => {
            // Process and organize questions by category
            const questionsByCategory = processQuestionsData(data);
            
            // Initialize with GA1 questions
            displayPreloadedQuestions('GA1', questionsByCategory);
            
            // Handle category switching
            categoryTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    categoryTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Display questions for the selected category
                    displayPreloadedQuestions(this.dataset.category, questionsByCategory);
                });
            });
            
            // Setup search functionality
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                searchInput.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    const activeCategory = document.querySelector('.category-tab.active').dataset.category;
                    
                    // Filter questions based on search term
                    displayFilteredQuestions(activeCategory, questionsByCategory, searchTerm);
                });
            }
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            // Fallback to empty message
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">Failed to load questions. Please try again later.</div>';
        });
    
    // Function to process the JSON data into categorized question objects
    function processQuestionsData(data) {
        const questionsByCategory = {
            'GA1': [], 'GA2': [], 'GA3': [], 'GA4': [], 'GA5': [], 'Other': []
        };
        
        data.forEach((item, index) => {
            if (item.file && item.question) {
                // Extract the category (GA1, GA2, etc.) from the file path
                const match = item.file.match(/GA(\d+)/i);
                const category = match ? `GA${match[1]}` : 'Other';
                
                // Create a shortened version of the question for display
                const shortQuestion = item.question.split('.')[0].substring(0, 80) + '...';
                
                const questionObj = {
                    id: `question-${index}`,
                    text: shortQuestion,
                    fullText: item.question,
                    file: item.file
                };
                
                // Add to appropriate category
                if (questionsByCategory[category]) {
                    questionsByCategory[category].push(questionObj);
                } else {
                    questionsByCategory['Other'].push(questionObj);
                }
            }
        });
        
        return questionsByCategory;
    }
    
    // Display questions from a specific category
    function displayPreloadedQuestions(category, questionsByCategory) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const questions = questionsByCategory[category] || [];
        
        if (questions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No questions available for this category.</div>';
            return;
        }
        
        questions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText; // For tooltip and search
            questionItem.dataset.file = question.file;
            
            questionItem.addEventListener('click', () => {
                questionInput.value = question.fullText.substring(0, 200) + '...';
                // Auto-submit the question on click if desired
                // questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Filter and display questions based on search term
    function displayFilteredQuestions(category, questionsByCategory, searchTerm) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const questions = questionsByCategory[category] || [];
        const filteredQuestions = questions.filter(q => 
            q.text.toLowerCase().includes(searchTerm) || 
            q.fullText.toLowerCase().includes(searchTerm)
        );
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No matching questions found.</div>';
            return;
        }
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText;
            questionItem.dataset.file = question.file;
            
            questionItem.addEventListener('click', () => {
                questionInput.value = question.fullText.substring(0, 200) + '...';
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Function to send questions with file
    window.sendQuestionWithFile = function(event) {
        event.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;
        
        // Display user question
        addMessage(question, 'user');
        
        // Clear input
        questionInput.value = '';
        
        // Display loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('Thinking...', 'bot loading', loadingId);
        
        // Create form data
        const formData = new FormData();
        formData.append('question', question);
        
        // Add file if present
        if (fileAttachment && fileAttachment.files.length > 0) {
            formData.append('file', fileAttachment.files[0]);
            
            // Clear file preview
            if (filePreview) {
                filePreview.innerHTML = '';
            }
            fileAttachment.value = '';
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
                addMessage(data.answer || "No response received", 'bot');
                
                // Save to session history
                saveToHistory(question, data.answer);
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
    function addMessage(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        if (id) messageElement.id = id;
        
        // Process code blocks if it's a bot message
        if (type === 'bot' || type === 'bot loading') {
            // Code block detection for ```code``` blocks
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
                
                // Use clipboard API to copy text
                navigator.clipboard.writeText(code).then(() => {
                    // Show feedback
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    this.style.backgroundColor = 'rgba(75, 181, 67, 0.4)';
                    
                    // Reset button after 2 seconds
                    setTimeout(() => {
                        this.textContent = originalText;
                        this.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                    }, 2000);
                });
            });
        });
    }, 100);
}

// Save conversation to session history
function saveToHistory(question, answer) {
    let history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    history.push({
        timestamp: new Date().toISOString(),
        question: question,
        answer: answer
    });
    localStorage.setItem('chatHistory', JSON.stringify(history));
}

// Check if we need to scroll to the bottom
chatBox.appendChild(messageElement);
chatBox.scrollTop = chatBox.scrollHeight;
    }
});
""")

# Function to extract just the answer from a verbose response
def extract_clean_answer(text):
    """Extract just the answer from a verbose response, handling multiple content types"""
    
    # Check if it's likely a numeric answer question
    numeric_indicators = ['calculate', 'sum', 'total', 'count', 'how many', 'average', 'percentage']
    is_likely_numeric = any(indicator in text.lower() for indicator in numeric_indicators)
    
    if is_likely_numeric:
        # Try to find patterns like "The answer is X" or "Result: X"
        patterns = [
            r'answer[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'result[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'value[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'total[:\s]+([0-9]+(?:\.[0-9]+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"The answer is {match.group(1)}"
    
    # For non-numeric answers or if numeric pattern not found,
    # try to extract the most relevant sentence
    sentences = text.split('.')
    for starter in ['The answer is', 'Therefore', 'In conclusion', 'Hence', 'So']:
        for sentence in sentences:
            if starter.lower() in sentence.lower():
                # Return this sentence and the next one if it exists
                idx = sentences.index(sentence)
                if idx < len(sentences) - 1:
                    return f"{sentence.strip()}.{sentences[idx+1].strip()}"
                return f"{sentence.strip()}."
    
    # If no pattern matched, return condensed text (first and last sentences)
    if len(sentences) > 2:
        return f"{sentences[0].strip()}. ... {sentences[-1].strip()}"
    return text.strip()

# Set up template directory
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Create HTML template if it doesn't exist
index_path = TEMPLATES_DIR / "index.html"
if not index_path.exists():
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vicky - Data Science Assistant</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>Vicky</h1>
                    <p class="subtitle">Your Data Science & Graded Assignment Assistant</p>
                </div>
            </div>
            <div class="header-buttons">
                <button class="header-button" id="clearChat">
                    <i class="fas fa-broom"></i> Clear Chat
                </button>
            </div>
        </header>

        <div class="main-section">
            <div class="chat-container">
                <div id="chatBox" class="chat-box">
                    <div class="message bot-message">
                        Hi there! I'm Vicky, your data science assistant. How can I help you today?
                    </div>
                </div>
                <div class="input-area">
                    <form id="questionForm" class="input-form" onsubmit="sendQuestionWithFile(event)">
                        <input type="text" id="questionInput" class="question-input" placeholder="Ask me anything about data science or your assignments..." autocomplete="off">
                        <div class="file-attach">
                            <label for="fileAttachment" class="file-button">
                                <i class="fas fa-paperclip"></i>
                            </label>
                            <input type="file" name="file" id="fileAttachment" accept=".csv,.xlsx,.txt,.py,.ipynb,.pdf,.json,.r">
                        </div>
                        <button type="submit" class="send-button">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </form>
                    <div id="filePreview" class="file-preview-area"></div>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="sidebar-header">Assignment Questions</div>
                <div class="category-container">
                    <div class="category-tab active" data-category="GA1">GA1</div>
                    <div class="category-tab" data-category="GA2">GA2</div>
                    <div class="category-tab" data-category="GA3">GA3</div>
                    <div class="category-tab" data-category="GA4">GA4</div>
                    <div class="category-tab" data-category="GA5">GA5</div>
                    <div class="category-tab" data-category="Other">Other</div>
                </div>
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search questions...">
                </div>
                <div id="preloadedQuestions" class="preloaded-questions">
                    <!-- Questions will be loaded here -->
                </div>
            </div>
        </div>
        
        <div class="file-upload-section">
            <div class="file-upload-header">
                <i class="fas fa-file-upload"></i>
                <span>Upload Supporting Documents</span>
            </div>
            <div class="file-upload-content">
                <form action="/upload" method="post" enctype="multipart/form-data" class="file-input-container">
                    <input type="file" name="file" class="file-input">
                    <button type="submit" class="upload-button">Upload</button>
                </form>
                <div class="uploaded-files">
                    <h4>Your Files</h4>
                    <ul id="uploadedFilesList">
                        <!-- Files will be loaded here -->
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        <div class="status-indicator">
            <div class="status-dot"></div>
            <span>Connected to Vicky</span>
        </div>
        <div>v2.0.0</div>
    </div>

    <script src="/static/js/main.js"></script>
    <script>
        // Load existing files on page load
        fetch('/files')
            .then(response => response.json())
            .then(files => {
                const filesList = document.getElementById('uploadedFilesList');
                filesList.innerHTML = '';
                
                if (files.length === 0) {
                    filesList.innerHTML = '<li>No files uploaded yet</li>';
                    return;
                }
                
                files.forEach(file => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        ${file}
                        <div class="file-actions">
                            <a href="/files/${file}" target="_blank">View</a>
                            <a href="/download/${file}" download>Download</a>
                            <a href="#" class="delete-btn" data-file="${file}">Delete</a>
                        </div>
                    `;
                    filesList.appendChild(li);
                });
                
                // Add delete functionality
                document.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const file = this.dataset.file;
                        if (confirm(`Are you sure you want to delete ${file}?`)) {
                            fetch(`/delete/${file}`, {method: 'DELETE'})
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        this.parentNode.parentNode.remove();
                                    } else {
                                        alert('Failed to delete file');
                                    }
                                });
                        }
                    });
                });
            });

        // Clear chat functionality
        document.getElementById('clearChat').addEventListener('click', function() {
            if (confirm('Are you sure you want to clear the chat?')) {
                const chatBox = document.getElementById('chatBox');
                chatBox.innerHTML = '<div class="message bot-message">Chat cleared. How can I help you?</div>';
            }
        });
    </script>
</body>
</html>
""")
# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ask_with_file")
async def ask_question_with_file(
    question: str = Form(...),
    file: UploadFile = File(None)
):
    """Handle questions with optional file attachments"""
    file_content = None
    file_path = None
    
    try:
        # Process file if uploaded
        if file and file.filename:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
            file_path = UPLOADS_DIR / unique_filename
            
            # Save uploaded file
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Read file content for context
            with open(file_path, "rb") as f:
                file_content = f.read().decode("utf-8", errors="ignore")
                
            logger.info(f"File uploaded: {file_path}")
            
        # Prepare question with file content if available
        if file_content:
            enhanced_question = f"{question}\n\nFile content:\n{file_content[:5000]}"
            if len(file_content) > 5000:
                enhanced_question += "... [content truncated]"
        else:
            enhanced_question = question
        
        # Get answer from Vicky
        answer = answer_question(enhanced_question)
        
        # Clean and format the answer
        cleaned_answer = extract_clean_answer(answer)
        
        return {"success": True, "answer": cleaned_answer}
    
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the server"""
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOADS_DIR / unique_filename
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logger.info(f"File uploaded: {file_path}")
        return RedirectResponse(url="/", status_code=303)
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/files")
async def list_files():
    """List all uploaded files"""
    try:
        files = [f.name for f in UPLOADS_DIR.iterdir() if f.is_file()]
        return files
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return []

@app.get("/files/{filename}")
async def get_file(filename: str):
    """Get a specific file"""
    file_path = UPLOADS_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a specific file"""
    file_path = UPLOADS_DIR / filename
    if file_path.exists():
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type="application/octet-stream"
        )
    raise HTTPException(status_code=404, detail="File not found")

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    """Delete a specific file"""
    try:
        file_path = UPLOADS_DIR / filename
        if file_path.exists():
            os.remove(file_path)
            return {"success": True}
        return {"success": False, "error": "File not found"}
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return {"success": False, "error": str(e)}

# Run the app
if __name__ == "__main__":
    uvicorn.run("vicky_main:app", host="0.0.0.0", port=8000, reload=True)