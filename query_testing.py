import json
import csv
import requests
import os
from pathlib import Path
import time

def query_tds_api(questions_file, output_csv):
    """
    Query the TDS API with questions from a JSON file and save results to CSV
    
    Args:
        questions_file: Path to the JSON file containing questions
        output_csv: Path to save the CSV output
    """
    # Load questions from JSON file
    print(f"Loading questions from {questions_file}")
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)
    
    # Prepare CSV file
    fieldnames = ['file', 'question', 'answer']
    with open(output_csv, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process each question
        total = len(questions_data)
        for i, q_data in enumerate(questions_data, 1):
            file_path = q_data.get('file', '')
            question = q_data.get('question', '')
            
            if not question:
                continue
                
            print(f"[{i}/{total}] Processing: {question[:50]}..." + ("" if len(question) < 50 else "..."))
            
            # Prepare request data
            data = {'question': question}
            files = {}
            
            # If file exists, attach it
            if file_path and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                files = {'file': (file_name, open(file_path, 'rb'))}
                print(f"  Attaching file: {file_name}")
            
            try:
                # Make API request
                response = requests.post(
                    "https://app.algsoch.tech/api/", 
                    data=data,
                    files=files
                )
                
                # Process response
                if response.status_code == 200:
                    answer = response.json().get('answer', 'No answer received')
                    print(f"  Got answer: {answer[:50]}..." + ("" if len(answer) < 50 else "..."))
                else:
                    answer = f"Error {response.status_code}: {response.text}"
                    print(f"  Error: {answer}")
                
                # Write to CSV
                writer.writerow({
                    'file': file_path,
                    'question': question,
                    'answer': answer
                })
                
                # Close file if it was opened
                if 'file' in files and not files['file'][1].closed:
                    files['file'][1].close()
                
                # Brief pause to avoid overwhelming the server
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  Failed to process question: {e}")
                writer.writerow({
                    'file': file_path,
                    'question': question,
                    'answer': f"Error: {str(e)}"
                })
    
    print(f"\nProcessing complete! Results saved to {output_csv}")

if __name__ == "__main__":
    # Set file paths
    questions_file = "vickys.json"
    output_csv = "tds_api_results.csv"
    
    # Run the query process
    query_tds_api(questions_file, output_csv)