from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import subprocess

app = FastAPI()

# Load questions.json
with open("questions.json", "r", encoding="utf-8") as f:
    questions_data = json.load(f)

class QuestionRequest(BaseModel):
    question: str

def find_script_for_question(user_question):
    """Find the matching script for a given question."""
    for entry in questions_data:
        if user_question.lower() in entry["question"].lower():
            return entry["file"]
    return None

@app.post("/ask")
def ask_question(request: QuestionRequest):
    print("🔍 Received Question:", request.question)
    
    # Debug: Show all available questions
    available_questions = [entry["question"] for entry in questions_data]
    print("📌 Available Questions:", available_questions)

    script_path = find_script_for_question(request.question)
    
    if not script_path:
        return {"error": "❌ Question not found in questions.json!"}

    try:
        result = subprocess.run(["python", script_path], capture_output=True, text=True)
        return {"output": result.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}


