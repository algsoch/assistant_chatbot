import json
import os
import subprocess
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="Query Execution System API")

# Define the base directory for scripts
BASE_DIR = Path("E:/data science tool")  # Changed to correct base directory

# Create a default question mapping if it doesn't exist
def ensure_question_mapping_exists():
    mapping_path = BASE_DIR / "main" / "question_mapping.json"
    
    if not mapping_path.exists():
        print('not')
        print(f"Creating new question mapping at {mapping_path}")
        default_mapping = {
            "questions": [
                {
                    "question": "What is the output of code -s?",
                    "mapped_script": str(BASE_DIR / "GA1/first.py"),
                    "keywords": ["code -s", "output", "terminal", "command"]
                },
                {
                    "question": "Send a HTTPS request to https://httpbin.org/get",
                    "mapped_script": str(BASE_DIR / "GA1/second.py"),
                    "keywords": ["httpbin", "http", "https", "request", "api"]
                },
                {
                    "question": "Sort this JSON array of objects by age.",
                    "mapped_script": str(BASE_DIR / "GA1/ninth.py"),
                    "keywords": ["json", "sort", "array", "objects", "age"]
                },
                {
                    "question": "Extract tables from a PDF file.",
                    "mapped_script": str(BASE_DIR / "GA4/ninth.py"),
                    "keywords": ["pdf", "table", "extract", "csv"]
                },
                {
                    "question": "Calculate the total Physics marks of students who scored 69 or more marks in Maths in groups 1-25 (including both groups)",
                    "mapped_script": str(BASE_DIR / "GA4/ninth.py"),
                    "keywords": ["physics", "marks", "maths", "students", "groups", "pdf", "total"]
                }
            ]
        }
        
        # Ensure parent directory exists
        mapping_path.parent.mkdir(exist_ok=True)
        
        # Write the default mapping
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(default_mapping, f, indent=2)
        
        print(f"Created default question mapping at {mapping_path}")

# Load the question-to-script mapping
def load_question_mappings() -> List[Dict[str, Any]]:
    try:
        # Try multiple possible locations
        possible_paths = [
            BASE_DIR / "main" / "question_mapping.json",
            BASE_DIR / "question_mapping.json",
            Path("E:/data science tool/question_mapping.json"),
            Path("E:/data science tool/main/question_mapping.json")
        ]
        
        for mapping_path in possible_paths:
            if mapping_path.exists():
                print(f"Loading question mappings from {mapping_path}")
                with open(mapping_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "questions" in data:
                        return data["questions"]
                    return data
        
        # If no mapping file found, create default
        ensure_question_mapping_exists()
        mapping_path = BASE_DIR / "main" / "question_mapping.json"
        
        with open(mapping_path, "r", encoding="utf-8") as f:
            return json.load(f)["questions"]
    except Exception as e:
        print(f"Error loading question mappings: {e}")
        return []

# Calculate similarity between two strings
def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Function to find the best matching question using keyword matching and string similarity
def find_matching_question(user_prompt: str) -> Optional[Dict[str, Any]]:
    print(f"Finding match for: {user_prompt[:100]}...")
    
    # Clean the prompt
    clean_prompt = user_prompt.lower()
    
    # Check for direct keywords related to specific tasks
    
    # Physics marks question (direct check)
    if any(keyword in clean_prompt for keyword in ["physics marks", "maths", "groups 1-25"]):
        for q in QUESTION_MAPPINGS:
            if "physics" in q.get("question", "").lower() and "maths" in q.get("question", "").lower():
                print(f"Keyword match found for Physics marks question")
                return q
    
    # VS Code output question
    if "code -s" in clean_prompt or ("output" in clean_prompt and "code" in clean_prompt):
        for q in QUESTION_MAPPINGS:
            if "code -s" in q.get("question", "").lower():
                print(f"Keyword match found for VS Code question")
                return q
    
    # PDF extraction question
    if "extract" in clean_prompt and "pdf" in clean_prompt:
        for q in QUESTION_MAPPINGS:
            if "extract" in q.get("question", "").lower() and "pdf" in q.get("question", "").lower():
                print(f"Keyword match found for PDF extraction")
                return q
    
    # HTTPS request question
    if "https" in clean_prompt and "request" in clean_prompt:
        for q in QUESTION_MAPPINGS:
            if "https" in q.get("question", "").lower() and "request" in q.get("question", "").lower():
                print(f"Keyword match found for HTTPS request")
                return q
    
    # Keyword matching
    best_keyword_match = None
    best_keyword_score = 0
    
    for q in QUESTION_MAPPINGS:
        keywords = q.get("keywords", [])
        if not keywords and "question" in q:
            # Generate keywords from the question if not provided
            question_words = q["question"].lower().split()
            keywords = [word for word in question_words if len(word) > 3]
        
        # Count matching keywords
        matching_keywords = sum(1 for keyword in keywords if keyword.lower() in clean_prompt)
        keyword_score = matching_keywords / max(len(keywords), 1) if keywords else 0
        
        if keyword_score > best_keyword_score:
            best_keyword_score = keyword_score
            best_keyword_match = q
    
    # If we have a good keyword match (at least 30% of keywords match)
    if best_keyword_score >= 0.3:
        print(f"Found keyword match with score {best_keyword_score:.2f}")
        return best_keyword_match
    
    # String similarity matching as fallback
    best_match = None
    best_score = 0
    
    for q in QUESTION_MAPPINGS:
        if "question" not in q:
            continue
            
        question = q["question"]
        score = similarity(user_prompt, question)
        
        if score > best_score:
            best_score = score
            best_match = q
    
    # Only return if the similarity is reasonable (over 0.5 or 50% similar)
    if best_score >= 0.5:
        print(f"Found string similarity match with score {best_score:.2f}")
        return best_match
    
    print("No good match found")
    return None

# Function to execute the mapped script
def run_script(script_path: str) -> Dict[str, Any]:
    script_path = Path(script_path)
    
    if not script_path.exists():
        # Try to find the script in different locations
        possible_paths = [
            BASE_DIR / script_path.name,
            BASE_DIR / "GA1" / script_path.name,
            BASE_DIR / "GA4" / script_path.name
        ]
        
        for path in possible_paths:
            if path.exists():
                script_path = path
                print(f"Found script at: {script_path}")
                break
        else:
            return {"error": f"Script {script_path} not found", "output": ""}

    try:
        # Check if the directory containing the script exists in sys.path
        script_dir = str(script_path.parent)
        if script_dir not in sys.path:
            sys.path.append(script_dir)
        
        print(f"Executing script: {script_path}")
        
        # Run the script using subprocess
        command = [sys.executable, str(script_path)]
        result = subprocess.run(command, text=True, capture_output=True)
        
        # If there was an error, print it for debugging
        if result.stderr:
            print(f"Script error: {result.stderr}")
        
        return {
            "output": result.stdout.strip(), 
            "error": result.stderr.strip() if result.stderr.strip() else None
        }
    except Exception as e:
        print(f"Exception during script execution: {e}")
        return {"error": str(e), "output": ""}

@app.post("/ask", response_model=Dict[str, Any])
async def execute_question(user_prompt: str = Form(...)):
    matched_data = find_matching_question(user_prompt)

    if not matched_data:
        return JSONResponse(
            status_code=404,
            content={"error": "No matching question found for your prompt"}
        )

    script_path = matched_data["mapped_script"]
    execution_result = run_script(script_path)
    
    # Format the output for better readability
    formatted_output = format_output(execution_result["output"])
    
    return {
        "question": matched_data.get("question", ""),
        "execution_result": {
            "formatted_output": formatted_output,
            "original_output": execution_result["output"],
            "error": execution_result["error"]
        }
    }

def format_output(output: str) -> Dict[str, Any]:
    """Format command output into a structured, readable format"""
    if not output:
        return {"message": "No output generated"}
    
    # For Physics marks output specifically
    if "Total Physics marks" in output and "Analysis Results" in output:
        # Try to extract the result
        match = re.search(r'Total Physics marks: (\d+)', output)
        if match:
            total_marks = match.group(1)
            return {
                "total_physics_marks": total_marks,
                "full_output": output
            }
    
    # For VS Code stats output specifically
    if "Version:" in output and "Code " in output:
        # Parse VS Code output
        result = {}
        
        # Extract main sections
        lines = output.split('\n')
        system_info = {}
        gpu_status = {}
        processes = []
        workspace_stats = []
        
        current_section = "system_info"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section changes
            if "GPU Status:" in line:
                current_section = "gpu_status"
                continue
            elif "CPU %" in line:
                current_section = "processes"
                continue
            elif "Workspace Stats:" in line:
                current_section = "workspace_stats"
                continue
                
            # Process based on current section
            if current_section == "system_info":
                if ":" in line:
                    key, value = line.split(":", 1)
                    system_info[key.strip()] = value.strip()
            elif current_section == "gpu_status":
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        gpu_status[key] = value
            elif current_section == "processes":
                processes.append(line)
            elif current_section == "workspace_stats":
                workspace_stats.append(line)
        
        return {
            "vs_code_info": {
                "system": system_info,
                "gpu_status": gpu_status,
                "processes": processes[1:] if len(processes) > 1 else [],  # Skip header
                "workspace": workspace_stats
            }
        }
    
    # For general HTTP request responses (likely JSON)
    elif output.strip().startswith('{') and output.strip().endswith('}'):
        try:
            # Try to parse as JSON
            return {"json_response": json.loads(output)}
        except:
            pass
    
    # For general command output, split by sections
    sections = []
    current_section = []
    
    for line in output.split('\n'):
        if not line.strip() and current_section:
            sections.append('\n'.join(current_section))
            current_section = []
        else:
            current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    if len(sections) == 1:
        return {"text": output}
    else:
        return {"sections": sections}

# For direct testing
@app.get("/")
async def root():
    return {"message": "Query Execution System API is running"}

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": f"An unexpected error occurred: {str(exc)}"}
    )

# Add this after creating the app
templates = Jinja2Templates(directory="templates")

# Add a new endpoint for HTML response
@app.get("/web", response_class=HTMLResponse)
async def web_interface(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/web/ask", response_class=HTMLResponse)
async def web_execute_question(request: Request, user_prompt: str = Form(...)):
    matched_data = find_matching_question(user_prompt)

    if not matched_data:
        return templates.TemplateResponse(
            "result.html", 
            {
                "request": request, 
                "error": "No matching question found for your prompt",
                "prompt": user_prompt
            }
        )

    script_path = matched_data["mapped_script"]
    execution_result = run_script(script_path)
    
    # Format the output for better readability
    formatted_output = format_output(execution_result["output"])
    
    return templates.TemplateResponse(
        "result.html", 
        {
            "request": request,
            "prompt": user_prompt,
            "question": matched_data.get("question", ""),
            "output": execution_result["output"],
            "formatted_output": formatted_output,
            "error": execution_result["error"]
        }
    )

# Load question mappings
QUESTION_MAPPINGS = load_question_mappings()

if __name__ == "__main__":
    import uvicorn
    ensure_question_mapping_exists()
    uvicorn.run(app, host="127.0.0.1", port=8000)