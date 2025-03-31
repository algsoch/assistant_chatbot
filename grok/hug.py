from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os
import ollama
import string

app = FastAPI()

# ✅ Load `vickys.json` into memory instead of `questions.json`
vickys_file = "E:/data science tool/main/grok/vickys.json"
with open(vickys_file, "r", encoding="utf-8") as f:
    questions_data = json.load(f)

# ✅ Normalize text for better matching
def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase."""
    return text.lower().translate(str.maketrans("", "", string.punctuation)).strip()

# ✅ Store preprocessed question list for faster lookups
question_lookup = {normalize_text(entry["question"]): entry["file"] for entry in questions_data}

class QuestionRequest(BaseModel):
    question: str

def find_best_match_ollama(user_question):
    """Uses Ollama (Mistral) to match the user question with `vickys.json`."""
    normalized_user_question = normalize_text(user_question)

    # ✅ First, check for an exact match
    if normalized_user_question in question_lookup:
        return next(q["question"] for q in questions_data if normalize_text(q["question"]) == normalized_user_question)

    # ✅ If no exact match, use Mistral (Ollama) for best match
    question_list = [normalize_text(q["question"]) for q in questions_data]
    prompt = f"""Find the best-matching question from the list below.
    User Question: "{user_question}"
    Available Questions: {question_list}
    Return ONLY the closest matching question (must be an exact question from the list)."""

    response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}], options={"num_ctx": 2048})
    
    return response["message"]["content"].strip() if "message" in response else None

@app.post("/ask")
def ask_question(request: QuestionRequest):
    best_match = find_best_match_ollama(request.question)

    if not best_match:
        return {"error": "❌ No matching question found in vickys.json."}

    script_path = question_lookup.get(normalize_text(best_match))
    
    if not script_path or not os.path.exists(script_path):
        return {"error": f"❌ Script file not found: {script_path}"}

    try:
        # ✅ Load and execute the script dynamically
        with open(script_path, "r", encoding="utf-8") as script_file:
            script_content = script_file.read()
        
        exec_globals = {}
        exec(script_content, exec_globals)  # Run script within FastAPI
        
        # ✅ Extract and run function if available
        function_names = [key for key in exec_globals.keys() if callable(exec_globals[key])]
        if function_names:
            func = exec_globals[function_names[0]]
            return {"question": request.question, "output": func()}  # Run function
            
        return {"question": request.question, "output": "Script executed, but no function found."}
    
    except Exception as e:
        return {"error": str(e)}
