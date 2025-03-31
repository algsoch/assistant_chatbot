import ollama
import json
import os

# ✅ Load `vickys.json`
with open("E:\\data science tool\\main\\grok\\vickys.json", "r", encoding="utf-8") as f:
    vickys_data = json.load(f)

def extract_code(file_path):
    """Reads the existing code from the file."""
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_modified_code(question, original_code):
    """Uses LLM to modify the code dynamically."""
    prompt = f"""
    You are an AI that helps modify Python code to allow user-defined inputs. 
    Given this question: "{question}"
    
    Modify the following Python code so that:
    - Any fixed parameters are turned into function parameters.
    - The function can accept user input dynamically.
    - Ensure error handling is added.
    
    Original Code:
    ```python
    {original_code}
    ```
    
    Modified Code:
    """
    
    response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]

# ✅ Generate dataset.json
dataset = []
for entry in vickys_data:
    file_path = entry["file"]
    question = entry["question"]
    original_code = extract_code(file_path)

    if original_code:
        modified_code = generate_modified_code(question, original_code)
        dataset.append({"question": question, "file": file_path, "code": modified_code})

# ✅ Save modified dataset to JSON
with open("dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=4)

print("✅ dataset.json created successfully!")
