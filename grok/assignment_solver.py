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

# Initialize FastAPI app
app = FastAPI(
    title="Data Science Assignment Solver",
    description="API to solve IIT Madras Data Science graded assignments"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat history (in-memory)
CHAT_HISTORY: Dict[str, List[Dict[str, str]]] = {}

# Script mapping structure
SCRIPT_MAPPING = {
    "GA1": {},
    "GA2": {},
    "GA3": {},
    "GA4": {}
}

# Class to capture stdout
class CapturedOutput:
    def __init__(self, buffer):
        self.buffer = buffer
    
    def write(self, text):
        self.buffer.write(text)
    
    def flush(self):
        pass

def load_training_dataset():
    """Load the training dataset for question matching"""
    possible_paths = [
        "training_dataset.json",
        BASE_DIR / "training_dataset.json",
        BASE_DIR / "main" / "training_dataset.json",
        Path("E:/data science tool/training_dataset.json")
    ]
    
    for path in possible_paths:
        try:
            path = Path(path)
            if path.exists():
                logger.info(f"Loading training dataset from {path}")
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading training dataset from {path}: {e}")
    
    logger.warning("No training dataset found, using empty dataset")
    return []

def initialize_script_mapping():
    """Initialize the script mapping based on folder structure"""
    # Map GA folders to script counts
    ga_counts = {
        "GA1": 19,  # GA1 has 19 scripts
        "GA2": 10,  # GA2 has 10 scripts
        "GA3": 10,  # GA3 has 10 scripts
        "GA4": 10   # GA4 has 10 scripts
    }
    
    # Names for scripts (1-19)
    script_names = [
        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", 
        "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", 
        "seventeenth", "eighteenth", "nineteenth"
    ]
    
    # Map all scripts by their folder and name
    for ga_folder, count in ga_counts.items():
        for i in range(1, count + 1):
            script_name = script_names[i-1]
            script_path = f"E://data science tool//{ga_folder}//{script_name}.py"
            
            # Create the entry for this script
            SCRIPT_MAPPING[ga_folder][script_name] = {
                "path": script_path,
                "index": i,
                "questions": []  # Will be populated from training dataset
            }
    
    # Load training dataset
    training_data = load_training_dataset()
    
    # Map training questions to scripts
    question_index = 0
    for ga_folder, scripts in SCRIPT_MAPPING.items():
        for script_name, script_info in scripts.items():
            # If we have a training question for this index, use it
            if question_index < len(training_data):
                question_data = training_data[question_index]
                # Add question and answer to the script info
                script_info["questions"].append({
                    "text": question_data.get("question", f"Question for {ga_folder}/{script_name}"),
                    "answer": question_data.get("answer", "")
                })
            question_index += 1
    
    logger.info(f"Initialized script mapping with {sum(len(scripts) for scripts in SCRIPT_MAPPING.values())} scripts")

def get_script_info_by_question(question: str) -> Optional[Dict[str, Any]]:
    """Find script info based on question using fuzzy matching"""
    best_match = None
    best_match_score = 0
    question_lower = question.lower()
    
    # First, check for exact matches
    for ga_folder, scripts in SCRIPT_MAPPING.items():
        for script_name, script_info in scripts.items():
            for q_info in script_info["questions"]:
                q_text = q_info["text"]
                if q_text.lower() == question_lower:
                    logger.info(f"Found exact match for question in {ga_folder}/{script_name}")
                    return {
                        "ga_folder": ga_folder,
                        "script_name": script_name,
                        "script_path": script_info["path"],
                        "question": q_text,
                        "answer": q_info.get("answer", "")
                    }
    
    # Use keyword matching for partial matches
    for ga_folder, scripts in SCRIPT_MAPPING.items():
        for script_name, script_info in scripts.items():
            for q_info in script_info["questions"]:
                q_text = q_info["text"]
                # Calculate similarity score (basic contains check)
                score = 0
                
                # Contains match (weighted)
                if question_lower in q_text.lower() or q_text.lower() in question_lower:
                    score += 0.6
                
                # Keyword matching
                keywords = extract_keywords(question_lower)
                q_keywords = extract_keywords(q_text.lower())
                
                # Count matching keywords
                matching_keywords = sum(1 for kw in keywords if kw in q_keywords)
                keyword_score = matching_keywords / max(len(keywords), 1) * 0.4
                score += keyword_score
                
                if score > best_match_score:
                    best_match_score = score
                    best_match = {
                        "ga_folder": ga_folder,
                        "script_name": script_name,
                        "script_path": script_info["path"],
                        "question": q_text,
                        "answer": q_info.get("answer", ""),
                        "score": score
                    }
    
    # Special case matching
    if "code -s" in question_lower:
        # This is likely the VS Code output question (GA1/first.py)
        return {
            "ga_folder": "GA1",
            "script_name": "first",
            "script_path": "E://data science tool//GA1//first.py",
            "question": "What is the output of code -s?",
            "score": 0.9
        }
    
    elif "httpbin" in question_lower or "http request" in question_lower:
        # This is likely the HTTP request question (GA1/second.py)
        return {
            "ga_folder": "GA1",
            "script_name": "second",
            "script_path": "E://data science tool//GA1//second.py",
            "question": "Send a HTTPS request to httpbin.org/get with the URL encoded parameter email",
            "score": 0.9
        }
    
    elif ("how many" in question_lower and 
          any(day in question_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])):
        # This is likely the calendar counting question (GA1/seventh.py)
        return {
            "ga_folder": "GA1",
            "script_name": "seventh",
            "script_path": "E://data science tool//GA1//seventh.py",
            "question": "How many Wednesdays are there in the date range?",
            "score": 0.9
        }
    
    elif "physics marks" in question_lower and "maths" in question_lower:
        # This is likely the marks calculation question (GA4/ninth.py)
        return {
            "ga_folder": "GA4",
            "script_name": "ninth",
            "script_path": "E://data science tool//GA4//ninth.py",
            "question": "Calculate the total Physics marks of students who scored 69 or more marks in Maths",
            "score": 0.9
        }
    
    # Return the best match if it's good enough
    if best_match and best_match_score >= 0.6:
        logger.info(f"Found best match for question with score {best_match_score:.2f}: {best_match['ga_folder']}/{best_match['script_name']}")
        return best_match
    
    # If no good match, try to guess based on keywords
    for keyword, ga_script in [
        ("prettier", ("GA1", "third")),
        ("google sheets", ("GA1", "fourth")),
        ("npx", ("GA1", "third")),
        ("cricket", ("GA4", "first")),
        ("markdown", ("GA4", "tenth")),
        ("github", ("GA4", "eighth")),
        ("weather", ("GA4", "fourth")),
        ("sentiment", ("GA3", "first")),
        ("token", ("GA3", "second")),
        ("embedding", ("GA3", "fifth"))
    ]:
        if keyword in question_lower:
            ga_folder, script_name = ga_script
            script_info = SCRIPT_MAPPING[ga_folder][script_name]
            logger.info(f"Matched question by keyword '{keyword}' to {ga_folder}/{script_name}")
            return {
                "ga_folder": ga_folder,
                "script_name": script_name,
                "script_path": script_info["path"],
                "question": script_info["questions"][0]["text"] if script_info["questions"] else "Unknown question",
                "score": 0.7
            }
    
    logger.warning(f"No match found for question: {question[:50]}...")
    return None

def extract_keywords(text: str) -> List[str]:
    """Extract significant keywords from text for matching"""
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    
    # Stop words to filter out
    stop_words = {"the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of", 
                  "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", 
                  "has", "had", "do", "does", "did", "will", "would", "shall", "should", 
                  "can", "could", "may", "might", "must", "that", "this", "these", "those",
                  "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}
    
    # Filter words (remove stop words and short words)
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    return keywords

def extract_parameters(question: str, script_info: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parameters from the question based on script type"""
    params = {}
    question_lower = question.lower()
    
    # Extract parameters based on script type
    ga_folder = script_info["ga_folder"]
    script_name = script_info["script_name"]
    
    if ga_folder == "GA1" and script_name == "seventh":
        # Day counting script
        
        # Extract day of week if present
        day_match = re.search(r'how many (\w+)s', question_lower)
        if day_match:
            day = day_match.group(1).capitalize()
            params["day_of_week"] = day
        
        # Extract date range if present
        date_range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})', question)
        if date_range_match:
            params["start_date"] = date_range_match.group(1)
            params["end_date"] = date_range_match.group(2)
        
    elif ga_folder == "GA1" and script_name == "second":
        # HTTP request script
        
        # Extract email parameter if present
        email_match = re.search(r'email\s+(?:set\s+to\s+)?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', question_lower)
        if email_match:
            params["email"] = email_match.group(1)
        else:
            # Default email
            params["email"] = "24f2006438@ds.study.iitm.ac.in"
    
    elif ga_folder == "GA4" and script_name == "fourth":
        # Weather forecast script
        
        # Extract location if present
        location_match = re.search(r'weather\s+(?:in|for)\s+([A-Za-z\s]+)', question_lower)
        if location_match:
            params["location"] = location_match.group(1).strip()
        else:
            # Default location
            params["location"] = "Kathmandu"
    
    elif ga_folder == "GA4" and script_name == "fifth":
        # Bounding box script
        
        # Extract city and country
        location_match = re.search(r'bounding box for\s+([A-Za-z\s]+)(?:,|\s+in)\s+([A-Za-z\s]+)', question_lower)
        if location_match:
            params["city"] = location_match.group(1).strip()
            params["country"] = location_match.group(2).strip()
        else:
            # Default values
            params["city"] = "Bangalore"
            params["country"] = "India"
        
        # Extract parameter type
        param_match = re.search(r'(min_lat|max_lat|min_lon|max_lon)', question_lower)
        if param_match:
            params["parameter"] = param_match.group(1)
        else:
            params["parameter"] = "min_lat"
    
    # Add more parameter extraction rules for other scripts as needed
    
    logger.info(f"Extracted parameters: {params}")
    return params

def cleanup_temp_dir():
    """Clean up temporary files"""
    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
            TEMP_DIR.mkdir(exist_ok=True, parents=True)
            logger.info("Temporary directory cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}")

def find_script_path(script_path: str) -> Optional[Path]:
    """Find the actual script path, handling various path formats"""
    script_path = Path(script_path)
    
    # Check if path exists as is
    if script_path.exists():
        return script_path
    
    # Try with normalized path
    normalized_path = Path(str(script_path).replace("//", "/"))
    if normalized_path.exists():
        return normalized_path
    
    # Try alternative locations based on script name
    script_name = script_path.name
    
    # Parse script name to extract GA folder and script name
    ga_match = re.search(r'(GA\d+)[/\\]([a-zA-Z]+)\.py', str(script_path))
    if ga_match:
        ga_folder = ga_match.group(1)
        script_base = ga_match.group(2)
        
        # Try direct path
        alt_path = BASE_DIR / ga_folder / f"{script_base}.py"
        if alt_path.exists():
            return alt_path
    
    # Try all GA folders
    for ga_folder in ["GA1", "GA2", "GA3", "GA4"]:
        alt_path = BASE_DIR / ga_folder / script_name
        if alt_path.exists():
            return alt_path
    
    logger.error(f"Could not find script at {script_path}")
    return None

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

def run_script_with_import(script_path: str, params: Dict[str, Any] = None, file_content: BytesIO = None) -> str:
    """Run a script by importing it as a module"""
    try:
        # Find the actual script path
        actual_path = find_script_path(script_path)
        if not actual_path:
            return f"Error: Script not found at {script_path}"
        
        script_path = str(actual_path)
        logger.info(f"Running script via import: {script_path}")
        
        # Save file if provided
        file_path = None
        if file_content:
            file_path = os.path.join(TEMP_DIR, "uploaded_file")
            with open(file_path, "wb") as f:
                f.write(file_content.read() if hasattr(file_content, "read") else file_content.getvalue())
            logger.info(f"Saved uploaded file to {file_path}")
        
        # Import the script as a module
        spec = importlib.util.spec_from_file_location("dynamic_script", script_path)
        if not spec:
            return f"Error: Could not create spec for {script_path}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Capture stdout
        original_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = CapturedOutput(captured_output)
        
        result = None
        try:
            # Try different entry points in the module
            if hasattr(module, 'solve'):
                # Inspect the solve function to determine parameters
                sig = inspect.signature(module.solve)
                param_count = len(sig.parameters)
                
                if param_count == 0:
                    result = module.solve()
                elif param_count == 1:
                    result = module.solve(params)
                else:
                    result = module.solve(params, file_path)
                    
            elif hasattr(module, 'main'):
                # Try the main function
                sig = inspect.signature(module.main)
                param_count = len(sig.parameters)
                
                if param_count == 0:
                    result = module.main()
                elif param_count == 1:
                    result = module.main(params)
                else:
                    result = module.main(params, file_path)
                    
            else:
                # Try a function with the same name as the script
                script_name = os.path.splitext(os.path.basename(script_path))[0]
                if hasattr(module, script_name):
                    func = getattr(module, script_name)
                    sig = inspect.signature(func)
                    param_count = len(sig.parameters)
                    
                    if param_count == 0:
                        result = func()
                    elif param_count == 1:
                        result = func(params)
                    else:
                        result = func(params, file_path)
                else:
                    # If no specific function found, just execute the module
                    logger.info(f"No entry point function found in {script_path}")
        finally:
            # Restore stdout
            sys.stdout = original_stdout
        
        # Get captured output
        output = captured_output.getvalue()
        
        # Combine output and result
        if result is not None:
            if output:
                return f"{output}\n\nReturn value: {result}"
            else:
                return str(result)
        else:
            return output or "Script executed but produced no output"
        
    except Exception as e:
        logger.error(f"Error running script with import: {e}")
        return f"Error running script: {str(e)}\n{traceback.format_exc()}"

def execute_script(script_info: Dict[str, Any], params: Dict[str, Any] = None, file_content: BytesIO = None) -> str:
    """Execute the script using multiple methods and return the best result"""
    script_path = script_info["script_path"]
    
    # Try import method first
    try:
        logger.info(f"Trying import method for {script_path}")
        result = run_script_with_import(script_path, params, file_content)
        
        # Check if result indicates an error with import method
        if not result.startswith("Error"):
            return result
        
        logger.warning(f"Import method failed for {script_path}, trying subprocess method")
    except Exception as e:
        logger.error(f"Exception with import method: {e}")
    
    # If import fails or has an error, try subprocess method
    try:
        logger.info(f"Trying subprocess method for {script_path}")
        result = run_script_with_subprocess(script_path, params, file_content)
        return result
    except Exception as e:
        logger.error(f"Exception with subprocess method: {e}")
        return f"Error executing script: {str(e)}"

def process_question(question: str, file_content: BytesIO = None) -> str:
    """Process a question and execute the corresponding script"""
    try:
        # Find the script info for this question
        script_info = get_script_info_by_question(question)
        
        if not script_info:
            return "I couldn't find a matching script for your question. Could you please rephrase or provide more details?"
        
        # Extract parameters from the question
        params = extract_parameters(question, script_info)
        
        # Execute the script
        result = execute_script(script_info, params, file_content)
        
        # If we have a stored answer from training data and script execution failed
        if "Error" in result and script_info.get("answer"):
            logger.info(f"Using stored answer from training data")
            return script_info["answer"]
        
        return result
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        return f"Error processing your question: {str(e)}\n{traceback.format_exc()}"

@app.post("/api/solve")
async def solve_assignment(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """REST API endpoint for solving assignments"""
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

# Initialize script mapping on startup
@app.on_event("startup")
def startup_event():
    """Initialize data on application startup"""
    logger.info("Initializing application...")
    initialize_script_mapping()
    cleanup_temp_dir()

# Clean up on shutdown
@app.on_event("shutdown")
def shutdown_event():
    """Clean up on application shutdown"""
    logger.info("Shutting down application...")
    cleanup_temp_dir()

if __name__ == "__main__":
    import uvicorn
    
    # Initialize script mapping
    initialize_script_mapping()
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000)