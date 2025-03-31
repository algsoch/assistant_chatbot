import re
import ast
import subprocess
import requests
import json
from fuzzywuzzy import process

# Dictionary to store extracted functions
function_registry = {}

# Read the questions.py file
with open("E:/data science tool/main/grok/question.py", "r", encoding="utf-8") as f:
    content = f.read()

# ✅ FIXED: Properly split by detecting file path headers
file_blocks = re.split(r"#\s*(E://[^\n]+)", content)[1:]

for i in range(0, len(file_blocks), 2):
    file_path = file_blocks[i].strip()
    block = file_blocks[i + 1]

    # ✅ Extract question and parameters
    question_match = re.search(r"question\d*\s*=\s*(\"\"\".*?\"\"\"|'''.*?'''|\".*?\"|'.*?')", block, re.DOTALL)
    param_match = re.search(r"parameter\s*=\s*(\[[^\]]*\]|\".*?\"|'.*?')", block, re.DOTALL)

    question_text = eval(question_match.group(1)).strip() if question_match else "Unknown Question"
    param = eval(param_match.group(1)) if param_match else None

    # ✅ Extract function code using AST safely
    try:
        parsed_tree = ast.parse(block)
        functions = [node for node in parsed_tree.body if isinstance(node, ast.FunctionDef)]
        function_definitions = [ast.unparse(fn) for fn in functions]
    except SyntaxError:
        function_definitions = []

    # ✅ Dynamically define function to execute extracted code
    def execute_function(param=param, code=function_definitions):
    exec_globals = {}
    exec("\n".join(code), exec_globals)  # Execute extracted code

    # ✅ Find the function name dynamically and execute it
    function_names = [key for key in exec_globals.keys() if callable(exec_globals[key])]
    if function_names:
        func = exec_globals[function_names[0]]  # Get the first defined function
        return func()  # Execute and return actual output

    return "❌ No valid function found to execute."


    # ✅ Store function in registry with normalized question
    function_registry[question_text.lower()] = execute_function

# ✅ Function to handle user queries with fuzzy matching
def answer_question(user_question):
    """Find and execute the corresponding function for a question using fuzzy matching"""
    user_question = user_question.lower().strip()

    # Use fuzzy matching to find best match
    matched_question, score = process.extractOne(user_question, function_registry.keys())

    if score > 60:  # ✅ If match is strong enough, execute
        print(f"\n✅ Found best match: {matched_question} (Match Score: {score})\n")
        return function_registry[matched_question]()
    else:
        # Show available questions if no good match
        print("\n❓ No exact match found. Did you mean one of these?\n")
        for i, q in enumerate(function_registry.keys(), 1):
            print(f"{i}. {q}")

        return "❌ No matching question found."

# ✅ Example Usage
if __name__ == "__main__":
    user_input = input("🔍 Ask your question: ").strip()
    result = answer_question(user_input)
    print(result)
