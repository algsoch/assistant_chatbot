from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import re
import json
import importlib.util
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Question Execution API",
    description="API for executing questions from questions.py",
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

class QuestionRequest(BaseModel):
    question: str
    parameters: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, str]] = None

class QuestionResponse(BaseModel):
    question: str
    matched_function: Optional[str]
    parameters: Optional[Dict[str, Any]]
    result: Optional[Any]
    error: Optional[str]

def extract_function_info(content: str, question: str) -> Optional[Dict[str, Any]]:
    """Extract function information based on the question."""
    lines = content.split('\n')
    current_question = None
    current_params = None
    current_function = None
    functions_info = []

    for i, line in enumerate(lines):
        line = line.strip()
        
        # Look for question definitions
        if line.startswith('question') and '=' in line:
            current_question = eval(line.split('=', 1)[1].strip())
            continue
            
        # Look for parameter definitions
        if line.startswith('parameter') and '=' in line:
            current_params = eval(line.split('=', 1)[1].strip())
            continue
            
        # Look for function definitions
        if line.startswith('def '):
            function_name = line[4:line.find('(')].strip()
            if current_question:
                functions_info.append({
                    'question': current_question,
                    'parameters': current_params,
                    'function': function_name,
                    'line_number': i + 1
                })
                current_question = None
                current_params = None

    # Find best matching question using fuzzy matching
    best_match = None
    best_score = 0
    
    for info in functions_info:
        # Simple word matching score
        q_words = set(question.lower().split())
        info_words = set(info['question'].lower().split())
        common_words = q_words & info_words
        score = len(common_words) / max(len(q_words), len(info_words))
        
        if score > best_score:
            best_score = score
            best_match = info

    if best_score >= 0.5:  # Threshold for accepting a match
        return best_match
    return None

def load_and_execute_function(function_name: str, module_path: str, parameters: Dict[str, Any] = None) -> Any:
    """Load and execute a function from the questions.py module."""
    try:
        # Import the module
        spec = importlib.util.spec_from_file_location("questions", module_path)
        if not spec or not spec.loader:
            raise ImportError("Could not load questions.py")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules["questions"] = module
        spec.loader.exec_module(module)
        
        # Get the function
        func = getattr(module, function_name)
        
        # Execute the function with parameters if provided
        if parameters:
            result = func(**parameters)
        else:
            result = func()
            
        return result
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing function: {str(e)}")

@app.post("/execute", response_model=QuestionResponse)
async def execute_question(request: QuestionRequest):
    """Execute a question from questions.py"""
    try:
        # Get the questions.py content
        questions_path = Path("questions.py")
        if not questions_path.exists():
            raise HTTPException(status_code=404, detail="questions.py not found")
            
        content = questions_path.read_text(encoding='utf-8')
        
        # Extract function info based on the question
        function_info = extract_function_info(content, request.question)
        if not function_info:
            return QuestionResponse(
                question=request.question,
                matched_function=None,
                parameters=None,
                result=None,
                error="No matching function found for the question"
            )
            
        # Execute the function
        parameters = request.parameters if request.parameters else {}
        result = load_and_execute_function(
            function_info['function'],
            str(questions_path),
            parameters
        )
        
        return QuestionResponse(
            question=request.question,
            matched_function=function_info['function'],
            parameters=parameters,
            result=result,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        return QuestionResponse(
            question=request.question,
            matched_function=None,
            parameters=None,
            result=None,
            error=str(e)
        )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file uploads for questions that require files"""
    try:
        # Create uploads directory if it doesn't exist
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        # Save the file
        file_path = uploads_dir / file.filename
        with file_path.open("wb") as f:
            content = await file.read()
            f.write(content)
            
        return {"filename": file.filename, "path": str(file_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "name": "Question Execution API",
        "version": "1.0.0",
        "description": "API for executing questions from questions.py",
        "endpoints": {
            "/execute": "POST - Execute a question",
            "/upload": "POST - Upload a file for questions that need it"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001) 