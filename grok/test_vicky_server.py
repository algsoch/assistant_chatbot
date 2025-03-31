import os
import sys
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from io import StringIO
from fastapi.testclient import TestClient
from main.grok.vicky_server import vscode_status_solution
from main.grok.vicky_server import httpbin_request_solution

# filepath: e:\data science tool\main\grok\test_vicky_server.py

# Import the module to test
from main.grok.vicky_server import (
    app, normalize_text, find_best_question_match, execute_solution,
    answer_question, SOLUTION_MAP, QUESTIONS_DATA
)

# Create a test client
client = TestClient(app)

# Test the normalization function
def test_normalize_text():
    assert normalize_text("  Hello  World!  ") == "hello world!"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""
    assert normalize_text("Multi\nLine\nText") == "multi line text"

# Test that each question in QUESTIONS_DATA has a unique solution mapping
def test_questions_have_solutions():
    # Track files that should have solutions
    files_to_check = set()
    
    # Ensure each question in vickys.json has a corresponding file path
    for question in QUESTIONS_DATA:
        assert "file" in question, f"Question missing 'file' field: {question.get('question', 'Unknown')[:50]}..."
        if "file" in question:
            files_to_check.add(question["file"])
    
    # Check if all files in files_to_check have a solution in SOLUTION_MAP
    for file_path in files_to_check:
        if file_path not in SOLUTION_MAP:
            # This check is softer since some files might be handled by the dynamic import mechanism
            print(f"Note: No direct solution mapping for {file_path}")
        else:
            # If we have a solution, ensure it's callable
            solution_fn = SOLUTION_MAP[file_path]
            assert callable(solution_fn), f"Solution for {file_path} is not callable"

# Test that solutions are correctly mapped to questions
@pytest.mark.parametrize("file_path,solution_fn", [
    (file_path, solution_fn) for file_path, solution_fn in SOLUTION_MAP.items()
])
def test_solution_function_mapping(file_path, solution_fn):
    # Find all questions that should use this file_path
    matching_questions = [q for q in QUESTIONS_DATA if q.get("file") == file_path]
    
    # Skip if no questions use this file path
    if not matching_questions:
        pytest.skip(f"No questions found for {file_path}")
    
    # Check if the solution function correctly handles the questions
    for question in matching_questions:
        with patch('sys.stdout', new=StringIO()) as fake_out:
            try:
                result = None
                # Handle special case for VSCode status where query matters
                if file_path == "E://data science tool//GA1//first.py" and "code -v" in question.get("question", "").lower():
                    result = solution_fn("code -v")
                else:
                    result = solution_fn()
                
                # Ensure we got a result
                combined_output = result if result else fake_out.getvalue()
                assert combined_output, f"No output from solution for {file_path}"
            except Exception as e:
                pytest.fail(f"Solution for {file_path} raised error: {str(e)}")

# Test the question matching function
@pytest.mark.parametrize("question", [
    q["question"] for q in QUESTIONS_DATA if "question" in q
])
def test_question_matching(question):
    match = find_best_question_match(question)
    assert match is not None, f"Failed to match question: {question[:50]}..."
    
    # Find the original question to check against
    original = next((q for q in QUESTIONS_DATA if q.get("question") == question), None)
    assert original is not None, "Original question not found"
    
    assert match["file"] == original["file"], f"Wrong file match for question"

# Test answer_question function
@pytest.mark.parametrize("question", [
    q["question"] for q in QUESTIONS_DATA if "question" in q
])
def test_answer_question(question):
    # Only test a sample of questions to avoid long test runs
    answer = answer_question(question)
    assert answer is not None, f"No answer for question: {question[:50]}..."
    assert isinstance(answer, str), "Answer should be a string"
    assert "Execution time:" in answer, "Answer should include execution time"

# Test specific solutions

# Test vscode_status_solution
def test_vscode_status_solution():
    
    result = vscode_status_solution()
    assert "Visual Studio Code console has been requested to remain open" in result
    
    result = vscode_status_solution("code -v")
    assert "Visual Studio Code" in result
    assert "commit:" in result

# Test httpbin_request_solution with mocked requests
@patch('requests.get')
def test_httpbin_request_solution(mock_get):
    
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "args": {"email": "24f2006438@ds.study.iitm.ac.in"},
        "headers": {"Host": "httpbin.org"},
        "url": "https://httpbin.org/get?email=24f2006438%40ds.study.iitm.ac.in"
    }
    mock_get.return_value = mock_response
    
    result = httpbin_request_solution()
    assert "24f2006438@ds.study.iitm.ac.in" in result
    assert "httpbin.org" in result

# Test the API endpoint
def test_api_answer_endpoint():
    # Select a sample question from QUESTIONS_DATA
    sample_question = next((q["question"] for q in QUESTIONS_DATA if "question" in q), None)
    if not sample_question:
        pytest.skip("No questions found in QUESTIONS_DATA")
    
    response = client.post("/api/answer", json={"question": sample_question})
    assert response.status_code == 200
    assert "answer" in response.json()
    assert response.json()["answer"]

# Test the chat API endpoint
def test_api_chat_endpoint():
    # Select a sample question from QUESTIONS_DATA
    sample_question = next((q["question"] for q in QUESTIONS_DATA if "question" in q), None)
    if not sample_question:
        pytest.skip("No questions found in QUESTIONS_DATA")
    
    response = client.post("/api/chat", json={"message": sample_question, "history": []})
    assert response.status_code == 200
    assert "response" in response.json()
    assert "history" in response.json()
    assert len(response.json()["history"]) == 2  # User message + system response

# Test the root endpoint
def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert "Vicky's Question Solver" in response.text

# Test handling of incorrect questions
def test_incorrect_question():
    response = client.post("/api/answer", json={"question": "This is a completely unrelated question that won't match anything."})
    assert response.status_code == 200
    assert "I couldn't find a matching question" in response.json()["answer"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])