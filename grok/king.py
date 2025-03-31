import re
import subprocess
import requests
import json

def load_questions(file_path):
    """ Read the questions.py file and extract questions, parameters, and code """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_pattern = re.compile(r"#\s*(E://[^\n]+)")
    question_pattern = re.compile(r"question\d*\s*=\s*(\"\"\".*?\"\"\"|'''.*?'''|\".*?\"|'.*?')", re.DOTALL)
    parameter_pattern = re.compile(r"parameter\s*=\s*(\[.*?\]|\".*?\"|'.*?')", re.DOTALL)
    code_pattern = re.compile(r"import.*?\ndef.*?\n(.*?)\n\n", re.DOTALL)

    file_matches = file_pattern.findall(content)
    question_matches = question_pattern.findall(content)
    parameter_matches = parameter_pattern.findall(content)
    code_matches = code_pattern.findall(content)

    extracted_data = []
    for i in range(len(file_matches)):
        question = eval(question_matches[i]) if i < len(question_matches) else "Unknown"
        parameter = eval(parameter_matches[i]) if i < len(parameter_matches) else None
        code = code_matches[i] if i < len(code_matches) else ""

        extracted_data.append({
            "file": file_matches[i],
            "question": question,
            "parameter": parameter,
            "code": code
        })

    return extracted_data

def execute_code(question_text, extracted_data):
    """ Find and execute the corresponding function for a question """
    for data in extracted_data:
        if question_text.lower() in data["question"].lower():
            print(f"\n✅ Executing Code for: {data['question']}\n")

            if "subprocess.run" in data["code"]:
                # Run shell command dynamically
                try:
                    command = data["parameter"]
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    print(result.stdout)
                except Exception as e:
                    print(f"Error executing command: {e}")

            elif "requests.get" in data["code"]:
                # Run HTTP API request dynamically
                url = "https://httpbin.org/get"
                params = {"email": "24f2006438@ds.study.iitm.ac.in"}
                response = requests.get(url, params=params)
                print(json.dumps(response.json(), indent=4))

            else:
                exec(data["code"])  # Directly execute Python code

            return
    print("❌ No matching question found.")

if __name__ == "__main__":
    extracted_data = load_questions("E://data science tool//main//grok//question.py")

    # Example user question
    user_question = input("🔍 Ask your question: ")
    execute_code(user_question, extracted_data)
