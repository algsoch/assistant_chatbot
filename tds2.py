import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
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
STATIC_CSS_DIR = STATIC_DIR / "css"
STATIC_JS_DIR = STATIC_DIR / "js"
UPLOADS_DIR = Path("uploads")

for directory in [TEMPLATES_DIR, STATIC_DIR, STATIC_CSS_DIR, STATIC_JS_DIR, UPLOADS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Create vickys.json if it doesn't exist
vickys_json_path = STATIC_DIR / "vickys.json"
if not vickys_json_path.exists():
    # Create a sample version with the provided example
    sample_data = [
        {
            "file": "E://data science tool//GA5//first.py",
            "question": "You need to clean this Excel data and calculate the total margin for all transactions that satisfy the following criteria..."
        },
        # Add more items as needed
    ]
    with open(vickys_json_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2)
    logger.info(f"Created sample vickys.json at {vickys_json_path}")

# Create the external CSS file
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

/* Rest of your CSS here */

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
    margin-right: 2px;
}
""")

# Create external JavaScript file
js_file_path = STATIC_JS_DIR / "main.js"
if not js_file_path.exists():
    with open(js_file_path, "w", encoding="utf-8") as f:
        f.write("""
document.addEventListener('DOMContentLoaded', function() {
    // Fetch questions from vickys.json
    fetch('/static/vickys.json')
        .then(response => response.json())
        .then(data => {
            // Process and categorize questions
            const questions = processQuestionsData(data);
            
            // Initialize with GA1 questions
            displayPreloadedQuestions('GA1', questions);
            
            // Handle category switching
            const categoryTabs = document.querySelectorAll('.category-tab');
            categoryTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    categoryTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Display questions for the selected category
                    displayPreloadedQuestions(this.dataset.category, questions);
                });
            });
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            // Fall back to default questions
            displayDefaultQuestions();
        });

    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    
    // Function to process questions from JSON
    function processQuestionsData(data) {
        const questions = [];
        
        data.forEach((item, index) => {
            if (item.file && item.question) {
                // Extract the category (GA1, GA2, etc.) from the file path
                const match = item.file.match(/GA(\d+)/i);
                const category = match ? `GA${match[1]}` : 'Other';
                
                // Create a shortened version of the question for display
                const shortText = item.question.split('.')[0];
                const displayText = shortText.length > 80 
                    ? shortText.substring(0, 80) + '...' 
                    : shortText;
                
                questions.push({
                    id: `question-${index}`,
                    category: category,
                    text: displayText,
                    fullText: item.question,
                    file: item.file
                });
            }
        });
        
        return questions;
    }
    
    // Display questions for a category
    function displayPreloadedQuestions(category, questions) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const filteredQuestions = questions.filter(q => q.category === category);
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText;
            questionItem.dataset.file = question.file;
            questionItem.addEventListener('click', () => {
                // Set the full question or a simplified version
                questionInput.value = question.text;
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No questions available for this category</div>';
        }
    }
    
    // Fall back to default questions if JSON loading fails
    function displayDefaultQuestions() {
        const defaultQuestions = [
            // GA1 Questions
            {"id": "ga1-1", "text": "What is the output of code -s?", "category": "GA1"},
            {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
            // More default questions can be added here
        ];
        
        const categoryTabs = document.querySelectorAll('.category-tab');
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                categoryTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Display default questions
                const category = this.dataset.category;
                const filtered = defaultQuestions.filter(q => q.category === category);
                
                preloadedQuestionsContainer.innerHTML = '';
                filtered.forEach(q => {
                    const div = document.createElement('div');
                    div.className = 'question-item';
                    div.textContent = q.text;
                    div.addEventListener('click', () => {
                        questionInput.value = q.text;
                        questionForm.dispatchEvent(new Event('submit'));
                    });
                    preloadedQuestionsContainer.appendChild(div);
                });
            });
        });
        
        // Initialize with GA1 questions
        categoryTabs[0].click();
    }

    // Handle sending messages
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
                addMessage(data.answer || "No response received", 'bot');
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
});
""")

# Create the template files (index.html, files.html, api_docs.html)
index_html_path = TEMPLATES_DIR / "index.html"
if not index_html_path.exists():
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vicky - Advanced Data Science Assistant</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>Vicky - Data Science Assistant</h1>
                    <div class="subtitle">Full support for all Graded Assignments (GA1-GA5)</div>
                </div>
            </div>
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
                        <strong>Welcome to Vicky's Data Science Assistant!</strong><br><br>
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
                <div class="category-container">
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

    <script src="/static/js/main.js"></script>
</body>
</html>""")

files_html_path = TEMPLATES_DIR / "files.html"
if not files_html_path.exists():
    with open(files_html_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Repository - Vicky</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
    <style>
        .files-table {
            width: 100%;
            background-color: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .files-table th, .files-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .files-table th {
            background-color: var(--primary-color);
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
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: var(--border-radius);
            margin-top: 20px;
            transition: var(--transition);
        }
        .back-button:hover {
            background-color: var(--primary-light);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>File Repository</h1>
                    <div class="subtitle">Manage your uploaded files</div>
                </div>
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
                    <th>Actions</th>
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
                    <td>
                        <a href="#" class="use-file" data-id="{{ file.id }}">Use</a>
                        <a href="#" class="delete-file" data-id="{{ file.id }}">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No files have been uploaded yet.</p>
        {% endif %}
        
        <a href="/" class="back-button">
            <i class="fas fa-arrow-left"></i> Back to Chat
        </a>
    </div>
    
    <script>
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('delete-file')) {
                e.preventDefault();
                if (confirm('Are you sure you want to delete this file?')) {
                    const fileId = e.target.dataset.id;
                    fetch(`/delete-file/${fileId}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                location.reload();
                            }
                        });
                }
            }
            if (e.target.classList.contains('use-file')) {
                e.preventDefault();
                const fileId = e.target.dataset.id;
                window.location.href = `/?file=${fileId}`;
            }
        });
    </script>
</body>
</html>""")

api_docs_html_path = TEMPLATES_DIR / "api_docs.html"
if not api_docs_html_path.exists():
    with open(api_docs_html_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - Vicky</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
    <style>
        .api-section {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 20px;
            margin-bottom: 20px;
        }
        .endpoint {
            margin-bottom: 30px;
        }
        .endpoint h3 {
            color: var(--primary-color);
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }
        .endpoint-path {
            background-color: #2d2d2d;
            color: white;
            padding: 8px 15px;
            border-radius: 4px;
            font-family: monospace;
            display: inline-block;
        }
        .http-method {
            background-color: var(--secondary-color);
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-right: 8px;
        }
        pre {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .param-name {
            font-weight: bold;
            color: var(--primary-color);
        }
        .back-button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: var(--border-radius);
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>API Documentation</h1>
                    <div class="subtitle">Integrate with Vicky's Data Science Assistant</div>
                </div>
            </div>
        </header>
        
        <div class="api-section">
            <h2>Standard Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="http-method">POST</span> /ask_with_file</h3>
                <p>Ask a question with an optional file attachment</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><span class="param-name">question</span> (required) - The question text</li>
                    <li><span class="param-name">file</span> (optional) - A file to use with the question</li>
                </ul>
                
                <h4>Example</h4>
                <pre>
curl -X POST "http://localhost:8000/ask_with_file" \\
  -F "question=Extract data from this ZIP file" \\
  -F "file=@/path/to/file.zip"</pre>
                
                <h4>Response</h4>
                <pre>
{
  "success": true,
  "answer": "The answer from extract.csv is 42",
  "question": "Extract data from this ZIP file"
}</pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="http-method">POST</span> /api/</h3>
                <p>API endpoint with standard response format for submission</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><span class="param-name">question</span> (required) - The question text</li>
                    <li><span class="param-name">file</span> (optional) - A file to use with the question</li>
                </ul>
                
                <h4>Vercel Deployment Example</h4>
                <pre>
curl -X POST "https://your-app.vercel.app/api/" \\
  -H "Content-Type: multipart/form-data" \\
  -F "question=Download and unzip file abcd.zip which has a single extract.csv file inside. What is the value in the \"answer\" column of the CSV file?" \\
  -F "file=@abcd.zip"</pre>
                
                <h4>Standard Response Format</h4>
                <pre>
{
  "answer": "1234567890"
}</pre>
            </div>
        </div>
        
        <div class="api-section">
            <h2>Specialized Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="http-method">POST</span> /api/process</h3>
                <p>Process a question with specialized handling based on question type</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><span class="param-name">question</span> (required) - The question text</li>
                    <li><span class="param-name">file</span> (required) - The file to process</li>
                    <li><span class="param-name">question_type</span> (optional) - Hint about question type</li>
                </ul>
                
                <h4>Example</h4>
                <pre>
# For README.md (Question 3)
curl -X POST "http://localhost:8000/api/process" \\
  -F "question=What is the output of npx prettier on this README file?" \\
  -F "file=@/path/to/README.md" \\
  -F "question_type=npx_readme"</pre>
            </div>
        </div>
        
        <a href="/" class="back-button">
            <i class="fas fa-arrow-left"></i> Back to Chat
        </a>
    </div>
</body>
</html>""")

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Rest of your code with FastAPI routes
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

# Add API endpoint with standard response format
@app.post("/api/")
async def api_standard_endpoint(
    request: Request,
    question: str = Form(...),
    file: UploadFile = File(None)
):
    """API endpoint that returns answers in a standard format for assignment submission"""
    try:
        # Process file if provided
        file_context = ""
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Add file context
            file_ext = os.path.splitext(file.filename)[1].lower()
            file_context = f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        full_question = question + file_context
        answer = answer_question(full_question)
        
        # Clean the answer to keep only the essential output
        clean_answer = extract_clean_answer(answer)
        
        # Return in the standard format
        return {
            "answer": clean_answer
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {
            "answer": f"Error: {str(e)}"
        }

def extract_clean_answer(text):
    """Extract just the answer from a verbose response, handling multiple content types"""
    
    # Check if it's likely a numeric answer question
    numeric_indicators = ['calculate', 'sum', 'total', 'count', 'how many', 'average', 'percentage', 'margin']
    is_likely_numeric = any(indicator in text.lower() for indicator in numeric_indicators)
    
    if is_likely_numeric:
        # Try to find patterns like "The answer is X" or "Result: X"
        patterns = [
            r'answer[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'result[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'value[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'total[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'is\s+([0-9]+(?:\.[0-9]+)?)',
            r'equals\s+([0-9]+(?:\.[0-9]+)?)',
            r'[\s\.]([0-9]+(?:\.[0-9]+)?)$'  # End of response number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Look for numbers that stand alone
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
        if numbers:
            # Return the last number as that's often the final result
            return numbers[-1]
    
    # For non-numeric content, try to extract clear answers with patterns
    answer_patterns = [
        r'answer is[:\s]+(.+?)(?:\.|$)',
        r'result is[:\s]+(.+?)(?:\.|$)',
        r'output is[:\s]+(.+?)(?:\.|$)',
        r'content is[:\s]+(.+?)(?:\.|$)'
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            answer = match.group(1).strip()
            # If the answer isn't too long, return it
            if len(answer) < 500:
                return answer
    
    # Handle code blocks - if there's a single code block, it might be the answer
    code_blocks = re.findall(r'```(?:\w+)?\n([\s\S]+?)\n```', text)
    if len(code_blocks) == 1 and len(code_blocks[0]) < 1000:
        return code_blocks[0]
    
    # Special case for file paths/URLs
    url_match = re.search(r'https?://\S+', text)
    if url_match:
        return url_match.group(0)
    
    path_match = re.search(r'(?:file|path)[:\s]+([\w\\/.~_-]+\.\w+)', text, re.IGNORECASE)
    if path_match:
        return path_match.group(1)
    
    # For markdown or text content, try to clean it up
    cleaned_text = re.sub(r'(?i)the answer is|here\'s the|the result is|output:|result:', '', text)
    cleaned_text = re.sub(r'[#*`]', '', cleaned_text)  # Remove markdown symbols
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)   # Normalize whitespace
    
    # If it's still too long, take the first paragraph or sentence
    if len(cleaned_text) > 500:
        # Try to get first paragraph
        paragraphs = cleaned_text.split('\n\n')
        if paragraphs and paragraphs[0].strip():
            cleaned_text = paragraphs[0].strip()
        else:
            # Or first sentence
            sentences = cleaned_text.split('.')
            if sentences and sentences[0].strip():
                cleaned_text = sentences[0].strip() + '.'
            else:
                # Last resort, just truncate
                cleaned_text = cleaned_text[:497] + "..."
    
    return cleaned_text.strip()
def load_vickys_json():
    """Load question data from vickys.json or create a default one if it doesn't exist"""
    vickys_json_path = STATIC_DIR / "vickys.json"
    
    if not vickys_json_path.exists():
        # Create a sample version with the provided example
        sample_data = []
        
        # Add GA5 questions
        sample_data.append({
            "file": "E://data science tool//GA5//first.py",
            "question": "You need to clean this Excel data and calculate the total margin for all transactions that satisfy criteria..."
        })
        
        # Add GA1-GA4 questions (examples)
        for ga_num in range(1, 5):
            for q_num in range(1, 4):  # Add 3 sample questions per GA
                sample_data.append({
                    "file": f"E://data science tool//GA{ga_num}//question{q_num}.py",
                    "question": f"Sample question {q_num} for GA{ga_num}..."
                })
        
        with open(vickys_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2)
        logger.info(f"Created sample vickys.json at {vickys_json_path}")
    
    # Now load the data
    try:
        with open(vickys_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading vickys.json: {e}")
        return []
import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
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
STATIC_CSS_DIR = STATIC_DIR / "css"
STATIC_JS_DIR = STATIC_DIR / "js"
UPLOADS_DIR = Path("uploads")

for directory in [TEMPLATES_DIR, STATIC_DIR, STATIC_CSS_DIR, STATIC_JS_DIR, UPLOADS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Create vickys.json if it doesn't exist
vickys_json_path = STATIC_DIR / "vickys.json"
if not vickys_json_path.exists():
    # Create a sample version with the provided example
    sample_data = [
        {
            "file": "E://data science tool//GA5//first.py",
            "question": "You need to clean this Excel data and calculate the total margin for all transactions that satisfy the following criteria..."
        },
        # Add more items as needed
    ]
    with open(vickys_json_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2)
    logger.info(f"Created sample vickys.json at {vickys_json_path}")

# Create the external CSS file
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

/* Rest of your CSS here */

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
    margin-right: 2px;
}
""")

# Create external JavaScript file
js_file_path = STATIC_JS_DIR / "main.js"
if not js_file_path.exists():
    with open(js_file_path, "w", encoding="utf-8") as f:
        f.write("""
document.addEventListener('DOMContentLoaded', function() {
    // Fetch questions from vickys.json
    fetch('/static/vickys.json')
        .then(response => response.json())
        .then(data => {
            // Process and categorize questions
            const questions = processQuestionsData(data);
            
            // Initialize with GA1 questions
            displayPreloadedQuestions('GA1', questions);
            
            // Handle category switching
            const categoryTabs = document.querySelectorAll('.category-tab');
            categoryTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    categoryTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Display questions for the selected category
                    displayPreloadedQuestions(this.dataset.category, questions);
                });
            });
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            // Fall back to default questions
            displayDefaultQuestions();
        });

    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    
    // Function to process questions from JSON
    function processQuestionsData(data) {
        const questions = [];
        
        data.forEach((item, index) => {
            if (item.file && item.question) {
                // Extract the category (GA1, GA2, etc.) from the file path
                const match = item.file.match(/GA(\d+)/i);
                const category = match ? `GA${match[1]}` : 'Other';
                
                // Create a shortened version of the question for display
                const shortText = item.question.split('.')[0];
                const displayText = shortText.length > 80 
                    ? shortText.substring(0, 80) + '...' 
                    : shortText;
                
                questions.push({
                    id: `question-${index}`,
                    category: category,
                    text: displayText,
                    fullText: item.question,
                    file: item.file
                });
            }
        });
        
        return questions;
    }
    
    // Display questions for a category
    function displayPreloadedQuestions(category, questions) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const filteredQuestions = questions.filter(q => q.category === category);
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText;
            questionItem.dataset.file = question.file;
            questionItem.addEventListener('click', () => {
                // Set the full question or a simplified version
                questionInput.value = question.text;
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No questions available for this category</div>';
        }
    }
    
    // Fall back to default questions if JSON loading fails
    function displayDefaultQuestions() {
        const defaultQuestions = [
            // GA1 Questions
            {"id": "ga1-1", "text": "What is the output of code -s?", "category": "GA1"},
            {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
            // More default questions can be added here
        ];
        
        const categoryTabs = document.querySelectorAll('.category-tab');
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                categoryTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Display default questions
                const category = this.dataset.category;
                const filtered = defaultQuestions.filter(q => q.category === category);
                
                preloadedQuestionsContainer.innerHTML = '';
                filtered.forEach(q => {
                    const div = document.createElement('div');
                    div.className = 'question-item';
                    div.textContent = q.text;
                    div.addEventListener('click', () => {
                        questionInput.value = q.text;
                        questionForm.dispatchEvent(new Event('submit'));
                    });
                    preloadedQuestionsContainer.appendChild(div);
                });
            });
        });
        
        // Initialize with GA1 questions
        categoryTabs[0].click();
    }

    // Handle sending messages
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
                addMessage(data.answer || "No response received", 'bot');
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
});
""")

# Create the template files (index.html, files.html, api_docs.html)
index_html_path = TEMPLATES_DIR / "index.html"
if not index_html_path.exists():
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vicky - Advanced Data Science Assistant</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>Vicky - Data Science Assistant</h1>
                    <div class="subtitle">Full support for all Graded Assignments (GA1-GA5)</div>
                </div>
            </div>
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
                        <strong>Welcome to Vicky's Data Science Assistant!</strong><br><br>
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
                <div class="category-container">
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

    <script src="/static/js/main.js"></script>
</body>
</html>""")

files_html_path = TEMPLATES_DIR / "files.html"
if not files_html_path.exists():
    with open(files_html_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Repository - Vicky</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
    <style>
        .files-table {
            width: 100%;
            background-color: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .files-table th, .files-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .files-table th {
            background-color: var(--primary-color);
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
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: var(--border-radius);
            margin-top: 20px;
            transition: var(--transition);
        }
        .back-button:hover {
            background-color: var(--primary-light);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>File Repository</h1>
                    <div class="subtitle">Manage your uploaded files</div>
                </div>
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
                    <th>Actions</th>
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
                    <td>
                        <a href="#" class="use-file" data-id="{{ file.id }}">Use</a>
                        <a href="#" class="delete-file" data-id="{{ file.id }}">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No files have been uploaded yet.</p>
        {% endif %}
        
        <a href="/" class="back-button">
            <i class="fas fa-arrow-left"></i> Back to Chat
        </a>
    </div>
    
    <script>
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('delete-file')) {
                e.preventDefault();
                if (confirm('Are you sure you want to delete this file?')) {
                    const fileId = e.target.dataset.id;
                    fetch(`/delete-file/${fileId}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                location.reload();
                            }
                        });
                }
            }
            if (e.target.classList.contains('use-file')) {
                e.preventDefault();
                const fileId = e.target.dataset.id;
                window.location.href = `/?file=${fileId}`;
            }
        });
    </script>
</body>
</html>""")

api_docs_html_path = TEMPLATES_DIR / "api_docs.html"
if not api_docs_html_path.exists():
    with open(api_docs_html_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - Vicky</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
    <style>
        .api-section {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 20px;
            margin-bottom: 20px;
        }
        .endpoint {
            margin-bottom: 30px;
        }
        .endpoint h3 {
            color: var(--primary-color);
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }
        .endpoint-path {
            background-color: #2d2d2d;
            color: white;
            padding: 8px 15px;
            border-radius: 4px;
            font-family: monospace;
            display: inline-block;
        }
        .http-method {
            background-color: var(--secondary-color);
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-right: 8px;
        }
        pre {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .param-name {
            font-weight: bold;
            color: var(--primary-color);
        }
        .back-button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: var(--border-radius);
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="vicky-header">
                <div class="vicky-logo">V</div>
                <div class="vicky-info">
                    <h1>API Documentation</h1>
                    <div class="subtitle">Integrate with Vicky's Data Science Assistant</div>
                </div>
            </div>
        </header>
        
        <div class="api-section">
            <h2>Standard Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="http-method">POST</span> /ask_with_file</h3>
                <p>Ask a question with an optional file attachment</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><span class="param-name">question</span> (required) - The question text</li>
                    <li><span class="param-name">file</span> (optional) - A file to use with the question</li>
                </ul>
                
                <h4>Example</h4>
                <pre>
curl -X POST "http://localhost:8000/ask_with_file" \\
  -F "question=Extract data from this ZIP file" \\
  -F "file=@/path/to/file.zip"</pre>
                
                <h4>Response</h4>
                <pre>
{
  "success": true,
  "answer": "The answer from extract.csv is 42",
  "question": "Extract data from this ZIP file"
}</pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="http-method">POST</span> /api/</h3>
                <p>API endpoint with standard response format for submission</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><span class="param-name">question</span> (required) - The question text</li>
                    <li><span class="param-name">file</span> (optional) - A file to use with the question</li>
                </ul>
                
                <h4>Vercel Deployment Example</h4>
                <pre>
curl -X POST "https://your-app.vercel.app/api/" \\
  -H "Content-Type: multipart/form-data" \\
  -F "question=Download and unzip file abcd.zip which has a single extract.csv file inside. What is the value in the \"answer\" column of the CSV file?" \\
  -F "file=@abcd.zip"</pre>
                
                <h4>Standard Response Format</h4>
                <pre>
{
  "answer": "1234567890"
}</pre>
            </div>
        </div>
        
        <div class="api-section">
            <h2>Specialized Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="http-method">POST</span> /api/process</h3>
                <p>Process a question with specialized handling based on question type</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><span class="param-name">question</span> (required) - The question text</li>
                    <li><span class="param-name">file</span> (required) - The file to process</li>
                    <li><span class="param-name">question_type</span> (optional) - Hint about question type</li>
                </ul>
                
                <h4>Example</h4>
                <pre>
# For README.md (Question 3)
curl -X POST "http://localhost:8000/api/process" \\
  -F "question=What is the output of npx prettier on this README file?" \\
  -F "file=@/path/to/README.md" \\
  -F "question_type=npx_readme"</pre>
            </div>
        </div>
        
        <a href="/" class="back-button">
            <i class="fas fa-arrow-left"></i> Back to Chat
        </a>
    </div>
</body>
</html>""")

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Rest of your code with FastAPI routes
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

# Add API endpoint with standard response format
@app.post("/api/")
async def api_standard_endpoint(
    request: Request,
    question: str = Form(...),
    file: UploadFile = File(None)
):
    """API endpoint that returns answers in a standard format for assignment submission"""
    try:
        # Process file if provided
        file_context = ""
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Add file context
            file_ext = os.path.splitext(file.filename)[1].lower()
            file_context = f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        full_question = question + file_context
        answer = answer_question(full_question)
        
        # Clean the answer to keep only the essential output
        clean_answer = extract_clean_answer(answer)
        
        # Return in the standard format
        return {
            "answer": clean_answer
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {
            "answer": f"Error: {str(e)}"
        }

def extract_clean_answer(text):
    """Extract just the answer from a verbose response"""
    # Try to find patterns like "The answer is X" or "Result: X"
    patterns = [
        r'answer[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
        r'result[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
        r'value[s]?[:\s]+([0-9]+(?:\.[0-9]+)?)',
        r'total[:\s]+([0-9]+(?:\.[0-9]+)?)',
        r'is\s+([0-9]+(?:\.[0-9]+)?)',
        r'equals\s+([0-9]+(?:\.[0-9]+)?)',
        r'[\s\.]([0-9]+(?:\.[0-9]+)?)$'  # End of response number
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # If no pattern matches, try to extract anything that looks like a number result
    # Look for numbers that stand alone
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
    if numbers:
        # Return the last number as that's often the final result
        return numbers[-1]
    
    # If still no match, return the original text with reasonable trimming
    # Remove markdown formatting and limit length
    cleaned_text = re.sub(r'[#*`]', '', text)  # Remove markdown symbols
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
    
    if len(cleaned_text) > 100:
        cleaned_text = cleaned_text[:97] + "..."
        
    return cleaned_text.strip()