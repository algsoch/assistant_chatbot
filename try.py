import json
import os
import subprocess
import sys
from pathlib import Path
from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from rapidfuzz import process, fuzz

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define base directory for the project
BASE_DIR = Path("E:/data science tool")
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Try to load the question mapping from different locations
def load_question_mappings():
    possible_paths = [
        BASE_DIR / "question_mapping.json",
        BASE_DIR / "main" / "question_mapping.json",
        Path("E:/data science tool/question_mapping.json"),
        Path("E:/data science tool/main/question_mapping.json")
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"Loading question mappings from {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "questions" in data:
                    return data["questions"]
                return data
    
    print("No question mapping file found!")
    return []

# Load question mappings
QUESTION_MAPPINGS = load_question_mappings()

# Extract just the questions for fuzzy matching
QUESTION_LIST = [q.get("question", "") for q in QUESTION_MAPPINGS if "question" in q]

print(f"Loaded {len(QUESTION_LIST)} questions for matching")

# Function to find the best matching question using fuzzy search
def find_matching_question(user_prompt):
    if not user_prompt or not QUESTION_LIST:
        return None
    
    # Check for direct matches first
    for i, question in enumerate(QUESTION_LIST):
        if user_prompt.lower() == question.lower():
            print(f"Found exact match: {question[:50]}...")
            return QUESTION_MAPPINGS[i]
    
    # Try fuzzy matching
    try:
        matched_question, score, index = process.extractOne(
            user_prompt, QUESTION_LIST, scorer=fuzz.ratio
        )
        print(f"Best match: '{matched_question[:50]}...' with score {score}")
        
        if score >= 80:  # Only accept high-confidence matches
            return QUESTION_MAPPINGS[index]
    except Exception as e:
        print(f"Error during fuzzy matching: {e}")
    
    # Try keyword-based matching as fallback
    keywords = user_prompt.lower().split()
    best_match = None
    best_score = 0
    
    for i, question in enumerate(QUESTION_LIST):
        q_lower = question.lower()
        matches = sum(1 for keyword in keywords if keyword in q_lower and len(keyword) > 3)
        score = matches / max(len(keywords), 1)
        
        if score > best_score:
            best_score = score
            best_match = i
    
    if best_score >= 0.5 and best_match is not None:
        print(f"Keyword match with score {best_score}: {QUESTION_LIST[best_match][:50]}...")
        return QUESTION_MAPPINGS[best_match]
    
    return None

# Function to execute the mapped script
def run_script(script_path, file_path=None):
    script_path = Path(script_path)
    
    if not script_path.exists():
        # Try to find script with fixed path
        corrected_path = str(script_path).replace("//", "/")
        corrected_script = Path(corrected_path)
        
        if corrected_script.exists():
            script_path = corrected_script
        else:
            # Try to find in GA folders
            script_name = script_path.name
            possible_locations = [
                BASE_DIR / "GA1" / script_name,
                BASE_DIR / "GA2" / script_name,
                BASE_DIR / "GA3" / script_name,
                BASE_DIR / "GA4" / script_name
            ]
            
            for loc in possible_locations:
                if loc.exists():
                    script_path = loc
                    print(f"Found script at: {script_path}")
                    break
            else:
                return {"error": f"Script {script_path} not found. Tried paths: {possible_locations}"}

    try:
        print(f"Executing script: {script_path}")
        
        # Add the script's directory to the Python path
        script_dir = str(script_path.parent)
        if script_dir not in sys.path:
            sys.path.append(script_dir)
        
        # Build the command
        command = [sys.executable, str(script_path)]
        if file_path:
            command.append(str(file_path))  # Pass file if required

        # Run the script
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        
        # Check for errors
        if result.stderr:
            print(f"Script execution error: {result.stderr}")
            
        return {
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr.strip() else None
        }
    except subprocess.TimeoutExpired:
        return {"error": "Script execution timed out after 30 seconds", "output": ""}
    except Exception as e:
        print(f"Exception during script execution: {e}")
        return {"error": str(e), "output": ""}

@app.post("/api/")
async def execute_question(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    print(f"Received question: {question[:100]}...")
    matched_data = find_matching_question(question)

    if not matched_data:
        return JSONResponse(
            status_code=404,
            content={"error": "No matching question found", "question": question}
        )

    script_path = matched_data["mapped_script"]
    file_path = None

    if file:
        # Save uploaded file
        file_path = UPLOADS_DIR / file.filename
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        print(f"Saved uploaded file to {file_path}")

    # Execute the script
    execution_result = run_script(script_path, file_path)
    
    # If there was an error, return it with a 500 status
    if "error" in execution_result and execution_result["error"]:
        return JSONResponse(
            status_code=500,
            content={
                "error": execution_result["error"],
                "question": question,
                "script": script_path
            }
        )
    
    # Format the response
    return {
        "question": matched_data.get("question", ""),
        "script": script_path,
        "output": execution_result.get("output", ""),
        "error": execution_result.get("error", None)
    }

# Simple web interface
templates = Jinja2Templates(directory=str(BASE_DIR / "main" / "templates"))

@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    # Create templates directory if it doesn't exist
    templates_dir = BASE_DIR / "main" / "templates"
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Create index.html if it doesn't exist
    index_html = templates_dir / "index.html"
    if not index_html.exists():
        with open(index_html, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Query Execution System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        form {
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
        }
        textarea {
            width: 100%;
            height: 100px;
            padding: 10px;
            margin-bottom: 10px;
            font-family: Arial, sans-serif;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        #result {
            margin-top: 20px;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 5px;
            white-space: pre-wrap;
        }
        .hidden {
            display: none;
        }
        .examples {
            margin-top: 20px;
        }
        .example-item {
            cursor: pointer;
            padding: 10px;
            margin: 5px 0;
            background-color: #f0f0f0;
            border-radius: 4px;
        }
        .example-item:hover {
            background-color: #e0e0e0;
        }
    </style>
</head>
<body>
    <h1>Query Execution System</h1>
    
    <form id="query-form">
        <div>
            <label for="question">Enter your question:</label>
            <textarea id="question" name="question" required></textarea>
        </div>
        
        <div>
            <label for="file">Upload a file (optional):</label>
            <input type="file" id="file" name="file">
        </div>
        
        <button type="submit">Execute</button>
    </form>
    
    <div id="result" class="hidden"></div>
    
    <div class="examples">
        <h3>Example Questions:</h3>
        <div class="example-item" onclick="setQuestion('What is the output of code -s?')">
            What is the output of code -s?
        </div>
        <div class="example-item" onclick="setQuestion('Send a HTTPS request to https://httpbin.org/get with the URL encoded parameter email set to 24f2006438@ds.study.iitm.ac.in')">
            Send a HTTPS request to httpbin.org/get
        </div>
        <div class="example-item" onclick="setQuestion('Calculate the total Physics marks of students who scored 69 or more marks in Maths in groups 1-25')">
            Calculate total Physics marks from PDF
        </div>
    </div>
    
    <script>
        document.getElementById('query-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const question = document.getElementById('question').value;
            const fileInput = document.getElementById('file');
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = 'Processing...';
            resultDiv.classList.remove('hidden');
            
            const formData = new FormData();
            formData.append('question', question);
            
            if (fileInput.files.length > 0) {
                formData.append('file', fileInput.files[0]);
            }
            
            try {
                const response = await fetch('/api/', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    resultDiv.innerHTML = `<h3>Result:</h3><pre>${data.output}</pre>`;
                    if (data.error) {
                        resultDiv.innerHTML += `<h3>Errors:</h3><pre style="color: red;">${data.error}</pre>`;
                    }
                } else {
                    resultDiv.innerHTML = `<h3>Error:</h3><pre style="color: red;">${data.error || 'Unknown error'}</pre>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<h3>Error:</h3><pre style="color: red;">Request failed: ${error.message}</pre>`;
            }
        });
        
        function setQuestion(text) {
            document.getElementById('question').value = text;
        }
    </script>
</body>
</html>""")
    
    return templates.TemplateResponse("index.html", {"request": request})

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": f"An unexpected error occurred: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server with {len(QUESTION_MAPPINGS)} question mappings")
    uvicorn.run(app, host="127.0.0.1", port=8000)
