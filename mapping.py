import json
import os
import re

# Load training dataset
with open("E:\\data science tool\\main\\training_dataset.json", "r", encoding="utf-8") as f:
    training_data = json.load(f)

# Base directory where GA folders are located
BASE_DIR = "."

# List of GA directories (GA1, GA2, GA3, etc.)
ga_folders = [d for d in os.listdir(BASE_DIR) if d.startswith("GA") and os.path.isdir(d)]

# Function to extract numeric order from filenames (e.g., "first.py" → 1, "second.py" → 2)
def extract_script_order(script_name):
    mapping = {
        "first": 1, "second": 2, "third": 3, "forth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "nineth": 9, "tenth": 10,
        "eleventh": 11, "twelth": 12, "thirteenth": 13, "forteen": 14,
        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteen": 18
    }
    for key, value in mapping.items():
        if key in script_name.lower():
            return value
    return float("inf")  # If no match, keep it at the end

# Generate mapping of GA folders to their Python scripts
ga_script_mapping = {}

for ga_folder in ga_folders:
    scripts = [f for f in os.listdir(ga_folder) if f.endswith(".py")]
    scripts.sort(key=extract_script_order)  # Ensure scripts are in order

    ga_script_mapping[ga_folder] = scripts

# Automatically map questions to scripts
question_mapping = {"questions": []}

script_index = {}  # Track script usage per GA folder

for qa_pair in training_data:
    question_text = qa_pair["question"]
    
    # Find the GA folder with the least used script
    selected_ga = None
    selected_script = None
    
    for ga_folder, scripts in ga_script_mapping.items():
        if ga_folder not in script_index:
            script_index[ga_folder] = 0

        if script_index[ga_folder] < len(scripts):  # Ensure there are scripts left
            selected_ga = ga_folder
            selected_script = scripts[script_index[ga_folder]]
            script_index[ga_folder] += 1
            break  # Stop after assigning one

    if selected_ga and selected_script:
        question_mapping["questions"].append({
            "question": question_text,
            "mapped_script": f"{selected_ga}/{selected_script}"
        })

# Save the mapping to a JSON file
with open("question_mapping.json", "w", encoding="utf-8") as f:
    json.dump(question_mapping, f, indent=4)

print("✅ Question mapping successfully generated in `question_mapping.json`.")
