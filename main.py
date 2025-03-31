import os
import sys
import re
import json
import subprocess
import importlib.util
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union

class QueryExecutionSystem:
    """
    Intelligent query execution system that analyzes natural language queries,
    identifies the appropriate script, extracts parameters, and executes the solution.
    """
    
    def __init__(self, base_directory: str = "E:\\data science tool"):
        """
        Initialize the Query Execution System with the project's base directory.
        
        Args:
            base_directory: Root directory containing all GA folders
        """
        self.base_directory = base_directory
        self.ga_folders = self._discover_ga_folders()
        self.script_index = self._build_script_index()
        self.category_patterns = self._initialize_category_patterns()
        
    def _discover_ga_folders(self) -> List[str]:
        """Discover all GA folders in the base directory"""
        ga_folders = []
        try:
            for item in os.listdir(self.base_directory):
                if os.path.isdir(os.path.join(self.base_directory, item)) and item.startswith("GA"):
                    ga_folders.append(item)
            
            # Sort folders to ensure consistent ordering
            ga_folders.sort()
            print(f"Discovered GA folders: {ga_folders}")
            return ga_folders
        except Exception as e:
            print(f"Error discovering GA folders: {e}")
            return []
    
    def _build_script_index(self) -> Dict[str, Dict[str, str]]:
        """Build an index of all available scripts with their paths and descriptions"""
        script_index = {}
        
        for ga_folder in self.ga_folders:
            folder_path = os.path.join(self.base_directory, ga_folder)
            script_index[ga_folder] = {}
            
            try:
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        # For Python files, extract their description from docstring
                        if item.endswith('.py'):
                            description = self._extract_file_description(item_path)
                            script_index[ga_folder][item] = {
                                'path': item_path,
                                'description': description,
                                'type': 'python'
                            }
                        # For ZIP, PDF, etc. files, just record their existence
                        elif item.endswith(('.zip', '.pdf', '.json', '.csv', '.txt', '.png', '.jpg', '.webp')):
                            script_index[ga_folder][item] = {
                                'path': item_path,
                                'description': f"{item} file in {ga_folder}",
                                'type': item.split('.')[-1].lower()
                            }
            except Exception as e:
                print(f"Error building script index for {ga_folder}: {e}")
        
        return script_index
    
    def _extract_file_description(self, file_path: str) -> str:
        """Extract docstring or first comment block from a Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to find docstring
            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                return docstring_match.group(1).strip()
            
            # If no docstring, look for comment block at the beginning
            lines = content.split('\n')
            comment_block = []
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    comment_block.append(line[1:].strip())
                elif comment_block:
                    break
            
            if comment_block:
                return '\n'.join(comment_block)
            
            return "No description available"
        except Exception:
            return "Error extracting description"
    
    def _initialize_category_patterns(self) -> Dict[str, List[str]]:
        """Define regex patterns to identify query categories"""
        return {
            "CLI Command": [
                r"code\s+(-[a-z]+\s*)+",
                r"run\s+command",
                r"execute\s+(shell|bash|terminal|cmd)",
                r"terminal output"
            ],
            "API Development": [
                r"api",
                r"rest",
                r"endpoint",
                r"fastapi",
                r"flask",
                r"django",
                r"deploy"
            ],
            "PDF Processing": [
                r"pdf",
                r"extract\s+tables",
                r"convert\s+pdf",
                r"pdf\s+to\s+(csv|markdown|text)",
                r"markdown"
            ],
            "File Operations": [
                r"file",
                r"zip",
                r"extract",
                r"move",
                r"rename",
                r"copy",
                r"list\s+attributes",
                r"directory"
            ],
            "Web Scraping": [
                r"scrape",
                r"crawl",
                r"imdb",
                r"website",
                r"html",
                r"web\s+data"
            ],
            "Image Processing": [
                r"image",
                r"photo",
                r"picture",
                r"compress",
                r"resize",
                r"optimize",
                r"png",
                r"jpg",
                r"webp"
            ],
            "Data Analysis": [
                r"analyze",
                r"statistics",
                r"chart",
                r"graph",
                r"plot",
                r"data\s+visualization",
                r"pandas",
                r"numpy"
            ],
            "GitHub Operations": [
                r"github",
                r"git",
                r"repository",
                r"repo",
                r"commit",
                r"push"
            ]
        }
    
    def identify_category(self, query: str) -> str:
        """Identify the category of the query based on patterns"""
        query_lower = query.lower()
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return category
        
        return "General Task"  # Default category
    
    def extract_parameters(self, query: str) -> List[str]:
        """Extract parameters from the query string"""
        parameters = []
        
        # Extract filenames with extensions
        file_matches = re.findall(r'(?:^|\s)([a-zA-Z0-9_\-]+\.(py|zip|pdf|txt|csv|json|png|jpg|webp))(?:\s|$)', query)
        parameters.extend([match[0] for match in file_matches])
        
        # Extract numeric parameters
        num_matches = re.findall(r'(?:^|\s)(\d+)(?:\s|$)', query)
        parameters.extend(num_matches)
        
        # Extract URL parameters
        url_matches = re.findall(r'https?://[^\s]+', query)
        parameters.extend(url_matches)
        
        # Extract flag parameters
        flag_matches = re.findall(r'-{1,2}[a-zA-Z0-9]+', query)
        parameters.extend(flag_matches)
        
        return parameters
    
    def find_script(self, query: str, category: str) -> Dict[str, Any]:
        """Find the most appropriate script for the given query and category"""
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        # First, look for exact keyword matches in script names and descriptions
        for ga_folder, scripts in self.script_index.items():
            for script_name, script_info in scripts.items():
                score = 0
                
                # Check if the script type matches the category
                if (category == "PDF Processing" and script_info['type'] in ['py', 'pdf']) or \
                   (category == "File Operations" and script_info['type'] in ['py', 'zip']) or \
                   (category == "Image Processing" and script_info['type'] in ['py', 'png', 'jpg', 'webp']) or \
                   (category == "Web Scraping" and 'scrape' in script_name.lower()) or \
                   (category == "API Development" and ('api' in script_name.lower() or 'workflow' in script_name.lower())) or \
                   (category == "GitHub Operations" and ('git' in script_name.lower() or 'github' in script_name.lower())):
                    score += 5
                
                # Keywords in script name are weighted highest
                keywords = re.findall(r'\b\w+\b', query_lower)
                for keyword in keywords:
                    if keyword in script_name.lower():
                        score += 3
                
                # Fuzzy match against script description
                if 'description' in script_info:
                    description = script_info['description'].lower()
                    for keyword in keywords:
                        if keyword in description:
                            score += 1
                
                # Look for specific patterns
                if ('extract' in query_lower and 'extract' in script_name.lower()) or \
                   ('pdf' in query_lower and 'pdf' in script_name.lower()) or \
                   ('csv' in query_lower and 'csv' in script_name.lower()) or \
                   ('list' in query_lower and 'list' in script_name.lower()) or \
                   ('github' in query_lower and 'github' in script_name.lower()):
                    score += 4
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        'ga_folder': ga_folder,
                        'script_name': script_name,
                        'path': script_info['path'],
                        'type': script_info['type'],
                        'score': score
                    }
        
        # If no good match found, use fallbacks based on category
        if best_match is None or best_score < 3:
            if category == "PDF Processing":
                # Look for PDF-related scripts
                for ga_folder, scripts in self.script_index.items():
                    for script_name, script_info in scripts.items():
                        if 'pdf' in script_name.lower() and script_info['type'] == 'py':
                            return {
                                'ga_folder': ga_folder,
                                'script_name': script_name,
                                'path': script_info['path'],
                                'type': script_info['type']
                            }
            
            # Add more fallbacks for other categories here
        
        return best_match or {'error': 'No suitable script found'}
    
    def prepare_execution_environment(self, script_info: Dict[str, Any], parameters: List[str]) -> Tuple[str, List[str]]:
        """Prepare the execution environment for the script"""
        script_path = script_info['path']
        processed_params = []
        
        # If script is a Python file
        if script_info['type'] == 'python':
            # If script needs to process a zip file, extract it first
            for param in parameters:
                if param.endswith('.zip'):
                    zip_path = self._find_file_in_ga_folders(param)
                    if zip_path:
                        extract_dir = zip_path.replace('.zip', '_extracted')
                        if not os.path.exists(extract_dir):
                            os.makedirs(extract_dir, exist_ok=True)
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                zip_ref.extractall(extract_dir)
                        processed_params.append(extract_dir)
                else:
                    # For other parameters, try to find file paths
                    file_path = self._find_file_in_ga_folders(param)
                    if file_path:
                        processed_params.append(file_path)
                    else:
                        processed_params.append(param)
            
            return script_path, processed_params
        
        # For non-Python files that might need extraction
        elif script_info['type'] == 'zip':
            extract_dir = script_path.replace('.zip', '_extracted')
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(script_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            
            # Look for Python script in extracted directory
            py_files = list(Path(extract_dir).glob('*.py'))
            if py_files:
                return str(py_files[0]), processed_params
        
        return script_path, processed_params
    
    def _find_file_in_ga_folders(self, filename: str) -> Optional[str]:
        """Find a file across all GA folders"""
        for ga_folder in self.ga_folders:
            folder_path = os.path.join(self.base_directory, ga_folder)
            file_path = os.path.join(folder_path, filename)
            if os.path.exists(file_path):
                return file_path
        return None
    
    def execute_script(self, script_path: str, parameters: List[str]) -> Dict[str, Any]:
        """Execute the identified script with parameters"""
        result = {
            "output": "",
            "error": None,
            "status": "success"
        }
        
        if not os.path.exists(script_path):
            result["error"] = f"Script not found: {script_path}"
            result["status"] = "failed"
            return result
        
        try:
            # For Python scripts
            if script_path.endswith('.py'):
                # Try to execute as module first
                script_dir = os.path.dirname(script_path)
                script_file = os.path.basename(script_path)
                orig_dir = os.getcwd()
                orig_sys_path = sys.path.copy()
                
                try:
                    # Change to script directory and add to sys.path
                    os.chdir(script_dir)
                    if script_dir not in sys.path:
                        sys.path.insert(0, script_dir)
                    
                    # Import the script as a module
                    spec = importlib.util.spec_from_file_location("dynamic_module", script_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Check if module has main function
                    if hasattr(module, 'main'):
                        # Capture stdout
                        old_stdout = sys.stdout
                        sys.stdout = import_stdout = StringIO()
                        
                        # Run the main function with parameters
                        output = module.main(*parameters)
                        
                        # Get captured stdout
                        stdout_output = import_stdout.getvalue()
                        sys.stdout = old_stdout
                        
                        result["output"] = stdout_output
                        if output:
                            result["function_output"] = output
                        
                    else:
                        # Fall back to subprocess if no main function
                        raise AttributeError("No main function found")
                        
                except Exception as e:
                    # Fall back to subprocess execution
                    command = [sys.executable, script_path] + parameters
                    process = subprocess.run(command, capture_output=True, text=True)
                    
                    result["output"] = process.stdout
                    if process.stderr:
                        result["error"] = process.stderr
                    
                    if process.returncode != 0:
                        result["status"] = "warning"
                
                finally:
                    # Restore original directory and sys.path
                    os.chdir(orig_dir)
                    sys.path = orig_sys_path
            
            # For other executable files
            elif os.access(script_path, os.X_OK):
                command = [script_path] + parameters
                process = subprocess.run(command, capture_output=True, text=True)
                
                result["output"] = process.stdout
                if process.stderr:
                    result["error"] = process.stderr
                
                if process.returncode != 0:
                    result["status"] = "warning"
            
            # For non-executable files (like PDFs), just return info
            else:
                result["output"] = f"File {script_path} exists but is not executable."
                result["status"] = "info"
        
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
        
        return result
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query and execute the appropriate script.
        
        Args:
            query: The natural language query
            
        Returns:
            Dict with execution results
        """
        try:
            # Identify query category
            category = self.identify_category(query)
            print(f"Identified category: {category}")
            
            # Extract parameters
            parameters = self.extract_parameters(query)
            print(f"Extracted parameters: {parameters}")
            
            # Find the most suitable script
            script_info = self.find_script(query, category)
            
            if 'error' in script_info:
                return {
                    "question": query,
                    "identified_category": category,
                    "solution_script": None,
                    "parameters": parameters,
                    "execution_output": None,
                    "error": script_info['error']
                }
            
            print(f"Selected script: {script_info['path']}")
            
            # Prepare execution environment
            script_path, processed_params = self.prepare_execution_environment(script_info, parameters)
            print(f"Prepared execution with params: {processed_params}")
            
            # Execute the script
            execution_result = self.execute_script(script_path, processed_params)
            
            # Format response
            response = {
                "question": query,
                "identified_category": category,
                "solution_script": f"{script_info['ga_folder']}/{script_info['script_name']}",
                "parameters": processed_params,
                "execution_output": execution_result.get("output"),
                "function_output": execution_result.get("function_output", None),
                "error": execution_result.get("error"),
                "status": execution_result.get("status")
            }
            
            return response
        
        except Exception as e:
            return {
                "question": query,
                "identified_category": "Unknown",
                "solution_script": None,
                "parameters": [],
                "execution_output": None,
                "error": str(e),
                "status": "failed"
            }

# Helper class for capturing stdout
from io import StringIO

def main():
    """
    Main entry point for the query execution system.
    """
    # Initialize the query execution system
    system = QueryExecutionSystem()
    
    if len(sys.argv) > 1:
        # Take query from command line argument
        query = ' '.join(sys.argv[1:])
        result = system.process_query(query)
        print(json.dumps(result, indent=2))
    else:
        # Interactive mode
        print("🔍 Intelligent Query Execution System")
        print("Enter your query or 'exit' to quit")
        
        while True:
            query = input("\n> ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            if not query:
                continue
            
            result = system.process_query(query)
            print("\nExecution Result:")
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
    