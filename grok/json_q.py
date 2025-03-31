import re
import json

# Read the script file
with open("question.py", "r", encoding="utf-8") as f:
    content = f.read()

# Patterns to extract parts
file_pattern = re.compile(r"#\s*(E://[^\n]+)")
question_pattern = re.compile(r"question\d*\s*=\s*(['\"]{3}|['\"])(.*?)(\1)", re.DOTALL)
parameter_pattern = re.compile(r"parameter\s*=\s*(\[.*?\]|['\"]{3}.*?['\"]{3}|['\"].*?['\"])", re.DOTALL)

# Splitting based on file locations
blocks = re.split(r"(#\s*E://[^\n]+)", content)[1:]

extracted_data = []
current_file = None

for i in range(0, len(blocks), 2):
    current_file = blocks[i].strip()  # File path
    script_part = blocks[i + 1]  # Code with question and parameter

    # Extract question
    question_match = question_pattern.search(script_part)
    question = question_match.group(2).strip() if question_match else None

    # Extract parameter (handles both list and string formats)
    parameter_match = parameter_pattern.search(script_part)
    if parameter_match:
        param_str = parameter_match.group(1).strip()
        try:
            parameter = eval(param_str)  # Convert safely (list or string)
        except:
            parameter = param_str  # If it fails, keep as string
    else:
        parameter = None

    # Extract code (excluding question and parameter definitions)
    script_lines = script_part.split("\n")
    clean_code_lines = []
    inside_meta_block = False

    for line in script_lines:
        if "question" in line or "parameter" in line:
            inside_meta_block = True
            continue
        if inside_meta_block and (line.strip() == "" or line.strip().startswith("#")):
            continue
        clean_code_lines.append(line)

    code = "\n".join(clean_code_lines).strip()

    # Append extracted data
    extracted_data.append({
        "file": current_file.replace("# ", "").strip(),
        "question": question,
        "parameter": parameter,
        "code": code
    })

# Save to JSON
with open(r"E:\data science tool\main\grok\question.py", "w", encoding="utf-8") as json_file:
    json.dump(extracted_data, json_file, indent=4, ensure_ascii=False)

print("✅ Extracted data saved to questions.json")
