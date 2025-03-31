import json
import os
import sys
import unittest
import requests
from fastapi import FastAPI, Form, HTTPException
from fastapi.testclient import TestClient
from pathlib import Path
import traceback
import logging
from typing import Dict, List, Any, Optional
from io import StringIO
import uvicorn

import importlib.util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-question")

# Initialize FastAPI app
app = FastAPI(title="Assignment Solver Test API")

# Path to the question.py file
QUESTION_PATH = Path("E:/data science tool/main/grok/question.py")
TRAINING_DATA_PATH = Path("E:/data science tool/main/grok/training_dataset.json")

# Dictionary to store cached function outputs
function_cache = {}

def load_module_from_path(file_path: Path, module_name: str = "dynamic_module"):
    """Load a Python module from file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error loading module from {file_path}: {e}")
        return None

def load_training_data():
    """Load the training dataset from JSON file."""
    try:
        if not TRAINING_DATA_PATH.exists():
            logger.error(f"Training dataset not found at {TRAINING_DATA_PATH}")
            return []
        
        with open(TRAINING_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} questions from training dataset")
        return data
    except Exception as e:
        logger.error(f"Error loading training dataset: {e}")
        return []

def extract_function_from_question(question: str, question_file_content: str) -> Optional[str]:
    """
    Extract the function name from the question by searching for a matching comment in the code.
    """
    # Clean up question for comparison
    clean_question = question.strip().lower()
    
    # Look for a comment that matches the question
    lines = question_file_content.split('\n')
    current_function = None
    
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        
        # Check if this line defines a function
        if line.strip().startswith("def "):
            function_name = line.strip().split("(")[0].replace("def ", "").strip()
            current_function = function_name
        
        # Check if this line contains a comment that matches part of the question
        # We look for significant phrases (at least 10 characters) to avoid false matches
        if line_lower.startswith("#") and len(line_lower) > 15:
            # Extract the comment part (remove the # symbol)
            comment = line_lower.lstrip("#").strip()
            
            # Check if significant parts of the comment appear in the question
            # or if significant parts of the question appear in the comment
            if (len(comment) > 10 and comment in clean_question) or \
               any(phrase in comment for phrase in [p for p in clean_question.split() if len(p) > 6]):
                if current_function:
                    logger.info(f"Found matching function {current_function} for question")
                    return current_function
    
    logger.warning(f"No matching function found for question")
    return None

@app.post("/api/solve")
async def solve_question(question: str = Form(...)):
    """
    Process and solve a question.
    """
    try:
        logger.info(f"Received question: {question[:100]}...")
        
        # Check cache first
        if question in function_cache:
            logger.info("Returning cached result")
            return {"answer": function_cache[question]}
        
        # Load the question module
        question_module = load_module_from_path(QUESTION_PATH)
        if not question_module:
            raise HTTPException(status_code=500, detail="Could not load question module")
        
        # Get the file content for function extraction
        with open(QUESTION_PATH, "r", encoding="utf-8") as f:
            question_file_content = f.read()
        
        # Extract function name based on question content
        function_name = extract_function_from_question(question, question_file_content)
        
        # If no function found, try generic solver if it exists
        if not function_name and hasattr(question_module, "solve"):
            function_name = "solve"
        
        if not function_name:
            raise HTTPException(status_code=400, detail="Could not determine function to call")
        
        # Check if the function exists in the module
        if not hasattr(question_module, function_name):
            raise HTTPException(status_code=400, detail=f"Function '{function_name}' not found in question module")
        
        # Get the function
        function = getattr(question_module, function_name)
        
        # Capture stdout to get the printed output
        old_stdout = sys.stdout
        sys.stdout = output_catcher = StringIO()
        
        try:
            # Call the function
            if function_name == "solve":
                result = function(question)
            else:
                result = function()
            
            # Get the stdout output
            stdout_output = output_catcher.getvalue().strip()
            
            # Determine the answer from the function result or stdout
            if result is not None:
                answer = str(result)
            elif stdout_output:
                answer = stdout_output
            else:
                answer = "No output produced"
            
            # Cache the result
            function_cache[question] = answer
            
            return {"answer": answer}
        
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# Test client for the FastAPI app
client = TestClient(app)

class TestQuestionAPI(unittest.TestCase):
    def setUp(self):
        # Load the training data
        self.training_data = load_training_data()
        
        # Load the question module to check available functions
        self.question_module = load_module_from_path(QUESTION_PATH)
        
        # If no training data, skip tests
        if not self.training_data:
            self.skipTest("No training data available")
    
    def test_api_endpoint(self):
        """Test that the API endpoint is working."""
        # Simple test with a basic question
        response = client.post(
            "/api/solve",
            data={"question": "What is the output of code -s?"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.json())
    
    def test_first_five_questions(self):
        """Test the first five questions from the training dataset."""
        max_questions = min(5, len(self.training_data))
        
        for i in range(max_questions):
            question_data = self.training_data[i]
            question = question_data.get("question", "")
            expected_answer = question_data.get("answer", "")
            
            print(f"\nTesting question {i+1}/{max_questions}: {question[:100]}...")
            
            response = client.post(
                "/api/solve",
                data={"question": question}
            )
            
            self.assertEqual(response.status_code, 200, f"Failed on question {i+1}")
            self.assertIn("answer", response.json(), f"No answer in response for question {i+1}")
            
            actual_answer = response.json()["answer"]
            print(f"Expected: {expected_answer[:100]}...")
            print(f"Actual: {actual_answer[:100]}...")
            
            # Check for reasonable match (not exact since output formats may vary)
            if expected_answer:
                # Convert both to lowercase for case-insensitive comparison
                # and remove whitespace for format-insensitive comparison
                expected_normalized = " ".join(expected_answer.lower().split())
                actual_normalized = " ".join(actual_answer.lower().split())
                
                # Consider it a match if either contains the other,
                # or if they share significant common substrings
                is_match = (
                    expected_normalized in actual_normalized or
                    actual_normalized in expected_normalized or
                    len(set(expected_normalized.split()) & set(actual_normalized.split())) / 
                    len(set(expected_normalized.split()) | set(actual_normalized.split())) > 0.5
                )
                
                self.assertTrue(is_match, f"Answer mismatch for question {i+1}")

# Add a StringIO class for output capture

# This part allows running the tests directly
if __name__ == "__main__":
    # Option 1: Run tests
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        unittest.main(argv=['first-arg-is-ignored'])
    # Option 2: Start the API server
    else:
        print("Starting Assignment Solver API at http://localhost:8000")
        print("Use /api/solve endpoint with a 'question' form parameter")
        uvicorn.run(app, host="127.0.0.1", port=8100)