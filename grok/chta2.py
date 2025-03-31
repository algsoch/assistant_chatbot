import re
import json

# Input file (questions.py)
input_file = "E:/data science tool/main/grok/question.py"
output_file = "E:/data science tool/main/grok/vickys.json"

# Read the file
with open(input_file, "r", encoding="utf-8") as f:
    content = f.read()

# Regular expressions to extract file paths and questions
file_pattern = re.compile(r"#\s*(E://[^\n]+)")  # Extracts file paths
question_pattern = re.compile(r"question\d*\s*=\s*(\"\"\".*?\"\"\"|'''.*?'''|\".*?\"|'.*?')", re.DOTALL)  # Extracts questions

# Split content based on file headers
chunks = re.split(r"#\s*(E://[^\n]+)", content)[1:]

questions_list = []

for i in range(0, len(chunks), 2):
    file_path = chunks[i].strip()  # Extract file path
    block_content = chunks[i + 1]  # Extract the corresponding question block

    # Extract the question
    question_match = question_pattern.search(block_content)
    question_text = eval(question_match.group(1)).strip() if question_match else "Unknown Question"

    # Append to list
    questions_list.append({
        "file": file_path,
        "question": question_text
    })

# Save to JSON
with open(output_file, "w", encoding="utf-8") as json_file:
    json.dump(questions_list, json_file, indent=4)

print(f"✅ Extracted questions saved to {output_file}")
