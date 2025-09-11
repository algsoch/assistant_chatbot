"""
Server script that serves a web interface for asking questions and running scripts
"""

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sys
import os
import re
import inspect
import importlib.util
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str
    parameters: Optional[Dict[str, Any]] = None

app = FastAPI(
    title="Question Execution System",
    description="System for executing questions through a web interface",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates and static files
templates_dir = Path("E:/data science tool/main/grok/templates")
static_dir = Path("E:/data science tool/main/grok/static")

templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Path to the vickys.json file with questions
QUESTION_FILE = Path("E:/data science tool/main/grok/vickys.json")

# Dictionary to store the questions and their scripts
QUESTIONS = []
QUESTIONS_MAP = {}  # Maps question text to file path

def load_questions_from_json():
    """Load questions from the JSON file"""
    if not QUESTION_FILE.exists():
        print(f"Warning: {QUESTION_FILE} not found")
        return
    
    try:
        # Read the JSON file
        with open(QUESTION_FILE, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # Store the questions
        QUESTIONS.extend(questions)
        
        # Create a map for easier lookup
        for idx, q in enumerate(questions):
            # Add full question text
            QUESTIONS_MAP[q['question'].lower()] = q['file']
            
            # Add shortened versions for partial matches
            words = q['question'].lower().split()
            if len(words) > 5:
                # Map first 5 words
                QUESTIONS_MAP[' '.join(words[:5])] = q['file']
                # Map last 5 words
                QUESTIONS_MAP[' '.join(words[-5:])] = q['file']
        
        print(f"Loaded {len(QUESTIONS)} questions from JSON file")
    except Exception as e:
        print(f"Error loading questions from JSON: {str(e)}")

# Load the questions
load_questions_from_json()

def check_file_exists(file_path):
    """Check if a file exists, converting from comment format if needed"""
    # If file path has double slashes, convert to proper path
    file_path = file_path.replace('//', '/')
    
    # If path starts with E:/, convert to normal Windows path
    if file_path.startswith('E:/'):
        file_path = os.path.normpath(file_path)
    
    # If file path has E: prefix, try without it too
    if file_path.startswith('E:'):
        alt_path = file_path[2:]  # Remove E: prefix
        if os.path.exists(alt_path):
            return alt_path
    
    # Check if the file exists
    if os.path.exists(file_path):
        return file_path
    
    return None

def run_script(file_path, parameter=None):
    """Run the script at the given file path"""
    # Check if the file exists
    actual_path = check_file_exists(file_path)
    
    try:
        # Create a script file with the code
        script_dir = "E:/data science tool/temp_scripts"
        os.makedirs(script_dir, exist_ok=True)
        
        script_name = os.path.basename(file_path) if actual_path else f"script_{hash(file_path)}.py"
        script_path = os.path.join(script_dir, script_name)
        
        # Find the matching question
        matching_question = None
        for q in QUESTIONS:
            if q['file'] == file_path:
                matching_question = q
                break
        
        if not matching_question:
            return f"Error: No question found for path {file_path}"
        
        # Create a basic script that just returns the question for now
        # In a real scenario, you would extract actual code from question.py or elsewhere
        with open(script_path, 'w') as f:
            # Add a simple script that returns information about the question
            f.write(f'''
import json
import subprocess

# Question information
file_path = "{file_path}"
question = """{matching_question['question']}"""

# For this demo, we'll just execute 'code -s' if that's what was asked
if "code -s" in question.lower():
    try:
        result = subprocess.run('code -s', shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
    except Exception as e:
        output = f"Error executing command: {{str(e)}}"
else:
    # For other questions, just return a placeholder
    output = f"This would run the script for: {{question}}"

# Print the result as JSON
print(json.dumps(output))
''')
        
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(script_path)  # Run in the script directory
        )
        
        # Process the output
        if result.returncode == 0:
            output = result.stdout.strip()
            try:
                # Try to parse as JSON
                return json.loads(output)
            except:
                # Return as plain text
                return output
        else:
            return f"Error running script: {result.stderr}"
            
    except Exception as e:
        return f"Error executing script: {str(e)}"

# Dictionary of additional keywords for matching
QUESTION_KEYWORDS = {
    "code -s": "E://data science tool//GA1//first.py",
    "output of code -s": "E://data science tool//GA1//first.py",
    "what is the output of code -s": "E://data science tool//GA1//first.py",
    "visual studio code": "E://data science tool//GA1//first.py",
    "https request to httpbin": "E://data science tool//GA1//second.py",
    "send a https request": "E://data science tool//GA1//second.py",
    "email set to 24f2006438@ds.study.iitm.ac.in": "E://data science tool//GA1//second.py",
    "npx prettier": "E://data science tool//GA1//third.py",
    "sha256sum": "E://data science tool//GA1//third.py",
    "google sheets": "E://data science tool//GA1//fourth.py",
    "sum array_constrain": "E://data science tool//GA1//fourth.py",
    "sequence(100, 100, 12, 10)": "E://data science tool//GA1//fourth.py",
    "array_constrain": "E://data science tool//GA1//fourth.py",
    "calculate the result": "E://data science tool//GA1//fourth.py",
    "excel formula": "E://data science tool//GA1//fifth.py",
    "sortby": "E://data science tool//GA1//fifth.py",
    "take": "E://data science tool//GA1//fifth.py",
    "wednesdays": "E://data science tool//GA1//seventh.py",
    "date range": "E://data science tool//GA1//seventh.py",
    "how many wednesdays": "E://data science tool//GA1//seventh.py",
    "how many sundays": "E://data science tool//GA1//seventh.py",
    "how many mondays": "E://data science tool//GA1//seventh.py",
    "how many tuesdays": "E://data science tool//GA1//seventh.py",
    "how many thursdays": "E://data science tool//GA1//seventh.py",
    "how many fridays": "E://data science tool//GA1//seventh.py",
    "how many saturdays": "E://data science tool//GA1//seventh.py",
    "count days": "E://data science tool//GA1//seventh.py",
    "zip file": "E://data science tool//GA1//eighth.py",
    "extract csv": "E://data science tool//GA1//eighth.py",
    "sort json": "E://data science tool//GA1//ninth.py",
    "key value pairs": "E://data science tool//GA1//tenth.py",
    "json object": "E://data science tool//GA1//tenth.py"
}

def match_question_to_file(question: str) -> Optional[str]:
    """
    Match a natural language question to the appropriate file path.
    
    Args:
        question: The natural language question
        
    Returns:
        The file path for the script that answers the question, or None if no match found
    """
    if not question:
        return None
    
    # Normalize the question: lowercase, strip punctuation
    question = question.lower().strip()
    question = re.sub(r'[^\w\s]', '', question)
    
    # First try exact matches with questions
    for orig_question, file_path in QUESTIONS_MAP.items():
        normalized_orig = re.sub(r'[^\w\s]', '', orig_question.lower())
        if question == normalized_orig:
            return file_path
    
    # Then try partial matches - check if question is contained in the original
    for orig_question, file_path in QUESTIONS_MAP.items():
        normalized_orig = re.sub(r'[^\w\s]', '', orig_question.lower())
        if question in normalized_orig or normalized_orig in question:
            return file_path
    
    # Check if the question contains function keywords
    for keyword, file_path in QUESTION_KEYWORDS.items():
        if keyword.lower() in question:
            return file_path
    
    # For partial questions, try to find the most relevant function
    best_match = None
    max_score = 0
    
    # Try partial matching with original questions
    for question_obj in QUESTIONS:
        orig_question = question_obj['question'].lower()
        
        # Skip very short questions to avoid false matches
        if len(orig_question) < 15:
            continue
            
        # Split questions into words
        q_words = set(question.split())
        orig_words = set(orig_question.split())
        
        # Calculate overlap score
        common_words = q_words.intersection(orig_words)
        score = len(common_words) / max(len(q_words), 1)
        
        if score > max_score and score > 0.2:  # Require at least 20% match
            max_score = score
            best_match = question_obj['file']
    
    # Special case handling for known questions with tricky wording
    if "code -s" in question or "output of code" in question:
        return "E://data science tool//GA1//first.py"  # First question
    
    if "excel" in question or "formula" in question or "calculate" in question:
        if "sequence" in question or "array_constrain" in question:
            return "E://data science tool//GA1//fourth.py"
        if "sortby" in question or "take" in question:
            return "E://data science tool//GA1//fifth.py"
    
    return best_match

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page with a form to ask questions"""
    try:
        # Log current dir and template dir
        print(f"Current directory: {os.getcwd()}")
        print(f"Templates directory: {templates_dir}")
        
        # Create a simple HTML page instead of using templates
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Question Answering System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .question-form {
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
        }
        textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            min-height: 100px;
            margin-bottom: 15px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        .answer {
            background-color: #e9f7ef;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
            white-space: pre-wrap;
        }
        .examples {
            margin-top: 40px;
        }
        .example {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
            cursor: pointer;
        }
        .example:hover {
            background-color: #efefef;
        }
    </style>
</head>
<body>
    <h1>Question Answering System</h1>
    
    <div class="question-form">
        <form id="question-form">
            <label for="question">Ask a Question:</label>
            <textarea id="question" name="question" placeholder="Type your question here..."></textarea>
            <button type="submit">Ask</button>
        </form>
    </div>
    
    <div id="answer-container" class="answer" style="display: none;">
        <h3>Answer:</h3>
        <div id="answer-content"></div>
    </div>
    
    <div class="examples">
        <h3>Example Questions:</h3>
        <div class="example">What is the output of code -s?</div>
        <div class="example">How many Wednesdays are there in the date range 1981-03-03 to 2012-12-30?</div>
        <div class="example">Calculate the result of =SUM(ARRAY_CONSTRAIN(SEQUENCE(100, 100, 12, 10), 1, 10))</div>
    </div>
    
    <script>
        // Add click handlers to examples
        document.querySelectorAll('.example').forEach(example => {
            example.addEventListener('click', function() {
                document.getElementById('question').value = this.textContent;
            });
        });
        
        // Add submit handler
        document.getElementById('question-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const question = document.getElementById('question').value;
            
            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        'question': question
                    })
                });
                
                const result = await response.json();
                
                // Display the answer
                document.getElementById('answer-container').style.display = 'block';
                document.getElementById('answer-content').textContent = result.answer;
                
                // Scroll to the answer
                document.getElementById('answer-container').scrollIntoView({
                    behavior: 'smooth'
                });
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while fetching the answer.');
            }
        });
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html)
    except Exception as e:
        print(f"Error in home route: {str(e)}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>")

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    """Process a question submitted through the form"""
    # Match the question to a file path
    file_path = match_question_to_file(question)
    
    if not file_path:
        return {
            "answer": f"Sorry, I couldn't find a matching script for your question: {question}"
        }
    
    # Run the script
    result = run_script(file_path)
    
    return {
        "answer": result
    }

@app.post("/api/question")
async def execute_question(request: QuestionRequest):
    """API endpoint to execute a script based on a natural language question"""
    # Match the question to a file path
    file_path = match_question_to_file(request.question)
    
    if not file_path:
        return JSONResponse(
            status_code=404,
            content={"error": f"No matching script found for question: {request.question}"}
        )
    
    # Run the script
    try:
        result = run_script(file_path, request.parameters)
        return {"result": result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error executing script: {str(e)}"}
        )

@app.get("/api/question")
async def execute_question_get(q: str, parameter: Optional[str] = None):
    """API endpoint to execute a script based on a natural language question (GET method)"""
    # Match the question to a file path
    file_path = match_question_to_file(q)
    
    if not file_path:
        # Try to provide a helpful error message
        return JSONResponse(
            status_code=404,
            content={
                "error": f"No matching script found for question: {q}",
                "suggestion": "Try one of the example questions from the home page."
            }
        )
    
    # Run the script
    try:
        result = run_script(file_path, parameter)
        return {"result": result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error executing script: {str(e)}"}
        )

@app.get("/api/questions")
async def get_questions():
    """Get all available questions"""
    # Format questions for API
    questions_list = []
    for q in QUESTIONS:
        # Shorten long questions for display
        question_text = q['question']
        if len(question_text) > 100:
            question_text = question_text[:97] + "..."
            
        questions_list.append({
            "file": q['file'],
            "question": question_text
        })
    
    return {
        "count": len(questions_list),
        "questions": questions_list
    }

@app.get("/api/help")
async def get_help():
    """Provides help information about how to use the API with examples"""
    return {
        "name": "Question Execution System",
        "version": "1.0.0",
        "description": "API for executing scripts based on natural language questions",
        "endpoints": [
            {
                "path": "/",
                "method": "GET",
                "description": "Web interface for asking questions"
            },
            {
                "path": "/ask",
                "method": "POST",
                "description": "Form submission endpoint for asking questions"
            },
            {
                "path": "/api/question",
                "method": "POST",
                "description": "API endpoint for executing scripts based on natural language questions"
            },
            {
                "path": "/api/question",
                "method": "GET", 
                "description": "API endpoint for executing scripts based on natural language questions (GET method)"
            },
            {
                "path": "/api/questions",
                "method": "GET",
                "description": "API endpoint for getting all available questions"
            },
            {
                "path": "/api/help",
                "method": "GET",
                "description": "API endpoint for getting help information"
            }
        ],
        "examples": [
            {
                "description": "Ask a question using the web interface",
                "url": "/"
            },
            {
                "description": "Ask a question using the API (GET)",
                "url": "/api/question?q=What is the output of code -s?"
            },
            {
                "description": "Ask a question using the API (POST)",
                "url": "/api/question",
                "body": {
                    "question": "What is the output of code -s?",
                    "parameters": {}
                }
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting server on port 8090...")
    uvicorn.run(app, host="127.0.0.1", port=8090) 