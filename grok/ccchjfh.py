import re
import json
import os
from pathlib import Path

# Configuration - use absolute paths
QUESTION_FILE = "E:/data science tool/main/grok/question.py"
OUTPUT_JSON = "E:/data science tool/main/grok/vickyss.json"

def extract_questions():
    """Extract questions, parameters, and code blocks from the question.py file"""
    try:
        # Read the question.py file
        with open(QUESTION_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Successfully read file: {QUESTION_FILE} ({len(content)} bytes)")
        
        # Split content by file markers (handle both spacing variants)
        blocks = re.split(r'(#\s+E://[^\n]+)', content)[1:]  # Skip first empty section
        
        questions_data = []
        
        # Process blocks in pairs (filepath + content)
        for i in range(0, len(blocks), 2):
            if i+1 >= len(blocks):
                break
                
            file_path = blocks[i].strip().replace('#', '', 1).strip()
            content_block = blocks[i+1]
            
            print(f"Processing file: {file_path}")
            
            # Extract question - handle both quote formats
            question_match = re.search(r'question\d*\s*=\s*[\'"](.+?)[\'"]|question\d*\s*=\s*\'\'\'(.+?)\'\'\'', 
                                      content_block, re.DOTALL)
            
            question_text = ""
            if question_match:
                # Get whichever group matched (single or triple quotes)
                question_text = question_match.group(1) if question_match.group(1) else question_match.group(2)
                question_text = question_text.strip()
                print(f"Found question: {question_text[:50]}...")
            
            # Extract parameter (handle both spellings and formats)
            param_value = None
            param_match = re.search(r'param(?:e)?ter\s*=\s*[\'"](.+?)[\'"]', content_block)
            if param_match:
                param_value = param_match.group(1).strip()
                print(f"Found parameter: {param_value}")
            
            # Extract code block - start after imports or question/parameter definitions
            code_lines = []
            in_code_block = False
            
            for line in content_block.split('\n'):
                # Start capturing at import statements or function definitions
                if 'import ' in line or line.strip().startswith('def '):
                    in_code_block = True
                
                if in_code_block:
                    code_lines.append(line)
            
            code_text = "\n".join(code_lines).strip()
            
            # Special case: If the code is empty, look for any content after blank lines
            if not code_text:
                # Skip question/parameter lines and blank lines, then get remaining content
                content_lines = content_block.split('\n')
                for idx, line in enumerate(content_lines):
                    if ('question' not in line and 'parameter' not in line and 
                        line.strip() and not line.strip().startswith('#')):
                        code_text = "\n".join(content_lines[idx:]).strip()
                        break
            
            # Add to questions data
            if question_text:
                questions_data.append({
                    "file": file_path,
                    "question": question_text,
                    "parameter": param_value,
                    "code": code_text
                })
        
        print(f"Total questions extracted: {len(questions_data)}")
        return questions_data
        
    except Exception as e:
        import traceback
        print(f"Error processing file: {e}")
        print(traceback.format_exc())
        return []

# Main function
def main():
    # Extract questions from file
    questions = extract_questions()
    
    if not questions:
        print("No questions were extracted. Check the file path and format.")
        return
    
    # Save to JSON 
    try:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=4, ensure_ascii=False)
        print(f"✅ Successfully saved {len(questions)} questions to {OUTPUT_JSON}")
        
        # Print sample of first question
        if questions:
            first = questions[0]
            print("\nSample of first extracted question:")
            print(f"File: {first['file']}")
            print(f"Question: {first['question'][:100]}...")
            print(f"Parameter: {first['parameter']}")
            print(f"Code: {first['code'][:100]}...")
    except Exception as e:
        print(f"Error saving JSON: {e}")

if __name__ == "__main__":
    main()