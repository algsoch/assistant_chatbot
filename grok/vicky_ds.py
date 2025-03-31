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

# Create the HTML template file - same as your original implementation
with open(TEMPLATES_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS - Tools for Data Science</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #4c2882;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            margin: 0;
            font-size: 28px;
        }
        .subtitle {
            font-style: italic;
            opacity: 0.8;
            margin-top: 10px;
        }
        .chat-box {
            height: 500px;
            overflow-y: auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .message {
            padding: 10px 15px;
            border-radius: 18px;
            margin-bottom: 10px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background-color: #e6f7ff;
            margin-left: auto;
            border-top-right-radius: 4px;
            text-align: right;
        }
        .bot-message {
            background-color: #f0f0f0;
            margin-right: auto;
            border-top-left-radius: 4px;
            white-space: pre-wrap;
        }
        .input-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .question-input {
            flex-grow: 1;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 16px;
        }
        .send-button {
            padding: 12px 24px;
            background-color: #4c2882;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        .send-button:hover {
            background-color: #3a1c68;
        }
        .file-upload-section {
            margin-top: 20px;
            padding: 15px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .file-upload-title {
            margin-top: 0;
            margin-bottom: 15px;
            color: #4c2882;
        }
        .file-input-container {
            display: flex;
            gap: 10px;
        }
        .file-input {
            flex-grow: 1;
            padding: 8px;
        }
        .upload-button {
            padding: 8px 16px;
            background-color: #4c2882;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .uploaded-files {
            margin-top: 10px;
        }
        code {
            background-color: #f8f8f8;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: monospace;
        }
        pre {
            background-color: #f8f8f8;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .code-block {
            background-color: #f8f8f8;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: monospace;
        }
        .status-bar {
            background-color: #4c2882;
            color: white;
            padding: 5px 10px;
            position: fixed;
            bottom: 0;
            width: 100%;
            text-align: center;
            font-size: 12px;
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
            display: inline-block;
            padding: 12px;
            background-color: #f0f0f0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 18px;
            transition: background-color 0.3s;
        }
        .file-button:hover {
            background-color: #e0e0e0;
        }
        #fileAttachment:focus + .file-button {
            outline: 1px solid #4c2882;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS - Tools for Data Science</h1>
            <div class="subtitle">Currently only 8 questions from Graded Assignment 1 are available</div>
        </header>
        
        <div class="chat-box" id="chatBox">
            <div class="message bot-message">
                Hello! I'm your TDS assistant. You can ask me questions about the first 8 tasks in Graded Assignment 1.
                
                Here are examples of questions I can help with:
                - What is the output of code -s?
                - Send a HTTPS request to httpbin.org with email parameter
                - How to use npx and prettier with README.md?
                - Google Sheets formula with SEQUENCE and ARRAY_CONSTRAIN
                - Excel formula with SORTBY and TAKE
                - Find hidden input value
                - How many Wednesdays are in a date range?
                - Extract data from CSV in a ZIP file
                
                <strong>Working with your own files:</strong>
                1. Upload your file using the form below
                2. You'll receive a file ID (like abc123de) 
                3. Include that ID in your question, for example:
                   "Run npx prettier on README.md with ID abc123de" or
                   "Extract data from ZIP file with ID abc123de"
            </div>
        </div>
        
        <form class="input-form" id="questionForm" enctype="multipart/form-data" onsubmit="sendQuestionWithFile(event)">
            <input type="text" class="question-input" id="questionInput" placeholder="Ask your question..." autocomplete="off">
            <div class="file-attach">
                <input type="file" id="fileAttachment" name="file">
                <label for="fileAttachment" class="file-button">📎</label>
            </div>
            <button type="submit" class="send-button">Ask</button>
        </form>
        
        <div class="file-upload-section">
            <h3 class="file-upload-title">Upload Files for Processing</h3>
            <form class="file-input-container" action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" class="file-input" name="file">
                <button type="submit" class="upload-button">Upload</button>
            </form>
            <div class="uploaded-files" id="uploadedFiles">
                {% if files %}
                    <p>Uploaded files:</p>
                    <ul>
                        {% for file in files %}
                            <li>{{ file }} <a href="/use-file/{{ file }}">Use this file</a></li>
                        {% endfor %}
                    </ul>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        Server status: Running | Port: 8000 | Version: 1.0
    </div>

    <script>
        function sendQuestion(event) {
            event.preventDefault();
            const questionInput = document.getElementById('questionInput');
            const question = questionInput.value.trim();
            
            if (!question) return;
            
            // Display user question
            addMessage(question, 'user');
            
            // Clear input
            questionInput.value = '';
            
            // Display loading indicator
            const loadingId = 'loading-' + Date.now();
            addMessage('Processing your request...', 'bot', loadingId);
            
            // Send question to server
            fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `question=${encodeURIComponent(question)}`
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading message
                const loadingMsg = document.getElementById(loadingId);
                if (loadingMsg) loadingMsg.remove();
                
                // Format and display answer
                let formattedAnswer = formatAnswer(data.answer);
                addMessage(formattedAnswer, 'bot');
            })
            .catch(error => {
                // Remove loading message
                const loadingMsg = document.getElementById(loadingId);
                if (loadingMsg) loadingMsg.remove();
                
                console.error('Error:', error);
                addMessage("Sorry, there was an error processing your question.", 'bot');
            });
        }
        
        function sendQuestionWithFile(event) {
            event.preventDefault();
            const questionInput = document.getElementById('questionInput');
            const fileInput = document.getElementById('fileAttachment');
            const question = questionInput.value.trim();
            
            if (!question) return;
            
            // Display user question
            addMessage(question + (fileInput.files.length > 0 ? ` (with file: ${fileInput.files[0].name})` : ''), 'user');
            
            // Clear input
            questionInput.value = '';
            
            // Display loading indicator
            const loadingId = 'loading-' + Date.now();
            addMessage('Processing your request...', 'bot', loadingId);
            
            // Send question with file to server
            const formData = new FormData();
            formData.append('question', question);
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
                
                // Format and display answer
                let formattedAnswer = formatAnswer(data.answer);
                addMessage(formattedAnswer, 'bot');
                
                // Reset file input
                fileInput.value = '';
            })
            .catch(error => {
                // Remove loading message
                const loadingMsg = document.getElementById(loadingId);
                if (loadingMsg) loadingMsg.remove();
                
                console.error('Error:', error);
                addMessage("Sorry, there was an error processing your question.", 'bot');
            });
        }
        
        function addMessage(text, sender, id = null) {
            const chatBox = document.getElementById('chatBox');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            if (id) messageDiv.id = id;
            messageDiv.innerHTML = text;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function formatAnswer(text) {
            if (!text) return "No response received";
            
            // Replace code blocks with styled versions
            text = text.replace(/```(.*?)```/gs, function(match, code) {
                return `<div class="code-block">${code}</div>`;
            });
            
            // Replace inline code
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            // Handle line breaks
            text = text.replace(/\\n/g, '<br>');
            
            return text;
        }
        
        // Check server connectivity on page load
        window.addEventListener('load', function() {
            fetch('/health')
                .then(response => {
                    if (response.ok) {
                        document.querySelector('.status-bar').style.backgroundColor = '#4CAF50';
                        document.querySelector('.status-bar').textContent = 'Server status: Connected | Ready to answer questions';
                    } else {
                        document.querySelector('.status-bar').style.backgroundColor = '#f44336';
                        document.querySelector('.status-bar').textContent = 'Server status: Connected but reporting issues';
                    }
                })
                .catch(error => {
                    document.querySelector('.status-bar').style.backgroundColor = '#f44336';
                    document.querySelector('.status-bar').textContent = 'Server status: Disconnected | Please refresh the page';
                });
        });
    </script>
</body>
</html>
""")

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

# Update the ask_question function to handle file types more generically

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

# Create a global registry for uploaded files
UPLOADED_FILES_REGISTRY = {}  # Maps unique IDs to actual file paths

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

# Update the upload file function to display file IDs better

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

# Add this function to make file IDs more accessible

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
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #4c2882;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            margin: 0;
            font-size: 28px;
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
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Uploaded Files</h1>
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
async def ask_with_file(question: str = Form(...), file: UploadFile = File(None)):
    try:
        logger.info(f"Processing question with file: {question[:50]}...")
        
        # If a file was provided, save and process it
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            logger.info(f"File uploaded with question: {filename} (ID: {file_id})")
            
            # Add file context directly to the question
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            elif file_ext == ".md":
                question += f" The README.md file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        try:
            # Process file and question
            answer = answer_question(question)
            return {"success": True, "answer": answer}
        except FileNotFoundError as e:
            return {
                "success": False,
                "error": "File not found on server. Please upload your file with the question.",
                "details": str(e)
            }
        except PermissionError as e:
            return {
                "success": False, 
                "error": "Server cannot access the file. File permissions issue.",
                "details": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing your request: {str(e)}",
                "error_type": e.__class__.__name__
            }
    except Exception as e:
        logger.error(f"Error processing question with file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing your question: {str(e)}")

@app.get("/api/docs", response_class=HTMLResponse)
async def api_docs(request: Request):
    return templates.TemplateResponse(
        "api_docs.html",
        {"request": request}
    )

# Create a template for the API documentation page
with open(TEMPLATES_DIR / "api_docs.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS API Documentation</title>
    <!-- CSS styles here -->
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS API Documentation</h1>
        </header>
        
        <section>
            <h2>Asking Questions</h2>
            
            <h3>POST /api/ask_with_file</h3>
            <p>Ask a question with an optional file attachment</p>
            
            <h4>Parameters</h4>
            <ul>
                <li><strong>question</strong> (required) - The question text</li>
                <li><strong>file</strong> (optional) - A file to use with the question</li>
            </ul>
            
            <h4>Example</h4>
            <pre>
curl -X POST "http://yourdomain.com/api/ask_with_file" \
  -F "question=Extract data from this ZIP file" \
  -F "file=@/path/to/file.zip"
            </pre>
            
            <h4>Response</h4>
            <pre>
{
  "success": true,
  "answer": "The answer from extract.csv is 42",
  "question": "Extract data from this ZIP file"
}
            </pre>
        </section>
        
        <section>
    <h2>File Processing API</h2>
    
    <h3>POST /api/process</h3>
    <p>Process a question that requires a file (like README.md for Question 3 or ZIP for Question 8)</p>
    
    <h4>Parameters</h4>
    <ul>
        <li><strong>question</strong> (required) - The question text</li>
        <li><strong>file</strong> (required) - The file to process</li>
        <li><strong>question_type</strong> (optional) - Hint about question type:
            <ul>
                <li><code>npx_readme</code> - For GA1 third question (README.md with npx)</li>
                <li><code>extract_zip</code> - For GA1 eighth question (Extract from ZIP)</li>
            </ul>
        </li>
    </ul>
    
    <h4>cURL Example</h4>
    <pre>
# For README.md (Question 3)
curl -X POST "http://localhost:8000/api/process" \
  -F "question=What is the output of npx prettier on this README file?" \
  -F "file=@/path/to/README.md" \
  -F "question_type=npx_readme"

# For ZIP file (Question 8)
curl -X POST "http://localhost:8000/api/process" \
  -F "question=What is the value in the answer column?" \
  -F "file=@/path/to/q-extract-csv-zip.zip" \
  -F "question_type=extract_zip"
    </pre>
</section>
    </div>
</body>
</html>
""")

@app.post("/api/process")
async def api_process(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...),
    question_type: str = Form(None)  # Optional hint about which question it is
):
    """Process a question with an optional file through API"""
    try:
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Auto-detect the question type from file extension if not specified
            if not question_type:
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext == ".md":
                    question_type = "npx_readme"  # GA1 third question
                elif file_ext == ".zip":
                    question_type = "extract_zip"  # GA1 eighth question
            
            # Add appropriate context based on detected question type
            if question_type == "npx_readme" or (file.filename.lower() == "readme.md"):
                question += f" The README.md file is located at {file_path}"
            elif question_type == "extract_zip" or file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the enhanced question
        answer = answer_question(question)
        
        # Return a structured response for API clients
        return {
            "success": True,
            "answer": answer,
            "file_processed": bool(file and file.filename),
            "question": question
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_details": str(e.__class__.__name__)
        }

@app.get("/connection-info")
async def connection_info():
    """Get server connection details - useful for debugging remote connections"""
    import platform
    import socket
    
    # Get hostname and IP
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except:
        ip = "Unable to determine IP"
    
    # Return connection info
    return {
        "server": {
            "hostname": hostname,
            "operating_system": platform.system(),
            "ip_address": ip,
            "python_version": platform.python_version(),
        },
        "request_handling": {
            "file_upload_directory": str(UPLOADS_DIR.absolute()),
            "ngrok_support": "Supported (use 'ngrok http 8000' to expose)"
        }
    }

# Add this to the startup code of your application
@app.on_event("startup")
async def startup_event():
    """Run when the application starts"""
    # Create uploads directory if it doesn't exist
    UPLOADS_DIR.mkdir(exist_ok=True)
    logger.info(f"Uploads directory ready: {UPLOADS_DIR.absolute()}")
    
    # Load existing files into registry
    load_existing_files()

def load_existing_files():
    """Load any existing files in the uploads directory into the registry"""
    if UPLOADS_DIR.exists():
        for file_path in UPLOADS_DIR.iterdir():
            if file_path.is_file():
                # Register existing file with its original timestamp if possible
                try:
                    # Try to extract timestamp from filename (assumes format: YYYYMMDD_HHMMSS_originalname)
                    filename = file_path.name
                    parts = filename.split('_', 2)
                    if len(parts) >= 3:
                        original_name = parts[2]  # Get original filename
                        file_id = register_uploaded_file(original_name, str(file_path))
                        logger.info(f"Loaded existing file: {filename} (ID: {file_id})")
                except Exception as e:
                    logger.warning(f"Couldn't register existing file {file_path}: {e}")

def start():
    """Function to start the server with proper error handling"""
    try:
        print("\n" + "=" * 50)
        print("Starting TDS - Tools for Data Science Server")
        print("=" * 50)
        print("\n* Access the web interface at: http://127.0.0.1:8000")
        print("* Press Ctrl+C to stop the server\n")
        
        # Use 127.0.0.1 instead of 0.0.0.0 for better local access
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\nError starting the server: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure port 8000 is not already in use")
        print("2. Check that you have permissions to create files/directories")
        print("3. Ensure vicky_server.py is in the same directory")
        sys.exit(1)

if __name__ == "__main__":
    start()