import os
import re
import sys
import json
import importlib
import inspect
import logging
import traceback
import subprocess
import difflib
from typing import Dict, List, Any, Optional, Tuple
from io import StringIO
from contextlib import redirect_stdout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("question_solver.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("question-solver")

# Define the path to your question.py file
QUESTION_FILE = "E:/data science tool/main/grok/question.py"
BASE_DIR = "E:/data science tool"

# Common libraries that might be needed by scripts
COMMON_IMPORTS = [
    "requests",
    "pandas",
    "numpy",
    "matplotlib.pyplot",
    "json",
    "csv",
    "datetime",
    "os",
    "sys",
    "re"
]

class QuestionInfo:
    """Class to store information about a question and its implementation"""
    def __init__(self, 
                 question_text: str, 
                 file_path: str,
                 parameters: Any = None,
                 code_block: str = None):
        self.question_text = question_text
        self.file_path = file_path
        self.parameters = parameters
        self.code_block = code_block
        
        # Extract function name if possible
        self.function_name = self._extract_function_name()
        
    def _extract_function_name(self) -> Optional[str]:
        """Extract the main function name from the code block"""
        if not self.code_block:
            return None
            
        # Try to find function definitions
        func_match = re.search(r'def\s+(\w+)\s*\(', self.code_block)
        if func_match:
            return func_match.group(1)
        return None
    
    def __str__(self):
        return f"QuestionInfo(question='{self.question_text[:30]}...', file='{self.file_path}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_text": self.question_text,
            "file_path": self.file_path,
            "parameters": self.parameters,
            "function_name": self.function_name,
            "code_block": self.code_block[:100] + "..." if self.code_block and len(self.code_block) > 100 else self.code_block
        }

def normalize_text(text):
    """Normalize text for better matching by removing extra whitespace and lowercasing"""
    if not text:
        return ""
    # Remove redundant whitespace and lowercase
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text

def parse_questions() -> List[QuestionInfo]:
    """Parse the question.py file and extract all questions, parameters, and code"""
    logger.info(f"Parsing questions from {QUESTION_FILE}")
    
    questions = []
    
    try:
        with open(QUESTION_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by file path comments - be more flexible with spaces
        sections = re.split(r'(#\s*E://[^\n]+)', content)
        
        current_file_path = None
        
        for i in range(len(sections)):
            section = sections[i]
            
            # Check if this is a file path marker
            if re.match(r'#\s*E://', section):
                # Extract file path
                current_file_path = section.strip().replace('#', '', 1).strip()
                logger.debug(f"Found file path marker: {current_file_path}")
                
                # Get the content section (next section if available)
                if i + 1 < len(sections):
                    content_section = sections[i + 1]
                    
                    # Extract question - handle both triple quotes and regular quotes
                    question_text = None
                    question_match = re.search(r'question\d*\s*=\s*[\'\"](.+?)[\'\"]', content_section, re.DOTALL)
                    if question_match:
                        question_text = question_match.group(1)
                    else:
                        # Try with triple quotes
                        question_match = re.search(r'question\d*\s*=\s*\'\'\'(.+?)\'\'\'', content_section, re.DOTALL)
                        if question_match:
                            question_text = question_match.group(1)
                    
                    if question_text:
                        # Extract parameter - be more flexible with formats
                        parameters = None
                        param_match = re.search(r'parameter\s*=\s*[\'\"](.+?)[\'\"]', content_section)
                        if param_match:
                            parameters = param_match.group(1)
                        else:
                            # Try with list format
                            param_match = re.search(r'parameter\s*=\s*(\[.+?\])', content_section)
                            if param_match:
                                try:
                                    parameters = eval(param_match.group(1))
                                except:
                                    parameters = param_match.group(1)
                            else:
                                # Check for parameter without value
                                if re.search(r'parameter\s*$', content_section, re.MULTILINE):
                                    parameters = None
                        
                        # Extract code - look for imports or function definitions
                        code_block = []
                        in_code = False
                        imports_found = False
                        
                        for line in content_section.split('\n'):
                            if line.strip().startswith('import ') or 'from ' in line and ' import ' in line:
                                in_code = True
                                imports_found = True
                                code_block.append(line)
                            elif line.strip().startswith('def '):
                                in_code = True
                                code_block.append(line)
                            elif in_code:
                                code_block.append(line)
                        
                        # If no imports/defs found, collect any non-metadata lines as potential code
                        if not imports_found:
                            code_block = []
                            skip_line = False
                            for line in content_section.split('\n'):
                                if 'question' in line and '=' in line or 'parameter' in line and '=' in line:
                                    skip_line = True
                                    continue
                                if skip_line and line.strip() == '':
                                    skip_line = False
                                    continue
                                if not skip_line:
                                    code_block.append(line)
                        
                        code_text = '\n'.join(code_block).strip()
                        
                        # Create question info object
                        questions.append(QuestionInfo(
                            question_text,
                            current_file_path,
                            parameters,
                            code_text
                        ))
        
        logger.info(f"Found {len(questions)} questions in {QUESTION_FILE}")
        return questions
    
    except Exception as e:
        logger.error(f"Error parsing questions: {e}")
        logger.error(traceback.format_exc())
        return []

def get_signature_phrases(text):
    """Extract signature phrases from the question text"""
    # Get the most distinctive phrases from the text
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Remove common words
    stop_words = {"the", "and", "a", "an", "in", "on", "at", "to", "for", "with", 
                 "by", "of", "is", "are", "was", "were", "be", "been", "being"}
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Special case handling for specific technical terms
    tech_terms = ["csv", "zip", "unzip", "vscode", "httpbin", "code -s", 
                 "python", "pandas", "numpy", "json", "http", "api", "extract"]
    
    # If any tech term is found in the text, prioritize it
    signature_terms = []
    for term in tech_terms:
        if term in text.lower():
            signature_terms.append(term)
    
    # Add other distinctive words (prioritizing longer words)
    sorted_words = sorted(filtered_words, key=len, reverse=True)
    signature_terms.extend(sorted_words[:5])  # Take up to 5 most distinctive terms
    
    return signature_terms

def find_matching_question(user_query: str, questions: List[QuestionInfo]) -> Optional[QuestionInfo]:
    """Find the question that best matches the user's query"""
    logger.info(f"Finding match for query: {user_query[:50]}...")
    
    if not questions:
        logger.error("No questions available for matching")
        return None
    
    # Normalize query for better matching
    normalized_query = normalize_text(user_query)
    
    # Get signature phrases from the query
    query_signatures = get_signature_phrases(normalized_query)
    logger.debug(f"Query signatures: {query_signatures}")
    
    # Store matches with their scores
    matches = []
    
    # 1. Try exact match first
    for question_info in questions:
        normalized_question = normalize_text(question_info.question_text)
        if normalized_question == normalized_query:
            logger.info(f"Found exact match: {question_info.file_path}")
            return question_info
    
    # 2. Try signature phrase matching
    for question_info in questions:
        normalized_question = normalize_text(question_info.question_text)
        question_signatures = get_signature_phrases(normalized_question)
        
        # Calculate signature match score
        common_signatures = set(query_signatures) & set(question_signatures)
        if common_signatures:
            score = len(common_signatures) / max(len(query_signatures), 1)
            matches.append((question_info, score, "signature"))
    
    # 3. Try keyword matching
    query_keywords = set(re.findall(r'\b\w+\b', normalized_query.lower()))
    for question_info in questions:
        normalized_question = normalize_text(question_info.question_text)
        question_keywords = set(re.findall(r'\b\w+\b', normalized_question.lower()))
        
        # Calculate Jaccard similarity
        intersection = query_keywords.intersection(question_keywords)
        union = query_keywords.union(question_keywords)
        if union:
            score = len(intersection) / len(union)
            matches.append((question_info, score, "keyword"))
    
    # 4. Try fuzzy matching for additional matches
    for question_info in questions:
        normalized_question = normalize_text(question_info.question_text)
        # For long texts, use partial matching of first 100 chars
        query_part = normalized_query[:100]
        question_part = normalized_question[:100]
        
        ratio = difflib.SequenceMatcher(None, query_part, question_part).ratio()
        matches.append((question_info, ratio, "fuzzy"))
    
    # Sort matches by score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    # Print top matches for debugging
    for i, (question, score, match_type) in enumerate(matches[:3]):
        logger.debug(f"Match #{i+1}: {match_type} score={score:.2f}, file={question.file_path}")
        logger.debug(f"  Question: {question.question_text[:50]}...")
    
    # Find best match above threshold
    best_match = None
    best_score = 0
    best_type = None
    
    for question, score, match_type in matches:
        # Different thresholds for different match types
        threshold = {
            "signature": 0.5,
            "keyword": 0.3,
            "fuzzy": 0.6
        }.get(match_type, 0.5)
        
        if score >= threshold and score > best_score:
            best_match = question
            best_score = score
            best_type = match_type
    
    if best_match:
        logger.info(f"Best match ({best_type}, score={best_score:.2f}): {best_match.file_path}")
        return best_match
    
    logger.warning(f"No good match found for query: {normalized_query[:50]}...")
    return None

def ensure_imports(code_block: str) -> str:
    """Ensure that common libraries are imported in the code block"""
    needed_imports = []
    
    # Check which imports might be needed
    for lib in COMMON_IMPORTS:
        if lib in code_block and f"import {lib}" not in code_block and f"from {lib}" not in code_block:
            if lib == "matplotlib.pyplot":
                needed_imports.append("import matplotlib.pyplot as plt")
            else:
                needed_imports.append(f"import {lib}")
    
    # If any imports are needed, add them at the beginning
    if needed_imports:
        return "\n".join(needed_imports) + "\n\n" + code_block
    return code_block

def execute_code_block(question_info: QuestionInfo, user_params: Dict[str, Any] = None) -> str:
    """Execute the code block associated with the question"""
    logger.info(f"Executing code for: {question_info.file_path}")
    
    # Check if we have a code block
    if not question_info.code_block:
        return "No code implementation found for this question."
    
    # Make sure required libraries are imported
    code_block = ensure_imports(question_info.code_block)
    
    # Create a namespace for execution
    namespace = {}
    
    # Pre-import common libraries
    for lib_name in COMMON_IMPORTS:
        try:
            if lib_name == "matplotlib.pyplot":
                exec("import matplotlib.pyplot as plt", namespace)
            else:
                exec(f"import {lib_name}", namespace)
        except ImportError:
            pass  # Skip if library is not available
    
    # Capture stdout to get printed output
    captured_output = StringIO()
    
    try:
        # Redirect stdout to capture output
        with redirect_stdout(captured_output):
            # Execute the code
            exec(code_block, namespace)
            
        # Get the captured output
        output = captured_output.getvalue()
        
        # If there's a main function identified, try to call it
        if question_info.function_name and question_info.function_name in namespace:
            function = namespace[question_info.function_name]
            sig = inspect.signature(function)
            
            # Call function with appropriate parameters based on its signature
            if len(sig.parameters) > 0 and user_params:
                try:
                    # Try calling with user params
                    if isinstance(user_params, dict):
                        # Check if function accepts kwargs
                        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                            result = function(**user_params)
                        else:
                            # Try to match params to parameter names
                            param_names = list(sig.parameters.keys())
                            if param_names and param_names[0] in user_params:
                                # Named parameters
                                kwargs = {k: v for k, v in user_params.items() if k in param_names}
                                result = function(**kwargs)
                            else:
                                # Call with defaults - don't use params from question.py
                                result = function()
                    else:
                        # Don't use params from question.py - call without params
                        result = function()
                        
                    if result is not None:
                        output += f"\nFunction return: {result}"
                except Exception as e:
                    logger.error(f"Error calling function with parameters: {e}")
                    logger.error(traceback.format_exc())
            else:
                try:
                    result = function()
                    if result is not None:
                        output += f"\nFunction return: {result}"
                except Exception as e:
                    logger.error(f"Error calling function without parameters: {e}")
        
        return output.strip() or "Code executed but produced no output."
    
    except Exception as e:
        logger.error(f"Error executing code: {e}")
        logger.error(traceback.format_exc())
        return f"Error executing code: {str(e)}\n{traceback.format_exc()}"

def answer_question(user_query: str, user_params: Dict[str, Any] = None) -> str:
    """Main function to answer a user's question"""
    # Parse questions from the file
    questions = parse_questions()
    
    if not questions:
        return "No questions found in the question database."
    
    # Find the matching question
    matching_question = find_matching_question(user_query, questions)
    
    if not matching_question:
        return "I couldn't find a matching question. Please try rephrasing your query."
    
    # Execute the code or script
    try:
        # Try executing the code block first
        if matching_question.code_block:
            return execute_code_block(matching_question, user_params)
        
        # If no code block, try executing the script file
        elif matching_question.file_path:
            return execute_script_file(matching_question.file_path, user_params)
        
        return "Found a matching question, but no code implementation available."
    
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        logger.error(traceback.format_exc())
        return f"Error processing your question: {str(e)}"

def execute_script_file(file_path: str, params: Dict[str, Any] = None) -> str:
    """Execute a Python script file and return its output"""
    logger.info(f"Executing script: {file_path}")
    
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            # Try relative path from BASE_DIR
            file_path = os.path.join(BASE_DIR, file_path.lstrip('E:/'))
            if not os.path.exists(file_path):
                return f"Script file not found: {file_path}"
        
        # Run the script using subprocess
        env = os.environ.copy()
        if params:
            env['SCRIPT_PARAMS'] = json.dumps(params)
        
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            env=env
        )
        
        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
        
        return output.strip() or "Script executed but produced no output."
    
    except Exception as e:
        logger.error(f"Error executing script: {e}")
        logger.error(traceback.format_exc())
        return f"Error executing script: {str(e)}\n{traceback.format_exc()}"

# Command line interface
def main():
    """Command line interface to answer questions"""
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        
        print(f"Question: {query}")
        print("-" * 50)
        
        answer = answer_question(query)
        
        print("Answer:")
        print(answer)
    else:
        print("Usage: python question_executor.py 'your question here'")
        print("\nOr enter interactive mode:")
        
        while True:
            query = input("\nEnter your question (or 'exit' to quit): ")
            
            if query.lower() == 'exit':
                break
            
            print("-" * 50)
            answer = answer_question(query)
            
            print("Answer:")
            print(answer)
            print("-" * 50)

if __name__ == "__main__":
    main()