import os
import re
import sys
import json
import time
import requests
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test-api")

# Configuration
BASE_DIR = Path("E:/data science tool")
API_ENDPOINT = "http://localhost:8000/api/solve"
RESULTS_DIR = BASE_DIR / "test_results"
RESULTS_DIR.mkdir(exist_ok=True, parents=True)

class QuestionExtractor:
    """Extract questions from Python files in GA folders"""
    
    def __init__(self, base_dir=BASE_DIR):
        self.base_dir = Path(base_dir)
        self.questions = []
        self.ga_folders = ["GA1", "GA2", "GA3", "GA4"]
    
    def extract_questions_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract question and parameters from a Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract questions using regex
            question_matches = re.findall(r'question\d+\s*=\s*[\'"](.+?)[\'"]', content, re.DOTALL)
            parameter_matches = re.findall(r'parameter\s*=\s*[\'"](.+?)[\'"]', content, re.DOTALL)
            
            result = []
            for i, question_text in enumerate(question_matches):
                # Clean up question text
                question_text = question_text.strip()
                
                # Get parameter if available
                parameter = parameter_matches[i] if i < len(parameter_matches) else ""
                
                # Extract function name
                func_match = re.search(r'def\s+(\w+)\s*\(', content)
                function_name = func_match.group(1) if func_match else None
                
                result.append({
                    "file_path": str(file_path),
                    "ga_folder": file_path.parent.name,
                    "script_name": file_path.stem,
                    "question": question_text,
                    "parameter": parameter,
                    "function_name": function_name
                })
            
            return result
        except Exception as e:
            logger.error(f"Error extracting questions from {file_path}: {e}")
            return []
    
    def extract_all_questions(self) -> List[Dict[str, Any]]:
        """Extract questions from all GA folders"""
        all_questions = []
        
        for ga_folder in self.ga_folders:
            folder_path = self.base_dir / ga_folder
            if not folder_path.exists() or not folder_path.is_dir():
                logger.warning(f"GA folder not found: {folder_path}")
                continue
            
            logger.info(f"Extracting questions from {ga_folder}...")
            
            # Find all Python files in this folder
            python_files = list(folder_path.glob("*.py"))
            
            for file_path in tqdm(python_files, desc=f"Files in {ga_folder}"):
                questions = self.extract_questions_from_file(file_path)
                all_questions.extend(questions)
        
        logger.info(f"Extracted {len(all_questions)} questions from all GA folders")
        self.questions = all_questions
        return all_questions
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """Get all extracted questions or extract them if not done yet"""
        if not self.questions:
            return self.extract_all_questions()
        return self.questions

class APITester:
    """Test the assignment solver API with extracted questions"""
    
    def __init__(self, api_url=API_ENDPOINT, questions=None):
        self.api_url = api_url
        self.questions = questions or []
        self.results = []
    
    def set_questions(self, questions):
        """Set the questions to test"""
        self.questions = questions
    
    def test_question(self, question_data):
        """Test a single question against the API"""
        question_text = question_data.get("question", "")
        file_path = question_data.get("file_path", "")
        
        if not question_text:
            return {
                "question_data": question_data,
                "status": "skipped",
                "reason": "Empty question",
                "api_response": None,
                "response_time": 0
            }
        
        try:
            # Send request to API
            start_time = time.time()
            response = requests.post(
                self.api_url,
                data={"question": question_text},
                files={"file": None}
            )
            response_time = time.time() - start_time
            
            result = {
                "question_data": question_data,
                "response_time": response_time
            }
            
            # Process response
            if response.status_code == 200:
                api_response = response.json().get("answer", "")
                result["api_response"] = api_response
                
                # Determine status based on response content
                if "error" in api_response.lower() or "could not" in api_response.lower():
                    result["status"] = "failed"
                    result["reason"] = "API returned error message"
                else:
                    result["status"] = "passed"
            else:
                result["status"] = "failed"
                result["reason"] = f"API returned status code {response.status_code}"
                result["api_response"] = response.text
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing question from {file_path}: {e}")
            return {
                "question_data": question_data,
                "status": "error",
                "reason": str(e),
                "api_response": None,
                "response_time": 0
            }
    
    def run_tests(self, start_index=0, end_index=None, parallel=False, max_workers=5):
        """Run tests on all or a subset of questions"""
        if not self.questions:
            logger.error("No questions available for testing")
            return []
        
        # Determine range to test
        if end_index is None:
            end_index = len(self.questions)
        
        test_data = self.questions[start_index:end_index]
        logger.info(f"Testing {len(test_data)} questions (index {start_index} to {end_index-1})")
        
        results = []
        
        if parallel:
            # Run tests in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.test_question, q): q 
                    for q in test_data
                }
                
                for future in tqdm(as_completed(futures), total=len(futures), desc="Testing questions"):
                    result = future.result()
                    results.append(result)
                    
                    # Log result
                    question_path = result["question_data"].get("file_path", "Unknown")
                    logger.info(f"Question {question_path}: {result['status']}")
        else:
            # Run tests sequentially
            for question_data in tqdm(test_data, desc="Testing questions"):
                result = self.test_question(question_data)
                results.append(result)
                
                # Log result
                question_path = question_data.get("file_path", "Unknown")
                logger.info(f"Question {question_path}: {result['status']}")
        
        # Store results
        self.results = results
        return results
    
    def generate_report(self):
        """Generate a report of the test results"""
        if not self.results:
            logger.error("No test results available")
            return
        
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "passed")
        failed_tests = sum(1 for r in self.results if r["status"] == "failed")
        error_tests = sum(1 for r in self.results if r["status"] == "error")
        skipped_tests = sum(1 for r in self.results if r["status"] == "skipped")
        
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        avg_response_time = sum(r["response_time"] for r in self.results) / total_tests if total_tests > 0 else 0
        
        # Create summary
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "skipped_tests": skipped_tests,
            "pass_rate": pass_rate,
            "avg_response_time": avg_response_time
        }
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save summary and detailed results as JSON
        results_path = RESULTS_DIR / f"test_results_{timestamp}.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": summary,
                "results": [
                    {
                        "file_path": r["question_data"]["file_path"],
                        "ga_folder": r["question_data"]["ga_folder"],
                        "script_name": r["question_data"]["script_name"],
                        "question": r["question_data"]["question"][:100] + "..." if len(r["question_data"]["question"]) > 100 else r["question_data"]["question"],
                        "parameter": r["question_data"]["parameter"],
                        "status": r["status"],
                        "reason": r.get("reason", ""),
                        "response_time": r["response_time"],
                        "api_response": r.get("api_response", "")[:200] + "..." if r.get("api_response") and len(r.get("api_response", "")) > 200 else r.get("api_response", "")
                    } for r in self.results
                ]
            }, f, indent=2)
        
        logger.info(f"Results saved to {results_path}")
        
        # Generate HTML report
        html_path = self._generate_html_report(summary, timestamp)
        
        return {
            "summary": summary,
            "results_path": results_path,
            "html_path": html_path
        }
    
    def _generate_html_report(self, summary, timestamp):
        """Generate an HTML report of the test results"""
        html_path = RESULTS_DIR / f"test_report_{timestamp}.html"
        
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Test Results</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #444;
                }}
                .summary {{
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    grid-gap: 15px;
                }}
                .summary-item {{
                    background-color: white;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .passed {{
                    color: #4caf50;
                }}
                .failed {{
                    color: #f44336;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #ddd;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .result-passed {{
                    background-color: rgba(76, 175, 80, 0.1);
                }}
                .result-failed {{
                    background-color: rgba(244, 67, 54, 0.1);
                }}
                .result-error {{
                    background-color: rgba(255, 152, 0, 0.1);
                }}
                .filter-buttons {{
                    margin-bottom: 20px;
                }}
                .filter-button {{
                    background-color: #f2f2f2;
                    border: none;
                    padding: 8px 16px;
                    margin-right: 8px;
                    border-radius: 4px;
                    cursor: pointer;
                }}
                .filter-button.active {{
                    background-color: #4a6da7;
                    color: white;
                }}
                details {{
                    margin: 10px 0;
                }}
                summary {{
                    cursor: pointer;
                }}
                pre {{
                    background-color: #f8f8f8;
                    padding: 10px;
                    border-radius: 3px;
                    overflow-x: auto;
                    white-space: pre-wrap;
                }}
            </style>
        </head>
        <body>
            <h1>API Test Results</h1>
            <p>Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Summary</h2>
                <div class="summary-grid">
                    <div class="summary-item">
                        <h3>Total Tests</h3>
                        <p>{summary['total_tests']}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Passed</h3>
                        <p class="passed">{summary['passed_tests']}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Failed</h3>
                        <p class="failed">{summary['failed_tests']}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Errors</h3>
                        <p class="failed">{summary['error_tests']}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Pass Rate</h3>
                        <p>{summary['pass_rate']:.2f}%</p>
                    </div>
                    <div class="summary-item">
                        <h3>Avg Response Time</h3>
                        <p>{summary['avg_response_time']:.3f}s</p>
                    </div>
                </div>
            </div>
            
            <h2>Detailed Results</h2>
            
            <div class="filter-buttons">
                <button class="filter-button active" data-filter="all">All</button>
                <button class="filter-button" data-filter="passed">Passed</button>
                <button class="filter-button" data-filter="failed">Failed</button>
                <button class="filter-button" data-filter="error">Errors</button>
            </div>
            
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th>GA Folder</th>
                        <th>Script</th>
                        <th>Status</th>
                        <th>Response Time</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add rows for each result
        for result in self.results:
            question_data = result["question_data"]
            file_path = question_data.get("file_path", "Unknown")
            ga_folder = question_data.get("ga_folder", "Unknown")
            script_name = question_data.get("script_name", "Unknown")
            question = question_data.get("question", "")
            parameter = question_data.get("parameter", "")
            
            row_class = f"result-{result['status']}"
            
            html_content += f"""
                    <tr class="{row_class}" data-status="{result['status']}">
                        <td>{ga_folder}</td>
                        <td>{script_name}</td>
                        <td>{result['status'].upper()}</td>
                        <td>{result['response_time']:.3f}s</td>
                        <td>
                            <details>
                                <summary>View Details</summary>
                                <h4>File Path:</h4>
                                <pre>{file_path}</pre>
                                
                                <h4>Question:</h4>
                                <pre>{question[:200] + '...' if len(question) > 200 else question}</pre>
            """
            
            # Add parameter if available
            if parameter:
                html_content += f"""
                                <h4>Parameter:</h4>
                                <pre>{parameter}</pre>
                """
            
            # Add API response if available
            if result.get("api_response"):
                html_content += f"""
                                <h4>API Response:</h4>
                                <pre>{result['api_response'][:500] + '...' if len(result['api_response']) > 500 else result['api_response']}</pre>
                """
            
            # Add reason if available
            if result.get("reason"):
                html_content += f"""
                                <h4>Reason:</h4>
                                <pre>{result['reason']}</pre>
                """
            
            html_content += """
                            </details>
                        </td>
                    </tr>
            """
        
        # Complete the HTML
        html_content += """
                </tbody>
            </table>
            
            <script>
                // Filter functionality
                document.querySelectorAll('.filter-button').forEach(button => {
                    button.addEventListener('click', function() {
                        // Update button styles
                        document.querySelectorAll('.filter-button').forEach(btn => {
                            btn.classList.remove('active');
                        });
                        this.classList.add('active');
                        
                        // Get filter value
                        const filter = this.getAttribute('data-filter');
                        
                        // Filter table rows
                        document.querySelectorAll('#resultsTable tbody tr').forEach(row => {
                            if (filter === 'all' || row.getAttribute('data-status') === filter) {
                                row.style.display = '';
                            } else {
                                row.style.display = 'none';
                            }
                        });
                    });
                });
            </script>
        </body>
        </html>
        """
        
        # Write HTML to file
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated at {html_path}")
        return html_path

def interactive_test_mode(extractor, tester):
    """Run an interactive test session"""
    print("\n=== Interactive Test Mode ===")
    
    # Extract all questions if not done yet
    if not extractor.questions:
        extractor.extract_all_questions()
    
    questions = extractor.questions
    
    while True:
        print("\nOptions:")
        print("1. Test a specific GA folder")
        print("2. Test a specific script")
        print("3. Test all questions")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            # Test a specific GA folder
            print("\nAvailable GA folders:")
            for i, folder in enumerate(extractor.ga_folders, 1):
                folder_questions = [q for q in questions if q["ga_folder"] == folder]
                print(f"{i}. {folder} ({len(folder_questions)} questions)")
            
            folder_choice = input("\nEnter folder number: ")
            try:
                folder_idx = int(folder_choice) - 1
                if 0 <= folder_idx < len(extractor.ga_folders):
                    selected_folder = extractor.ga_folders[folder_idx]
                    folder_questions = [q for q in questions if q["ga_folder"] == selected_folder]
                    
                    print(f"\nTesting {len(folder_questions)} questions from {selected_folder}...")
                    tester.set_questions(folder_questions)
                    tester.run_tests()
                    tester.generate_report()
                else:
                    print("Invalid folder number")
            except ValueError:
                print("Please enter a number")
        
        elif choice == "2":
            # Test a specific script
            ga_folder = input("\nEnter GA folder (e.g., GA1): ")
            script_name = input("Enter script name (e.g., first): ")
            
            script_questions = [q for q in questions if q["ga_folder"] == ga_folder and q["script_name"] == script_name]
            
            if script_questions:
                print(f"\nTesting {len(script_questions)} questions from {ga_folder}/{script_name}...")
                tester.set_questions(script_questions)
                tester.run_tests()
                tester.generate_report()
            else:
                print(f"No questions found for {ga_folder}/{script_name}")
        
        elif choice == "3":
            # Test all questions
            parallel = input("\nRun tests in parallel? (y/n): ").lower() == 'y'
            
            print(f"\nTesting all {len(questions)} questions...")
            tester.set_questions(questions)
            tester.run_tests(parallel=parallel)
            tester.generate_report()
        
        elif choice == "4":
            # Exit
            print("\nExiting interactive mode")
            break
        
        else:
            print("\nInvalid choice. Please try again.")

def main():
    """Main function for the API tester"""
    parser = argparse.ArgumentParser(description="Test the Assignment Solver API")
    parser.add_argument("--url", type=str, default=API_ENDPOINT, help="API endpoint URL")
    parser.add_argument("--ga", type=str, help="Test only a specific GA folder (e.g., GA1)")
    parser.add_argument("--script", type=str, help="Test only a specific script (requires --ga)")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--workers", type=int, default=5, help="Number of workers for parallel testing")
    
    args = parser.parse_args()
    
    # Create question extractor
    extractor = QuestionExtractor()
    
    # Extract questions
    questions = extractor.extract_all_questions()
    
    # Filter questions if requested
    if args.ga:
        questions = [q for q in questions if q["ga_folder"] == args.ga]
        if not questions:
            print(f"No questions found in {args.ga}")
            return
        
        if args.script:
            questions = [q for q in questions if q["script_name"] == args.script]
            if not questions:
                print(f"No questions found for {args.ga}/{args.script}")
                return
    
    # Initialize tester
    tester = APITester(api_url=args.url, questions=questions)
    
    # Run in interactive mode if requested
    if args.interactive:
        interactive_test_mode(extractor, tester)
        return
    
    # Run tests
    print(f"Testing {len(questions)} questions...")
    tester.run_tests(parallel=args.parallel, max_workers=args.workers)
    
    # Generate report
    report = tester.generate_report()
    
    # Print summary
    print("\nTest Summary:")
    print(f"Total tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed_tests']}")
    print(f"Failed: {report['summary']['failed_tests']}")
    print(f"Errors: {report['summary']['error_tests']}")
    print(f"Pass rate: {report['summary']['pass_rate']:.2f}%")
    print(f"Average response time: {report['summary']['avg_response_time']:.3f}s")
    
    # Print locations of results
    print(f"\nDetailed results saved to: {report['results_path']}")
    print(f"HTML report saved to: {report['html_path']}")

if __name__ == "__main__":
    main()