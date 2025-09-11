from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import re
from typing import Optional
import os
import shutil
from io import BytesIO

app = FastAPI(
    title="Data Science Assignment Solver",
    description="API to solve IIT Madras Data Science graded assignments"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_temp_dir():
    """Clean up temporary files"""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

# Task Handlers
def run_command(command: str) -> str:
    """Execute a shell command and return its output"""
    try:
        return subprocess.check_output(command, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {str(e)}"
def question_2():
    '''Running uv run --with httpie -- https [URL] installs the Python package httpie and sends a HTTPS request to the URL.

Send a HTTPS request to https://httpbin.org/get with the URL encoded parameter email set to 24f2006438@ds.study.iitm.ac.in

What is the JSON output of the command? (Paste only the JSON body, not the headers)'''
    import requests
    import json
    def send_request(url, params):
        response = requests.get(url, params=params)
        print(json.dumps(response.json(), indent=4))

    url = "https://httpbin.org/get"
    params = {"email": "24f2006438@ds.study.iitm.ac.in"}
    send_request(url, params)
# Question Parser
def parse_question(question: str) -> dict:
    """Parse question to extract tasks and parameters"""
    question_lower = question.lower().replace('\n', ' ')  # Normalize newlines
    tasks = {}
    
    # Detect command execution task
    # Matches: "output of 'code -s'", "output of code -s", etc.
    command_match = re.search(r"output of\s+['\"]?(code\s+-s)['\"]?|type\s+(code\s+-s)\s+and\s+press\s+enter", question_lower)
    if command_match:
        # Extract the command from either group 1 or 2
        command = command_match.group(1) or command_match.group(2)
        if command:
            tasks["command"] = command.strip()
    
    # Add more patterns for other question types (e.g., unzip, replace) as needed
    return tasks

# Main Processing Logic
def process_question(question: str, file: BytesIO = None) -> str:
    """Process the question and return the answer"""
    tasks = parse_question(question)
    if not tasks:
        return "Unable to interpret question"
    
    # Handle command execution task
    if "command" in tasks:
        return run_command(tasks["command"])
    
    return "No supported task detected"

@app.post("/api/")
async def solve_assignment(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """API endpoint to solve assignment questions"""
    try:
        file_content = BytesIO(await file.read()) if file else None
        answer = process_question(question, file_content)
        cleanup_temp_dir()
        return {"answer": answer}
    except Exception as e:
        cleanup_temp_dir()
        return {"answer": f"Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)