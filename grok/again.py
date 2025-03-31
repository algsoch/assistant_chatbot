import json
import os
import sys
import subprocess
import importlib.util
import inspect
import re
import shutil
import logging
import traceback
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from io import BytesIO, StringIO

from fastapi import FastAPI, WebSocket, UploadFile, File, Form, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("assignment_solver.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("assignment-solver")

# Configuration
BASE_DIR = Path("E:/data science tool")
TEMP_DIR = BASE_DIR / "temp_files"
TEMP_DIR.mkdir(exist_ok=True, parents=True)
QUESTION_PATH = BASE_DIR / "main" / "grok" / "question.py"

# Initialize FastAPI app
app = FastAPI(
    title="Data Science Assignment Solver",
    description="API to solve data science assignments based on natural language questions"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat history storage
CHAT_HISTORY: Dict[str, List[Dict[str, str]]] = {}

# Class to capture stdout
class CapturedOutput:
    def __init__(self, buffer):
        self.buffer = buffer
    
    def write(self, text):
        self.buffer.write(text)
    
    def flush(self):
        pass

class QuestionInfo:
    """Class to store information about a question and its implementation"""
    def __init__(self, 
                 question_text: str, 
                 script_path: str,
                 parameters: Any = None,
                 function_name: Optional[str] = None,
                 code_block: Optional[str] = None):
        self.question_text = question_text
        self.script_path = script_path
        self.parameters = parameters
        self.function_name = function_name
        self.code_block = code_block
        
    def __str__(self):
        return f"QuestionInfo(question='{self.question_text[:30]}...', script_path='{self.script_path}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_text": self.question_text,
            "script_path": self.script_path,
            "parameters": self.parameters,
            "function_name": self.function_name
        }

def extract_questions_from_file() -> List[QuestionInfo]:
    """Extract questions and their implementation details from question.py"""
    logger.info(f"Extracting questions from {QUESTION_PATH}")
    
    questions = []
    current_question = None
    current_script_path = None
    current_parameters = None
    current_code_block = []
    in_code_block = False
    
    try:
        with open(QUESTION_PATH, "r", encoding="utf-8") as f:
            content = f.readlines()
            
        for i, line in enumerate(content):
            # Check for script path comment
            if line.strip().startswith("# E:"):
                # If we were processing a previous question, save it
                if current_question is not None:
                    # Extract function name if available
                    function_name = None
                    code_text = "\n".join(current_code_block)
                    func_match = re.search(r'def\s+(\w+)\s*\(', code_text)
                    if func_match:
                        function_name = func_match.group(1)
                    
                    questions.append(QuestionInfo(
                        current_question, 
                        current_script_path,
                        current_parameters,
                        function_name,
                        code_text
                    ))
                    current_code_block = []
                
                # Extract new script path
                current_script_path = line.strip().replace("# ", "")
                in_code_block = False
                
            # Check for question definition
            elif "question" in line and "=" in line and ('"' in line or "'" in line):
                # Extract question text
                match = re.search(r'question\w*\s*=\s*[\'"](.+)[\'"]', line)
                if match:
                    current_question = match.group(1)
                in_code_block = False
                
            # Check for parameter definition
            elif "parameter" in line or "paramter" in line:
                # Extract parameter value
                match = re.search(r'param(?:e)?ter\s*=\s*[\'"]?([^\'"]*)[\'"]?', line)
                if match:
                    current_parameters = match.group(1)
                in_code_block = False
                
            # If we've seen a question definition and this isn't a metadata line, collect code
            elif current_question is not None:
                if "import" in line or "def " in line or "=" in line or line.strip().startswith("print"):
                    in_code_block = True
                
                if in_code_block or line.strip() and not line.strip().startswith("#"):
                    current_code_block.append(line.rstrip())
        
        # Add the last question if there is one
        if current_question is not None and current_code_block:
            # Extract function name if available
            function_name = None
            code_text = "\n".join(current_code_block)
            func_match = re.search(r'def\s+(\w+)\s*\(', code_text)
            if func_match:
                function_name = func_match.group(1)
            
            questions.append(QuestionInfo(
                current_question, 
                current_script_path,
                current_parameters,
                function_name,
                code_text
            ))
        
        logger.info(f"Extracted {len(questions)} questions from {QUESTION_PATH}")
        return questions
        
    except Exception as e:
        logger.error(f"Error extracting questions: {e}")
        logger.error(traceback.format_exc())
        return []

# Global storage for extracted questions
QUESTIONS = extract_questions_from_file()

def extract_keywords(text: str) -> List[str]:
    """Extract significant keywords from text for matching"""
    # Remove common words and punctuation
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    
    # Common stop words to filter out
    stop_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "about", 
                 "from", "as", "of", "an", "a", "is", "was", "were", "be", "been", "being", 
                 "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", 
                 "can", "could", "may", "might", "must", "that", "this", "these", "those", 
                 "what", "which", "who", "whom", "whose", "when", "where", "why", "how"}
    
    # Filter words
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    
    return keywords

def find_best_question_match(query: str) -> Optional[QuestionInfo]:
    """Find the best matching question for a given query"""
    logger.info(f"Finding best match for: {query[:50]}...")
    
    if not QUESTIONS:
        logger.error("No questions have been loaded")
        return None
    
    # Clean the query
    query = query.lower().strip()
    
    # 1. Try exact match first
    for question_info in QUESTIONS:
        if question_info.question_text.lower() == query:
            logger.info(f"Found exact match: {question_info.script_path}")
            return question_info
    
    # 2. Try contains match
    for question_info in QUESTIONS:
        if query in question_info.question_text.lower() or question_info.question_text.lower() in query:
            logger.info(f"Found contains match: {question_info.script_path}")
            return question_info
    
    # 3. Use keyword matching
    query_keywords = extract_keywords(query)
    
    best_match = None
    best_score = 0
    
    for question_info in QUESTIONS:
        question_keywords = extract_keywords(question_info.question_text)
        
        # Calculate similarity based on matching keywords
        matching_keywords = set(query_keywords) & set(question_keywords)
        score = len(matching_keywords) / max(1, len(query_keywords))
        
        if score > best_score:
            best_score = score
            best_match = question_info
    
    if best_score >= 0.5:  # Threshold for accepting a match
        logger.info(f"Found keyword match with score {best_score:.2f}: {best_match.script_path}")
        return best_match
    
    # 4. Special case handling for common questions
    if "code -s" in query:
        for question_info in QUESTIONS:
            if "code -s" in question_info.question_text.lower():
                logger.info(f"Found special case match for 'code -s': {question_info.script_path}")
                return question_info
    
    elif "httpbin" in query or "http request" in query:
        for question_info in QUESTIONS:
            if "httpbin" in question_info.question_text.lower():
                logger.info(f"Found special case match for 'httpbin': {question_info.script_path}")
                return question_info
                
    elif "physics marks" in query and "maths" in query:
        for question_info in QUESTIONS:
            if "physics" in question_info.question_text.lower() and "marks" in question_info.question_text.lower():
                logger.info(f"Found special case match for 'physics marks': {question_info.script_path}")
                return question_info
    
    # If no good match is found
    logger.warning(f"No good match found for query: {query[:50]}...")
    return None

def extract_parameters(query: str, question_info: QuestionInfo) -> Dict[str, Any]:
    """Extract parameters from the query for the given question"""
    params = {}
    query_lower = query.lower()
    
    # Extract dates if present
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})', query)
    if date_match:
        params["start_date"] = date_match.group(1)
        params["end_date"] = date_match.group(2)
    
    # Extract day of week if present
    day_match = re.search(r'how many (\w+)s are there', query_lower)
    if day_match:
        params["day_of_week"] = day_match.group(1).capitalize()
    
    # Extract email if present
    email_match = re.search(r'email\s+(?:set\s+to\s+)?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', query_lower)
    if email_match:
        params["email"] = email_match.group(1)
    
    # Extract city and country if present
    location_match = re.search(r'(city|town)\s+(\w+)\s+(?:in|of)\s+(?:the\s+)?(country\s+)?(\w+)', query_lower)
    if location_match:
        params["city"] = location_match.group(2).capitalize()
        params["country"] = location_match.group(4).capitalize()
    
    # Include the parameter from the question definition
    if question_info.parameters:
        # Check if it's a list literal
        if question_info.parameters.startswith('[') and question_info.parameters.endswith(']'):
            try:
                params["param_list"] = eval(question_info.parameters)
            except:
                params["param"] = question_info.parameters
        else:
            params["param"] = question_info.parameters
    
    logger.info(f"Extracted parameters: {params}")
    return params

def find_script_path(script_path: str) -> Optional[Path]:
    """Find the actual script path by checking multiple locations"""
    # Try the path as is
    path = Path(script_path)
    if path.exists():
        return path
    
    # Try with normalized path
    path = Path(script_path.replace("//", "/"))
    if path.exists():
        return path
    
    # Extract GA folder and script name
    match = re.search(r'(GA\d+)[/\\]([a-zA-Z]+)\.py', script_path)
    if match:
        ga_folder = match.group(1)
        script_name = match.group(2)
        
        # Try direct path
        path = BASE_DIR / ga_folder / f"{script_name}.py"
        if path.exists():
            return path
    
    logger.error(f"Could not find script at {script_path}")
    return None

def run_function_from_code(code_block: str, function_name: str, params: Dict[str, Any] = None) -> str:
    """Execute a function from a code block"""
    # Create a unique module name
    module_name = f"dynamic_module_{hash(code_block)}"
    
    # Capture stdout to get printed output
    original_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = CapturedOutput(captured_output)
    
    try:
        # Compile and execute the code
        exec_globals = {}
        exec(code_block, exec_globals)
        
        # Check if the function exists
        if function_name in exec_globals and callable(exec_globals[function_name]):
            # Call the function with parameters if they exist
            if params:
                result = exec_globals[function_name](params)
            else:
                result = exec_globals[function_name]()
            
            # Get the captured output
            output = captured_output.getvalue()
            
            # Combine output and result
            if result is not None:
                if output:
                    return f"{output}\n\nFunction return value: {result}"
                else:
                    return str(result)
            else:
                return output or "Function executed but no output produced"
        else:
            # Function not found, just return any captured output
            return captured_output.getvalue() or "Code executed but no specific function found"
    
    except Exception as e:
        logger.error(f"Error running function from code: {e}")
        return f"Error: {str(e)}\n{traceback.format_exc()}"
    
    finally:
        # Restore stdout
        sys.stdout = original_stdout

def run_code_block(code_block: str, params: Dict[str, Any] = None) -> str:
    """Execute a code block and capture its output"""
    # Capture stdout to get printed output
    original_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = CapturedOutput(captured_output)
    
    try:
        # Create a local namespace and add parameters
        local_namespace = {}
        if params:
            local_namespace.update(params)
        
        # Execute the code block
        exec(code_block, globals(), local_namespace)
        
        # Return the captured output
        output = captured_output.getvalue()
        return output or "Code executed but no output produced"
    
    except Exception as e:
        logger.error(f"Error running code block: {e}")
        return f"Error: {str(e)}\n{traceback.format_exc()}"
    
    finally:
        # Restore stdout
        sys.stdout = original_stdout

def run_script_with_subprocess(script_path: str, params: Dict[str, Any] = None, file_content: BytesIO = None) -> str:
    """Run a script using subprocess"""
    try:
        # Find the actual script path
        actual_path = find_script_path(script_path)
        if not actual_path:
            return f"Error: Script not found at {script_path}"
        
        script_path = str(actual_path)
        logger.info(f"Running script via subprocess: {script_path}")
        
        # Save file if provided
        file_path = None
        if file_content:
            file_path = os.path.join(TEMP_DIR, "uploaded_file")
            with open(file_path, "wb") as f:
                f.write(file_content.read() if hasattr(file_content, "read") else file_content.getvalue())
            logger.info(f"Saved uploaded file to {file_path}")
        
        # Set environment variables for parameters
        env = os.environ.copy()
        if params:
            env["SCRIPT_PARAMS"] = json.dumps(params)
        if file_path:
            env["INPUT_FILE_PATH"] = file_path
        
        # Run the script
        command = [sys.executable, script_path]
        
        # Add command line arguments for parameters
        if params:
            for key, value in params.items():
                if isinstance(value, str):
                    command.extend([f"--{key}", value])
                elif isinstance(value, (int, float)):
                    command.extend([f"--{key}", str(value)])
        
        logger.info(f"Executing command: {' '.join(command)}")
        
        process = subprocess.run(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        
        # Handle return code
        if process.returncode != 0:
            logger.warning(f"Script returned non-zero exit code: {process.returncode}")
            logger.warning(f"Stderr: {process.stderr}")
            
            # Include both stdout and stderr in the output
            if process.stdout and process.stderr:
                return f"{process.stdout}\n\nErrors:\n{process.stderr}"
            elif process.stderr:
                return f"Error executing script:\n{process.stderr}"
            else:
                return process.stdout or "No output from script"
        
        return process.stdout
        
    except subprocess.TimeoutExpired:
        return "Error: Script execution timed out after 60 seconds"
    except Exception as e:
        logger.error(f"Error running script with subprocess: {e}")
        return f"Error running script: {str(e)}\n{traceback.format_exc()}"

def process_question(question: str, file_content: BytesIO = None) -> str:
    """Process a question and return the answer"""
    try:
        # Find the best matching question
        question_info = find_best_question_match(question)
        
        if not question_info:
            return "I couldn't find a matching question. Could you please rephrase or be more specific?"
        
        # Extract parameters
        params = extract_parameters(question, question_info)
        
        # Try to run the code in different ways
        
        # Method 1: If we have a code block and function name, run that directly
        if question_info.code_block and question_info.function_name:
            logger.info(f"Running function {question_info.function_name} from code block")
            try:
                return run_function_from_code(question_info.code_block, question_info.function_name, params)
            except Exception as e:
                logger.error(f"Error running function from code: {e}")
                # Fall back to running the whole code block
        
        # Method 2: If we have a code block but no function name, run the whole block
        if question_info.code_block:
            logger.info("Running entire code block")
            return run_code_block(question_info.code_block, params)
        
        # Method 3: Run the script file using subprocess
        if question_info.script_path:
            logger.info(f"Running script file: {question_info.script_path}")
            return run_script_with_subprocess(question_info.script_path, params, file_content)
        
        return "I found a matching question, but couldn't execute the code. Please check the implementation."
    
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        return f"Error: {str(e)}\n{traceback.format_exc()}"

def cleanup_temp_dir():
    """Clean up temporary files"""
    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
            TEMP_DIR.mkdir(exist_ok=True, parents=True)
            logger.info("Temporary directory cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}")

@app.post("/api/solve")
async def solve_assignment(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """API endpoint to solve an assignment"""
    try:
        logger.info(f"Received question: {question[:100]}...")
        
        # Handle file upload
        file_content = None
        if file:
            file_content = BytesIO(await file.read())
            logger.info(f"Received file: {file.filename}")
        
        # Process the question
        answer = process_question(question, file_content)
        
        # Clean up temporary files
        cleanup_temp_dir()
        
        return {"answer": answer}
    except Exception as e:
        logger.error(f"API error: {e}")
        cleanup_temp_dir()
        return {"answer": f"Error: {str(e)}\n{traceback.format_exc()}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat interface"""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    CHAT_HISTORY[session_id] = []
    
    try:
        # Send welcome message
        await websocket.send_json({
            "message": "Hello! I'm your Data Science Assignment Assistant. How can I help you today?",
            "type": "bot"
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            question = data.get("message", "")
            file_content = None
            
            # Handle file if present
            if "file" in data and data["file"]:
                import base64
                file_data = data["file"].split(",")[1]
                file_content = BytesIO(base64.b64decode(file_data))
                logger.info("Received file upload via WebSocket")
            
            # Add message to history
            CHAT_HISTORY[session_id].append({"type": "user", "message": question})
            
            # Process the question
            answer = process_question(question, file_content)
            
            # Add response to history
            CHAT_HISTORY[session_id].append({"type": "bot", "message": answer})
            
            # Send response
            await websocket.send_json({
                "message": answer,
                "type": "bot",
                "history": CHAT_HISTORY[session_id]
            })
            
            # Clean up temporary files
            cleanup_temp_dir()
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        if session_id in CHAT_HISTORY:
            del CHAT_HISTORY[session_id]
        cleanup_temp_dir()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "message": f"An error occurred: {str(e)}",
                "type": "error"
            })
        except:
            pass
        if session_id in CHAT_HISTORY:
            del CHAT_HISTORY[session_id]
        cleanup_temp_dir()

@app.get("/", response_class=HTMLResponse)
async def get_chat_ui(request: Request):
    """Serve the chat UI"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Data Science Assignment Solver</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                height: 100vh;
                background-color: #f5f5f5;
            }
            .header {
                background-color: #4a69bd;
                color: white;
                padding: 15px 20px;
                text-align: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .chat-container {
                flex: 1;
                display: flex;
                flex-direction: column;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                width: 100%;
                box-sizing: border-box;
            }
            .chat-box {
                flex: 1;
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                overflow-y: auto;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .message {
                margin-bottom: 15px;
                padding: 10px 15px;
                border-radius: 6px;
                max-width: 80%;
                word-wrap: break-word;
            }
            .user-message {
                background-color: #e3f2fd;
                margin-left: auto;
                border-top-right-radius: 0;
            }
            .bot-message {
                background-color: #f1f1f1;
                margin-right: auto;
                border-top-left-radius: 0;
            }
            .input-area {
                display: flex;
                flex-direction: column;
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .message-input {
                flex: 1;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 10px;
                resize: none;
                font-family: Arial, sans-serif;
            }
            .file-upload {
                margin-bottom: 10px;
            }
            .send-button {
                padding: 12px 20px;
                background-color: #4a69bd;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
            }
            .send-button:hover {
                background-color: #3b5998;
            }
            pre {
                background-color: #f8f8f8;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-width: 100%;
            }
            code {
                background-color: #f0f0f0;
                padding: 2px 4px;
                border-radius: 4px;
                font-family: monospace;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 10px 0;
            }
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(74, 105, 189, 0.3);
                border-radius: 50%;
                border-top-color: #4a69bd;
                animation: spin 1s ease-in-out infinite;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .file-info {
                display: none;
                padding: 8px;
                background-color: #e3f2fd;
                border-radius: 4px;
                margin-bottom: 10px;
            }
            .suggestions {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 15px;
            }
            .suggestion {
                padding: 8px 12px;
                background-color: #e3f2fd;
                border-radius: 16px;
                font-size: 0.9em;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            .suggestion:hover {
                background-color: #bbdefb;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Data Science Assignment Solver</h1>
        </div>
        <div class="chat-container">
            <div class="chat-box" id="chatBox"></div>
            
            <div class="suggestions">
                <div class="suggestion" onclick="setMessage('What is the output of code -s?')">VS Code Output</div>
                <div class="suggestion" onclick="setMessage('Send a HTTPS request to httpbin.org/get with email set to 24f2006438@ds.study.iitm.ac.in')">HTTP Request</div>
                <div class="suggestion" onclick="setMessage('How many Wednesdays are there in the date range 1981-03-03 to 2012-12-30?')">Count Wednesdays</div>
                <div class="suggestion" onclick="setMessage('Calculate the total Physics marks of students who scored 69 or more marks in Maths')">Student Marks Analysis</div>
            </div>
            
            <div class="file-info" id="fileInfo">
                <span id="fileName"></span>
                <button onclick="removeFile()" style="margin-left: 10px;">Remove</button>
            </div>
            
            <div class="loading" id="loading">
                <div class="loading-spinner"></div> Processing...
            </div>
            
            <div class="input-area">
                <textarea class="message-input" id="messageInput" placeholder="Type your question here..." rows="3"></textarea>
                <input type="file" class="file-upload" id="fileUpload">
                <button class="send-button" id="sendButton">Send</button>
            </div>
        </div>
        
        <script>
            let ws;
            let fileData = null;
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'error') {
                        addMessage(data.message, 'bot', true);
                    } else {
                        addMessage(data.message, data.type);
                    }
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('sendButton').disabled = false;
                };
                
                ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    setTimeout(connectWebSocket, 3000);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    addMessage('Connection error. Please try again later.', 'bot', true);
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('sendButton').disabled = false;
                };
            }
            
            function sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const message = messageInput.value.trim();
                
                if (!message) return;
                
                addMessage(message, 'user');
                messageInput.value = '';
                
                document.getElementById('loading').style.display = 'block';
                document.getElementById('sendButton').disabled = true;
                
                const data = { message: message };
                
                if (fileData) {
                    data.file = fileData;
                }
                
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify(data));
                } else {
                    // Fallback to REST API if WebSocket not available
                    const formData = new FormData();
                    formData.append('question', message);
                    
                    if (fileData) {
                        const fileBlob = dataURItoBlob(fileData);
                        formData.append('file', fileBlob, 'file');
                    }
                    
                    fetch('/api/solve', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        addMessage(data.answer, 'bot');
                        document.getElementById('loading').style.display = 'none';
                        document.getElementById('sendButton').disabled = false;
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        addMessage('Error processing your request. Please try again.', 'bot', true);
                        document.getElementById('loading').style.display = 'none';
                        document.getElementById('sendButton').disabled = false;
                    });
                }
                
                fileData = null;
                document.getElementById('fileInfo').style.display = 'none';
            }
            
            function addMessage(text, sender, isError = false) {
                const chatBox = document.getElementById('chatBox');
                const messageElement = document.createElement('div');
                messageElement.className = `message ${sender}-message`;
                
                if (isError) {
                    messageElement.style.backgroundColor = '#ffebee';
                }
                
                const formattedText = formatMessage(text);
                messageElement.innerHTML = formattedText;
                
                chatBox.appendChild(messageElement);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            
            function formatMessage(text) {
                if (!text) return '';
                
                // Replace code blocks with <pre> tags
                let formattedText = text.replace(/```([^`]+)```/g, '<pre>$1</pre>');
                
                // Handle single line code
                formattedText = formattedText.replace(/`([^`]+)`/g, '<code>$1</code>');
                
                // Replace URLs with links
                formattedText = formattedText.replace(
                    /(https?:\/\/[^\s]+)/g, 
                    '<a href="$1" target="_blank">$1</a>'
                );
                
                // Replace line breaks with <br>
                formattedText = formattedText.replace(/\\n/g, '<br>');
                formattedText = formattedText.replace(/\n/g, '<br>');
                
                return formattedText;
            }
            
            function handleFileUpload(event) {
                const file = event.target.files[0];
                if (!file) return;
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    fileData = e.target.result;
                    
                    document.getElementById('fileInfo').style.display = 'block';
                    document.getElementById('fileName').textContent = file.name;
                };
                reader.readAsDataURL(file);
            }
            
            function removeFile() {
                document.getElementById('fileUpload').value = '';
                fileData = null;
                document.getElementById('fileInfo').style.display = 'none';
            }
            
            function setMessage(text) {
                document.getElementById('messageInput').value = text;
                document.getElementById('messageInput').focus();
            }
            
            function dataURItoBlob(dataURI) {
                const byteString = atob(dataURI.split(',')[1]);
                const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                
                for (let i = 0; i < byteString.length; i++) {
                    ia[i] = byteString.charCodeAt(i);
                }
                
                return new Blob([ab], { type: mimeString });
            }
            
            document.addEventListener('DOMContentLoaded', function() {
                connectWebSocket();
                
                document.getElementById('sendButton').addEventListener('click', sendMessage);
                
                document.getElementById('messageInput').addEventListener('keydown', function(event) {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        sendMessage();
                    }
                });
                
                document.getElementById('fileUpload').addEventListener('change', handleFileUpload);
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"error": f"An unexpected error occurred: {str(exc)}"}
    )

# Clean up on shutdown
@app.on_event("shutdown")
def shutdown_event():
    """Clean up on application shutdown"""
    logger.info("Shutting down application...")
    cleanup_temp_dir()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)