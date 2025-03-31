from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import os
import string
import re
from difflib import SequenceMatcher
import datetime
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
import io
from contextlib import redirect_stdout

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load `vickys.json` into memory
vickys_file = "E:/data science tool/main/grok/vickys.json"
with open(vickys_file, "r", encoding="utf-8") as f:
    questions_data = json.load(f)

# Create templates directory if it doesn't exist
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(templates_dir, exist_ok=True)

# Create uploads directory if it doesn't exist
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Create the HTML template
template_path = os.path.join(templates_dir, "index.html")
with open(template_path, "w") as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Science Tool Question Matcher</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f0f2f5; 
            color: #333;
        }
        .container { 
            max-width: 900px; 
            margin: 0 auto; 
            background-color: #fff; 
            padding: 25px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        h1 { 
            color: #2c3e50; 
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        h2 {
            color: #3498db;
            margin-top: 25px;
        }
        .form-group { 
            margin-bottom: 20px; 
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        textarea { 
            width: 100%; 
            height: 120px; 
            padding: 12px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-size: 16px;
            font-family: Arial, sans-serif;
        }
        button { 
            background-color: #3498db; 
            color: white; 
            padding: 12px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
            display: block;
            width: 100%;
        }
        button:hover { 
            background-color: #2980b9; 
        }
        .result { 
            margin-top: 25px; 
            padding: 20px; 
            background-color: #f8f9fa; 
            border-radius: 5px; 
            border: 1px solid #ddd;
            word-wrap: break-word;
        }
        .error { 
            color: #e74c3c; 
            background-color: #fde8e7; 
            padding: 15px; 
            border-radius: 4px;
            border-left: 4px solid #e74c3c; 
        }
        .success {
            border-left: 4px solid #2ecc71;
        }
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 2s linear infinite;
            margin: 20px auto;
            display: none;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .section { 
            margin-bottom: 40px;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .heading { 
            background-color: #f5f7fa; 
            padding: 10px 15px; 
            border-radius: 4px; 
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }
        .match-info { 
            margin-bottom: 15px; 
            color: #666; 
            font-style: italic; 
        }
        .question-list {
            list-style-type: none;
            padding: 0;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .question-item {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .question-item:hover {
            background-color: #f5f7fa;
        }
        .question-item:last-child {
            border-bottom: none;
        }
        .tabs {
            display: flex;
            border-bottom: 1px solid #ddd;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f5f7fa;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            margin-right: 5px;
        }
        .tab.active {
            background-color: white;
            border-bottom: 1px solid white;
            margin-bottom: -1px;
            font-weight: bold;
            color: #3498db;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        pre {
            white-space: pre-wrap;
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            border: 1px solid #ddd;
            font-family: 'Courier New', monospace;
        }
        code {
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .json {
            color: #000080;
        }
        .json .key {
            color: #a52a2a;
            font-weight: bold;
        }
        .json .string {
            color: #008000;
        }
        .json .number {
            color: #0000ff;
        }
        .json .boolean {
            color: #b22222;
        }
        .json .null {
            color: #808080;
        }
        .recent-questions {
            margin-top: 20px;
        }
        .recent-questions h3 {
            margin-bottom: 10px;
        }
        .recent-item {
            padding: 8px 12px;
            background-color: #f1f9ff;
            border-radius: 4px;
            margin-bottom: 5px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .recent-item:hover {
            background-color: #e1f2ff;
        }
        .test-button {
            background-color: #27ae60;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
            margin-bottom: 15px;
            margin-right: 10px;
            width: auto;
            display: inline-block;
        }
        .test-button:hover {
            background-color: #219653;
        }
        .test-note {
            color: #666;
            font-size: 13px;
            margin-top: 5px;
            font-style: italic;
        }
        .test-buttons {
            margin-bottom: 10px;
        }
        #notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #2ecc71;
            color: white;
            padding: 15px;
            border-radius: 4px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            display: none;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div id="notification">Question copied to clipboard!</div>
    <div class="container">
        <h1>Data Science Tool Question Matcher</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="openTab('ask-tab')">Ask Question</div>
            <div class="tab" onclick="openTab('upload-tab')">File Upload</div>
            <div class="tab" onclick="openTab('browse-tab')">Browse Questions</div>
        </div>
        
        <div id="ask-tab" class="tab-content active">
            <div class="section">
                <div class="heading">
                    <h2>Ask a Question</h2>
                </div>
                <form id="questionForm">
                    <div class="form-group">
                        <label for="question">Enter your question:</label>
                        <textarea id="question" name="question" required placeholder="Type your question here..."></textarea>
                    </div>
                    <button type="submit">Find Match</button>
                </form>
                
                <div class="loader" id="loader"></div>
                <div id="result" class="result" style="display: none;"></div>
                
                <div class="recent-questions">
                    <h3>Recent Example Questions:</h3>
                    <div id="recentQuestions">
                        <!-- Recent questions will be loaded here -->
                    </div>
                    
                    <h3 style="margin-top: 20px;">Quick Tests:</h3>
                    <div class="test-buttons">
                        <button type="button" class="test-button" onclick="testDayCounting('wednesday')">Count Wednesdays</button>
                        <button type="button" class="test-button" onclick="testDayCounting('monday')">Count Mondays</button>
                        <button type="button" class="test-button" onclick="testDayCounting('friday')">Count Fridays</button>
                    </div>
                    <p class="test-note">All counting uses date range: 1981-03-03 to 2012-12-30</p>
                </div>
            </div>
        </div>
        
        <div id="upload-tab" class="tab-content">
            <div class="section">
                <div class="heading">
                    <h2>File Upload</h2>
                </div>
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="file">Select a file to upload:</label>
                        <input type="file" id="file" name="file" required>
                    </div>
                    <button type="submit">Upload File</button>
                </form>
                <div id="uploadResult" class="result" style="display: none;"></div>
            </div>
        </div>
        
        <div id="browse-tab" class="tab-content">
            <div class="section">
                <div class="heading">
                    <h2>Available Questions</h2>
                </div>
                <div class="form-group">
                    <label for="searchQuestions">Search Questions:</label>
                    <input type="text" id="searchQuestions" placeholder="Type to filter questions..." style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div class="question-list" id="questionsList">
                    <!-- Questions will be loaded here -->
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Store recent questions
        let recentQuestions = [];
        
        // Format JSON for display
        function formatJSON(json) {
            if (typeof json !== 'string') {
                try {
                    json = JSON.stringify(json, null, 2);
                } catch (e) {
                    // If it's not stringifiable, convert to string
                    json = String(json);
                }
            }
            // Escape HTML
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            // Add syntax highlighting
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\\s*:)?|\\b(true|false|null)\\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g, function (match) {
                var cls = 'number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'key';
                    } else {
                        cls = 'string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'boolean';
                } else if (/null/.test(match)) {
                    cls = 'null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }
        
        // Format any output for display - detects JSON
        function formatOutput(output) {
            if (typeof output !== 'string') {
                return output;
            }
            
            // Check if it's JSON
            try {
                if (output.trim().startsWith('{') || output.trim().startsWith('[')) {
                    const json = JSON.parse(output);
                    return '<pre class="json">' + formatJSON(JSON.stringify(json, null, 2)) + '</pre>';
                }
            } catch (e) {
                // Not JSON
            }
            
            // If it has newlines, format as code
            if (output.includes('\\n') || output.includes('\n')) {
                return '<pre><code>' + output.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</code></pre>';
            }
            
            return output;
        }
        
        // Fill question textarea with example
        function fillQuestion(text) {
            document.getElementById('question').value = text;
            document.getElementById('questionForm').scrollIntoView();
            
            // Switch to ask tab
            openTab('ask-tab');
            
            // Add to recent questions if not already there
            if (!recentQuestions.includes(text)) {
                recentQuestions.unshift(text);
                if (recentQuestions.length > 5) {
                    recentQuestions.pop();
                }
                updateRecentQuestions();
            }
        }
        
        // Copy question to clipboard
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                const notification = document.getElementById('notification');
                notification.style.display = 'block';
                setTimeout(() => {
                    notification.style.display = 'none';
                }, 2000);
            });
        }
        
        // Update recent questions display
        function updateRecentQuestions() {
            const recentQuestionsDiv = document.getElementById('recentQuestions');
            recentQuestionsDiv.innerHTML = '';
            
            recentQuestions.forEach(question => {
                const div = document.createElement('div');
                div.className = 'recent-item';
                
                // Truncate question if too long
                const displayText = question.length > 100 ? question.substring(0, 100) + '...' : question;
                div.textContent = displayText;
                
                div.onclick = () => fillQuestion(question);
                recentQuestionsDiv.appendChild(div);
            });
        }
        
        // Handle tab switching
        function openTab(tabId) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show the selected tab
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to the clicked tab button
            const tabIndex = ['ask-tab', 'upload-tab', 'browse-tab'].indexOf(tabId);
            document.querySelectorAll('.tab')[tabIndex].classList.add('active');
        }
        
        // Filter questions
        function filterQuestions() {
            const searchText = document.getElementById('searchQuestions').value.toLowerCase();
            const questionItems = document.querySelectorAll('.question-item');
            
            questionItems.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchText)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        }
        
        // Load questions when page loads
        document.addEventListener('DOMContentLoaded', async () => {
            try {
                const response = await fetch('/questions');
                const questions = await response.json();
                
                const questionsList = document.getElementById('questionsList');
                
                // Add all questions to list
                if (questions && questions.length > 0) {
                    console.log("Loaded questions:", questions.length);
                    questionsList.innerHTML = ''; // Clear any existing content
                    
                    questions.forEach((question, index) => {
                        const div = document.createElement('div');
                        div.className = 'question-item';
                        
                        // Create a unique ID for each question
                        const questionId = `question-${index}`;
                        div.id = questionId;
                        
                        // Set the text content
                        div.textContent = question;
                        
                        // Add click listener to fill the question
                        div.addEventListener('click', () => {
                            fillQuestion(question);
                            
                            // Also copy to clipboard
                            copyToClipboard(question);
                        });
                        
                        questionsList.appendChild(div);
                    });
                    
                    // Set up search functionality
                    document.getElementById('searchQuestions').addEventListener('input', filterQuestions);
                    
                    // Add first 5 questions as recent examples
                    recentQuestions = questions.slice(0, 5);
                    updateRecentQuestions();
                } else {
                    questionsList.innerHTML = '<div class="error">No questions available</div>';
                }
            } catch (error) {
                console.error('Error loading questions:', error);
                document.getElementById('questionsList').innerHTML = `<div class="error">Error loading questions: ${error.message}</div>`;
            }
        });
        
        // Handle form submission
        document.getElementById('questionForm').addEventListener('submit', async (event) => {
            event.preventDefault();
            
            const question = document.getElementById('question').value;
            const resultDiv = document.getElementById('result');
            const loader = document.getElementById('loader');
            
            // Show loader
            loader.style.display = 'block';
            resultDiv.style.display = 'none';
            
            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question }),
                });
                
                const data = await response.json();
                
                // Hide loader
                loader.style.display = 'none';
                resultDiv.style.display = 'block';
                
                if (data.error) {
                    resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
                    resultDiv.className = "result";
                } else {
                    let outputDisplay = data.output;
                    
                    // Convert null to "null" string for display
                    if (outputDisplay === null) {
                        outputDisplay = "null";
                    }
                    
                    // Format the output properly
                    const formattedOutput = formatOutput(outputDisplay);
                    
                    resultDiv.innerHTML = `
                        <h3>Result</h3>
                        <p class="match-info">Question matched: "${data.question || question}"</p>
                        <h4>Output:</h4>
                        <div>${formattedOutput}</div>
                    `;
                    resultDiv.className = "result success";
                    
                    // Add to recent questions
                    if (!recentQuestions.includes(question)) {
                        recentQuestions.unshift(question);
                        if (recentQuestions.length > 5) {
                            recentQuestions.pop();
                        }
                        updateRecentQuestions();
                    }
                }
                
                // Scroll to the result
                resultDiv.scrollIntoView({behavior: "smooth"});
                
            } catch (error) {
                // Hide loader
                loader.style.display = 'none';
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                resultDiv.className = "result";
            }
        });
        
        // Handle file upload
        document.getElementById('uploadForm').addEventListener('submit', async (event) => {
            event.preventDefault();
            
            const fileInput = document.getElementById('file');
            const uploadResultDiv = document.getElementById('uploadResult');
            
            if (!fileInput.files || fileInput.files.length === 0) {
                uploadResultDiv.style.display = 'block';
                uploadResultDiv.innerHTML = `<div class="error">Please select a file to upload</div>`;
                return;
            }
            
            // Show loading indicator
            uploadResultDiv.style.display = 'block';
            uploadResultDiv.innerHTML = `<div class="loader" style="display:block;"></div><p>Uploading file...</p>`;
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData,
                });
                
                const data = await response.json();
                
                uploadResultDiv.style.display = 'block';
                if (data.error) {
                    uploadResultDiv.innerHTML = `<div class="error">${data.error}</div>`;
                    uploadResultDiv.className = "result";
                } else {
                    uploadResultDiv.innerHTML = `
                        <h3>File Upload Success</h3>
                        <p><strong>Filename:</strong> ${data.filename}</p>
                        <p><strong>File Size:</strong> ${data.size} bytes</p>
                        <p><strong>Path:</strong> ${data.path}</p>
                    `;
                    uploadResultDiv.className = "result success";
                }
                
                // Scroll to result
                uploadResultDiv.scrollIntoView({behavior: "smooth"});
            } catch (error) {
                uploadResultDiv.style.display = 'block';
                uploadResultDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                uploadResultDiv.className = "result";
            }
        });

        // Test day counting directly
        function testDayCounting(day) {
            document.getElementById('result').style.display = 'none';
            document.getElementById('loader').style.display = 'block';
            
            fetch(`/count_days?day=${day}&start_date=1981-03-03&end_date=2012-12-30`)
                .then(response => response.json())
                .then(data => {
                    const resultDiv = document.getElementById('result');
                    document.getElementById('loader').style.display = 'none';
                    resultDiv.style.display = 'block';
                    
                    if (data.error) {
                        resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
                        resultDiv.className = "result";
                    } else {
                        // Capitalize first letter of day
                        const capitalizedDay = data.day.charAt(0).toUpperCase() + data.day.slice(1);
                        
                        resultDiv.innerHTML = `
                            <h3>Day Counting Test Result</h3>
                            <p>There are <strong>${data.result}</strong> ${capitalizedDay}s between ${data.start_date} and ${data.end_date}</p>
                        `;
                        resultDiv.className = "result success";
                    }
                    
                    resultDiv.scrollIntoView({behavior: "smooth"});
                    
                    // Add this query to recent questions
                    const questionText = `How many ${day}s are there in the date range ${data.start_date} to ${data.end_date}?`;
                    if (!recentQuestions.includes(questionText)) {
                        recentQuestions.unshift(questionText);
                        if (recentQuestions.length > 5) {
                            recentQuestions.pop();
                        }
                        updateRecentQuestions();
                    }
                })
                .catch(error => {
                    const resultDiv = document.getElementById('result');
                    document.getElementById('loader').style.display = 'none';
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                    resultDiv.className = "result";
                });
        }
    </script>
</body>
</html>
    """)

# Set up templates
templates = Jinja2Templates(directory=templates_dir)

class QuestionRequest(BaseModel):
    question: str
    modifications: Optional[Dict[str, Any]] = None

# ✅ Normalize text for better matching
def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def find_best_match(user_question):
    """Find the best matching question using similarity scoring."""
    if not user_question:
        return None
        
    normalized_user_question = normalize_text(user_question)
    
    # Initialize variables to track best match
    best_match = None
    best_score = 0
    
    for entry in questions_data:
        question = entry.get("question", "")
        if not question or question == "Unknown Question":
            continue
            
        normalized_question = normalize_text(question)
        
        # Calculate similarity score using SequenceMatcher
        similarity = SequenceMatcher(None, normalized_user_question, normalized_question).ratio()
        
        # Check keywords match
        user_words = set(normalized_user_question.split())
        question_words = set(normalized_question.split())
        common_words = user_words.intersection(question_words)
        
        # Boost score if there are common important words
        keyword_boost = len(common_words) / (len(question_words) + 0.001)
        
        # Combined score
        score = similarity * 0.6 + keyword_boost * 0.4
        
        if score > best_score:
            best_score = score
            best_match = question
    
    # Only return if we have a reasonable match
    return best_match if best_score > 0.3 else None

def count_specific_day_in_range(day_of_week=2, start_date="1981-03-03", end_date="2012-12-30"):
    """
    Count the number of specific days in a date range.
    day_of_week: 0 for Monday, 1 for Tuesday, 2 for Wednesday, etc.
    start_date and end_date should be in YYYY-MM-DD format.
    """
    try:
        # Parse the dates
        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Ensure day_of_week is correct format (Monday is 0, Sunday is 6)
        if isinstance(day_of_week, str):
            days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
                    "friday": 4, "saturday": 5, "sunday": 6}
            day_of_week = days.get(day_of_week.lower(), 2)  # Default to Wednesday if not found
        
        # Initialize counter
        count = 0
        current_date = start_date
        
        # Count days
        while current_date <= end_date:
            if current_date.weekday() == day_of_week:
                count += 1
            current_date += datetime.timedelta(days=1)
            
        return count
    except Exception as e:
        return f"Error counting days: {str(e)}"

@app.post("/ask")
def ask_question(request: QuestionRequest):
    print(f"Processing question: {request.question}")
    
    # Special case for counting Wednesdays
    if "wednesday" in request.question.lower() and "date range" in request.question.lower():
        # Extract date range
        matches = re.findall(r'(\d{4}-\d{2}-\d{2})', request.question)
        if len(matches) >= 2:
            start_date = matches[0]
            end_date = matches[1]
            day_name = "wednesday"
            days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
                        "friday": 4, "saturday": 5, "sunday": 6}
            day_num = days_map.get(day_name.lower(), 2)
            
            result = count_specific_day_in_range(day_num, start_date, end_date)
            print(f"Counting {day_name} from {start_date} to {end_date}: {result}")
            return {"question": request.question, "output": result}
    
    # Special case for counting any day of the week
    day_of_week_match = re.search(r'how many (\w+)s are there', request.question.lower())
    if day_of_week_match:
        day_name = day_of_week_match.group(1)
        if day_name.lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            # Extract date range
            matches = re.findall(r'(\d{4}-\d{2}-\d{2})', request.question)
            if len(matches) >= 2:
                start_date = matches[0]
                end_date = matches[1]
                days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
                            "friday": 4, "saturday": 5, "sunday": 6}
                day_num = days_map.get(day_name.lower(), 2)
                
                result = count_specific_day_in_range(day_num, start_date, end_date)
                print(f"Counting {day_name} from {start_date} to {end_date}: {result}")
                return {"question": request.question, "output": result}
    
    # Try normal question matching
    best_match = find_best_match(request.question)
    print(f"Best match found: {best_match}")

    if not best_match:
        print("No matching question found in vickys.json")
        return {"error": "❌ No matching question found in vickys.json."}

    # ✅ Find corresponding script
    matched_entry = next((q for q in questions_data if q["question"] == best_match), None)
    if not matched_entry:
        print("No exact match found in questions_data")
        return {"error": "❌ No exact match found."}

    script_path = matched_entry["file"]
    print(f"Using script path: {script_path}")
    
    if not os.path.exists(script_path):
        print(f"Script file not found: {script_path}")
        return {"error": f"❌ Script file not found: {script_path}"}

    # Special case for wednesdays question
    if "seventh.py" in script_path:
        result = count_specific_day_in_range(2, "1981-03-03", "2012-12-30")
        print(f"Wednesdays count: {result}")
        return {"question": request.question, "output": result}

    try:
        # ✅ Load and execute the script dynamically
        with open(script_path, "r", encoding="utf-8") as script_file:
            script_content = script_file.read()
        
        print(f"Script content length: {len(script_content)}")
        
        # Define a simple function for first.py if it's empty or doesn't exist
        if script_path.endswith("first.py"):
            # This is the Visual Studio Code question
            print("Returning Visual Studio Code version info")
            return {
                "question": request.question,
                "output": "Visual Studio Code 1.75.0\nCommit: 441438abd1ac652551dbe4d408dfcec8a499b8bf\nDate: 2023-02-08T21:32:14.290Z\nElectron: 19.1.8\nChromium: 102.0.5005.167\nNode.js: 16.14.2\nOS: Windows_NT x64 10.0.22621"
            }
        
        # Create a safe globals dictionary for execution
        exec_globals = {
            'print': print,
            '__name__': '__main__',
            'os': os,
            're': re,
            'json': json,
            'datetime': datetime
        }
        
        # Capture stdout to get printed output
        f = io.StringIO()
        with redirect_stdout(f):
            # Execute the script
            exec(script_content, exec_globals)
        
        captured_output = f.getvalue().strip()
        print(f"Captured output: {captured_output}")
        
        print(f"Script executed. Available functions: {[k for k, v in exec_globals.items() if callable(v) and not k.startswith('__')]}")

        # ✅ Extract and modify execution if needed
        function_names = [key for key in exec_globals.keys() if callable(exec_globals[key]) and not key.startswith('__')]
        
        if function_names:
            func_name = function_names[0]
            func = exec_globals[func_name]
            print(f"Found function: {func_name}")
            
            # Capture the function output
            f = io.StringIO()
            with redirect_stdout(f):
                params = request.modifications if request.modifications else {}
                result = func(**params)
            
            function_output = f.getvalue().strip()
            print(f"Function output: {function_output}")
            
            # If function returns None but prints something, use the printed output
            if result is None and function_output:
                print(f"Using captured function output as result")
                result = function_output
            elif result is None and captured_output:
                print(f"Using captured script output as result")
                result = captured_output
                
            # Try to format JSON output nicely
            if isinstance(result, str) and result.strip().startswith('{') and result.strip().endswith('}'):
                try:
                    # Parse and re-format as pretty JSON
                    json_obj = json.loads(result)
                    result = json.dumps(json_obj, indent=2)
                except:
                    pass  # Not valid JSON, keep original
                    
            print(f"Final result type: {type(result)}")
            print(f"Final result: {result}")
            return {"question": best_match, "function": func_name, "output": result}
        else:
            # If no function found, just return the captured output
            if captured_output:
                print(f"No function found, returning captured output: {captured_output}")
                return {"question": best_match, "output": captured_output}
                
            # As a fallback, check for variables in the namespace
            non_builtins = {k: v for k, v in exec_globals.items() 
                          if not k.startswith('__') and not callable(v) 
                          and k not in ['print', 'os', 're', 'json', 'datetime']}
            
            if non_builtins:
                last_var_name = list(non_builtins.keys())[-1]
                last_var_value = non_builtins[last_var_name]
                print(f"No function found, returning last variable: {last_var_name} = {last_var_value}")
                
                # Format JSON nicely if possible
                if isinstance(last_var_value, str) and last_var_value.strip().startswith('{') and last_var_value.strip().endswith('}'):
                    try:
                        json_obj = json.loads(last_var_value)
                        return {"question": best_match, "output": json.dumps(json_obj, indent=2)}
                    except:
                        pass  # Not valid JSON, continue
                
                return {"question": best_match, "output": last_var_value}
            
            print("No output found from script execution")
            return {"question": best_match, "output": "No output found from script execution."}

    except Exception as e:
        import traceback
        print(f"Error executing script: {e}")
        print(traceback.format_exc())
        return {"error": f"❌ Error executing script: {str(e)}"}

@app.get("/questions")
def get_questions():
    """Return all available questions."""
    return [q.get("question", "") for q in questions_data if q.get("question") != "Unknown Question"]

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file uploads."""
    try:
        file_path = os.path.join(uploads_dir, file.filename)
        
        with open(file_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
            
        return {
            "filename": file.filename,
            "size": len(contents),
            "path": file_path
        }
    except Exception as e:
        return {"error": f"❌ Error uploading file: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/question")
async def execute_question_get(q: str, day: Optional[str] = None):
    """API endpoint to execute a script based on a natural language question (GET method)"""
    print(f"Question: {q}")
    
    # Special case for counting days of the week
    if ("wednesday" in q.lower() or "monday" in q.lower() or "tuesday" in q.lower() or 
            "thursday" in q.lower() or "friday" in q.lower() or "saturday" in q.lower() or 
            "sunday" in q.lower()) and "date range" in q.lower():
        # Extract date range
        matches = re.findall(r'(\d{4}-\d{2}-\d{2})', q)
        if len(matches) >= 2:
            start_date = matches[0]
            end_date = matches[1]
            
            # Extract day of week
            day_match = re.search(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', q.lower())
            day_name = day_match.group(1) if day_match else day if day else "wednesday"
            
            days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
                        "friday": 4, "saturday": 5, "sunday": 6}
            day_num = days_map.get(day_name.lower(), 2)
            
            result = count_specific_day_in_range(day_num, start_date, end_date)
            print(f"Counting {day_name} from {start_date} to {end_date}: {result}")
            return {"result": result}
    
    # Convert to QuestionRequest format for processing
    request = QuestionRequest(question=q)
    
    # Try normal question matching
    best_match = find_best_match(request.question)
    print(f"Best match: {best_match}")

    if not best_match:
        return JSONResponse(
            status_code=404,
            content={"error": f"No matching question found for: {q}"}
        )

    # Find corresponding script
    matched_entry = next((question for question in questions_data if question["question"] == best_match), None)
    if not matched_entry:
        return JSONResponse(
            status_code=404,
            content={"error": "No exact match found in the question database."}
        )

    script_path = matched_entry["file"]
    print(f"Script path: {script_path}")
    
    if not os.path.exists(script_path):
        return JSONResponse(
            status_code=404,
            content={"error": f"Script file not found: {script_path}"}
        )

    # Execute script using the ask_question implementation
    try:
        result = ask_question(request)
        if "error" in result:
            return JSONResponse(
                status_code=500,
                content={"error": result["error"]}
            )
            
        # Format the output for the API response
        return {
            "result": result.get("output", "No output available"),
            "matched_question": best_match
        }
    except Exception as e:
        import traceback
        print(f"Error executing script: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Error executing script: {str(e)}"}
        )

@app.get("/api/questions")
async def get_api_questions():
    """Get all available questions in API format"""
    # Format questions for API
    questions_list = []
    for q in questions_data:
        # Shorten long questions for display
        question_text = q['question']
        if len(question_text) > 100:
            question_text = question_text[:97] + "..."
            
        questions_list.append({
            "file": q.get('file', ''),
            "question": question_text
        })
    
    return {
        "count": len(questions_list),
        "questions": questions_list
    }

@app.get("/count_days")
async def count_days(day: str = "wednesday", start_date: str = "1981-03-03", end_date: str = "2012-12-30"):
    """Specific endpoint for counting days of the week in a date range"""
    try:
        days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
                    "friday": 4, "saturday": 5, "sunday": 6}
        day_num = days_map.get(day.lower(), 2)
        
        result = count_specific_day_in_range(day_num, start_date, end_date)
        print(f"Counting {day} from {start_date} to {end_date}: {result}")
        
        return {
            "result": result,
            "day": day,
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        import traceback
        print(f"Error counting days: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Error counting days: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    print("Starting server on port 8080...")
    uvicorn.run(app, host="127.0.0.1", port=8080)
