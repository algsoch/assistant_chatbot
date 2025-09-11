import requests

def process_file_question(file_path, question, server_url="http://localhost:8000"):
    """Process a question with a file using the TDS API"""
    url = f"{server_url}/api/process"
    
    # Automatically detect question type from file extension
    question_type = None
    if file_path.lower().endswith('.md'):
        question_type = "npx_readme"  
    elif file_path.lower().endswith('.zip'):
        question_type = "extract_zip"
    
    # Prepare multipart form data with file
    files = {'file': open(file_path, 'rb')}
    data = {'question': question}
    if question_type:
        data['question_type'] = question_type
    
    # Make the API request
    response = requests.post(url, files=files, data=data)
    return response.json()

# Example usage:
if __name__ == "__main__":
    # For GA1 third question (npx README.md)
    result = process_file_question(
        "path/to/README.md", 
        "What is the output of running npx prettier on this README file?"
    )
    print(f"NPX Result: {result['answer']}")
    
    # For GA1 eighth question (extract from ZIP)
    result = process_file_question(
        "path/to/q-extract-csv-zip.zip", 
        "What is the value in the 'answer' column of the CSV file?"
    )
    print(f"ZIP Extract Result: {result['answer']}")