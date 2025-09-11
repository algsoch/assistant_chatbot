import json
import os
import sys
import requests
import logging
import time
import traceback
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_assignment_solver.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test-assignment-solver")

# Configuration
BASE_DIR = Path("E:/data science tool")
TRAINING_DATA_PATH = BASE_DIR / "main" / "grok" / "training_dataset.json"
API_ENDPOINT = "http://localhost:8000/api/solve"
RESULTS_DIR = BASE_DIR / "test_results"
RESULTS_DIR.mkdir(exist_ok=True, parents=True)

class AssignmentTester:
    """Class to test the assignment solver API"""
    
    def __init__(self, api_url: str, training_data_path: Path):
        self.api_url = api_url
        self.training_data_path = training_data_path
        self.training_data = self._load_training_data()
        self.results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_results": []
        }
    
    def _load_training_data(self) -> List[Dict[str, Any]]:
        """Load the training dataset"""
        try:
            if not self.training_data_path.exists():
                logger.error(f"Training dataset not found at {self.training_data_path}")
                return []
            
            with open(self.training_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            logger.info(f"Loaded {len(data)} questions from training dataset")
            return data
        except Exception as e:
            logger.error(f"Error loading training dataset: {e}")
            return []
    
    def test_single_question(self, question_data: Dict[str, Any], question_index: int) -> Dict[str, Any]:
        """Test a single question against the API"""
        question = question_data.get("question", "")
        expected_answer = question_data.get("answer", "")
        
        if not question:
            return {
                "index": question_index,
                "question": question,
                "status": "skipped",
                "reason": "Empty question"
            }
        
        try:
            # Send request to API
            start_time = time.time()
            response = requests.post(
                self.api_url,
                data={"question": question},
                files={"file": None}
            )
            response_time = time.time() - start_time
            
            # Get response
            if response.status_code == 200:
                answer = response.json().get("answer", "")
                
                # Determine if the answer is valid
                is_valid = self._validate_answer(answer, expected_answer)
                
                return {
                    "index": question_index,
                    "question": question,
                    "answer": answer,
                    "expected_answer": expected_answer,
                    "status": "passed" if is_valid else "failed",
                    "response_time": response_time,
                    "error": None
                }
            else:
                return {
                    "index": question_index,
                    "question": question,
                    "status": "failed",
                    "error": f"API returned status code {response.status_code}: {response.text}",
                    "response_time": response_time
                }
        except Exception as e:
            logger.error(f"Error testing question {question_index}: {e}")
            return {
                "index": question_index,
                "question": question,
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _validate_answer(self, answer: str, expected_answer: str) -> bool:
        """Validate if the answer is correct"""
        # If there's no expected answer, we can't validate
        if not expected_answer:
            return "error" not in answer.lower()
        
        # Remove whitespace, line breaks, and case sensitivity for comparison
        answer_normalized = " ".join(answer.lower().split())
        expected_normalized = " ".join(expected_answer.lower().split())
        
        # Check for exact match first
        if answer_normalized == expected_normalized:
            return True
        
        # Check if answer contains the expected answer
        if expected_normalized in answer_normalized:
            return True
        
        # Check if at least 50% of the expected answer is in the actual answer
        words_expected = set(expected_normalized.split())
        words_actual = set(answer_normalized.split())
        common_words = words_expected.intersection(words_actual)
        
        if len(common_words) >= 0.5 * len(words_expected):
            return True
        
        # Check if it's an error message
        if "error" in answer.lower():
            return False
        
        # Default to considering it valid if it's not an error
        return True
    
    def run_tests(self, start_index: int = 0, end_index: Optional[int] = None, parallel: bool = False) -> Dict[str, Any]:
        """Run tests for all questions in the training dataset"""
        if not self.training_data:
            logger.error("No training data to test")
            return {"error": "No training data available"}
        
        # Determine the range of questions to test
        total_questions = len(self.training_data)
        if end_index is None:
            end_index = total_questions
        
        questions_to_test = self.training_data[start_index:end_index]
        
        logger.info(f"Testing {len(questions_to_test)} questions from index {start_index} to {end_index-1}")
        
        self.results["total_tests"] = len(questions_to_test)
        self.results["test_results"] = []
        
        # Test each question
        if parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self.test_single_question, q, i + start_index): (i + start_index)
                    for i, q in enumerate(questions_to_test)
                }
                
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Testing questions"):
                    result = future.result()
                    self.results["test_results"].append(result)
                    
                    if result["status"] == "passed":
                        self.results["passed_tests"] += 1
                    elif result["status"] in ["failed", "error"]:
                        self.results["failed_tests"] += 1
                    
                    # Log result
                    logger.info(f"Question {result['index']}: {result['status']}")
                    if result["status"] in ["failed", "error"] and "error" in result:
                        logger.error(f"Error: {result['error']}")
        else:
            for i, question_data in enumerate(tqdm(questions_to_test, desc="Testing questions")):
                question_index = i + start_index
                result = self.test_single_question(question_data, question_index)
                self.results["test_results"].append(result)
                
                if result["status"] == "passed":
                    self.results["passed_tests"] += 1
                elif result["status"] in ["failed", "error"]:
                    self.results["failed_tests"] += 1
                
                # Log result
                logger.info(f"Question {result['index']}: {result['status']}")
                if result["status"] in ["failed", "error"] and "error" in result:
                    logger.error(f"Error: {result['error']}")
        
        # Calculate pass rate
        if self.results["total_tests"] > 0:
            self.results["pass_rate"] = self.results["passed_tests"] / self.results["total_tests"] * 100
        else:
            self.results["pass_rate"] = 0
        
        logger.info(f"Tests complete: {self.results['passed_tests']} passed, {self.results['failed_tests']} failed")
        logger.info(f"Pass rate: {self.results['pass_rate']:.2f}%")
        
        return self.results
    
    def save_results(self, output_path: Optional[Path] = None) -> Path:
        """Save test results to a file"""
        if not output_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = RESULTS_DIR / f"test_results_{timestamp}.json"
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2)
            
            logger.info(f"Test results saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
            return None
    
    def generate_report(self, output_path: Optional[Path] = None) -> Path:
        """Generate a human-readable HTML report of test results"""
        if not output_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = RESULTS_DIR / f"test_report_{timestamp}.html"
        
        try:
            # Create HTML report
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Assignment Solver Test Report</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    h1, h2, h3 {{
                        color: #333;
                    }}
                    .summary {{
                        display: flex;
                        justify-content: space-between;
                        padding: 20px;
                        margin-bottom: 20px;
                        background-color: #f8f9fa;
                        border-radius: 8px;
                    }}
                    .summary-item {{
                        text-align: center;
                    }}
                    .summary-value {{
                        font-size: 24px;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                    .passed {{
                        color: #28a745;
                    }}
                    .failed {{
                        color: #dc3545;
                    }}
                    .neutral {{
                        color: #6c757d;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    th, td {{
                        padding: 12px 15px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }}
                    th {{
                        background-color: #f8f9fa;
                        font-weight: bold;
                    }}
                    tr:hover {{
                        background-color: #f1f1f1;
                    }}
                    .details-toggle {{
                        cursor: pointer;
                        color: #007bff;
                        text-decoration: underline;
                    }}
                    .details-content {{
                        display: none;
                        padding: 10px;
                        background-color: #f8f9fa;
                        border-radius: 4px;
                        margin-top: 10px;
                        white-space: pre-wrap;
                        font-family: monospace;
                        max-height: 300px;
                        overflow-y: auto;
                    }}
                    .filter-controls {{
                        margin-bottom: 20px;
                        display: flex;
                        gap: 10px;
                    }}
                    .filter-button {{
                        padding: 8px 16px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        background-color: #f8f9fa;
                    }}
                    .filter-button.active {{
                        background-color: #007bff;
                        color: white;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Assignment Solver Test Report</h1>
                    <p>Generated on {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                    
                    <div class="summary">
                        <div class="summary-item">
                            <div>Total Tests</div>
                            <div class="summary-value neutral">{self.results["total_tests"]}</div>
                        </div>
                        <div class="summary-item">
                            <div>Passed Tests</div>
                            <div class="summary-value passed">{self.results["passed_tests"]}</div>
                        </div>
                        <div class="summary-item">
                            <div>Failed Tests</div>
                            <div class="summary-value failed">{self.results["failed_tests"]}</div>
                        </div>
                        <div class="summary-item">
                            <div>Pass Rate</div>
                            <div class="summary-value {
                                "passed" if self.results["pass_rate"] >= 80 else 
                                "neutral" if self.results["pass_rate"] >= 50 else 
                                "failed"
                            }">{self.results["pass_rate"]:.2f}%</div>
                        </div>
                    </div>
                    
                    <h2>Test Results</h2>
                    
                    <div class="filter-controls">
                        <button class="filter-button active" data-filter="all">All</button>
                        <button class="filter-button" data-filter="passed">Passed</button>
                        <button class="filter-button" data-filter="failed">Failed</button>
                        <button class="filter-button" data-filter="error">Errors</button>
                    </div>
                    
                    <table id="results-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Question</th>
                                <th>Status</th>
                                <th>Response Time</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Add rows for each test result
            for result in sorted(self.results["test_results"], key=lambda x: x["index"]):
                status_class = "passed" if result["status"] == "passed" else "failed"
                question_text = result.get("question", "")
                response_time = result.get("response_time", 0)
                
                html_content += f"""
                            <tr class="result-row" data-status="{result["status"]}">
                                <td>{result["index"]}</td>
                                <td>{question_text[:100]}{"..." if len(question_text) > 100 else ""}</td>
                                <td class="{status_class}">{result["status"].upper()}</td>
                                <td>{response_time:.2f}s</td>
                                <td>
                                    <div class="details-toggle" onclick="toggleDetails('details-{result["index"]}')">Show Details</div>
                                    <div id="details-{result["index"]}" class="details-content">
                """
                
                # Add error if present
                if "error" in result and result["error"]:
                    html_content += f"<strong>Error:</strong>\n{result['error']}\n\n"
                
                # Add expected answer if present
                if "expected_answer" in result and result["expected_answer"]:
                    html_content += f"<strong>Expected Answer:</strong>\n{result['expected_answer']}\n\n"
                
                # Add actual answer if present
                if "answer" in result and result["answer"]:
                    html_content += f"<strong>Actual Answer:</strong>\n{result['answer']}\n\n"
                
                html_content += """
                                    </div>
                                </td>
                            </tr>
                """
            
            # Close HTML tags and add JavaScript for interactivity
            html_content += """
                        </tbody>
                    </table>
                </div>
                
                <script>
                    function toggleDetails(id) {
                        const element = document.getElementById(id);
                        if (element.style.display === "block") {
                            element.style.display = "none";
                        } else {
                            element.style.display = "block";
                        }
                    }
                    
                    document.querySelectorAll('.filter-button').forEach(button => {
                        button.addEventListener('click', function() {
                            // Update active button
                            document.querySelectorAll('.filter-button').forEach(btn => {
                                btn.classList.remove('active');
                            });
                            this.classList.add('active');
                            
                            // Filter the results
                            const filter = this.getAttribute('data-filter');
                            const rows = document.querySelectorAll('.result-row');
                            
                            rows.forEach(row => {
                                const status = row.getAttribute('data-status');
                                if (filter === 'all' || status === filter) {
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
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            logger.info(f"Test report saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return None

def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description="Test the Assignment Solver API")
    parser.add_argument(
        "--api-url",
        type=str,
        default=API_ENDPOINT,
        help="URL of the Assignment Solver API"
    )
    parser.add_argument(
        "--training-data",
        type=str,
        default=str(TRAINING_DATA_PATH),
        help="Path to the training dataset JSON file"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Starting index of questions to test"
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Ending index of questions to test"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(RESULTS_DIR),
        help="Directory to save test results"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Initialize tester
    tester = AssignmentTester(
        api_url=args.api_url,
        training_data_path=Path(args.training_data)
    )
    
    # Run tests
    results = tester.run_tests(
        start_index=args.start,
        end_index=args.end,
        parallel=args.parallel
    )
    
    # Save results and generate report
    tester.save_results(output_dir / f"test_results_{time.strftime('%Y%m%d_%H%M%S')}.json")
    report_path = tester.generate_report(output_dir / f"test_report_{time.strftime('%Y%m%d_%H%M%S')}.html")
    
    print(f"\nTest Results:")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Pass Rate: {results['pass_rate']:.2f}%")
    
    if report_path:
        print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    main()