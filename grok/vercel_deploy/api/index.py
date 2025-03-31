import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load student data from JSON file
def load_student_data():
    # In Vercel, the JSON file will be in the same directory as this script
    json_path = os.path.join(os.path.dirname(__file__), 'q-vercel-python.json')
    try:
        with open(json_path, 'r') as file:
            students = json.load(file)
            # Create a dictionary for faster lookups while preserving the original data
            student_dict = {student["name"]: student["marks"] for student in students}
            return students, student_dict
    except Exception as e:
        print(f"Error loading student data: {e}")
        return [], {}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Enable CORS for all origins
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        # Parse query parameters
        parsed_url = urlparse(self.path)
        query_string = parsed_url.query
        query_params = parse_qs(query_string)
        
        # Get names from query
        requested_names = query_params.get('name', [])
        
        # Load student data
        students, student_dict = load_student_data()
        
        # If no names are requested, return the whole dataset
        if not requested_names:
            self.wfile.write(json.dumps(students).encode())
            return
            
        # Otherwise, get marks for requested names
        marks = [student_dict.get(name, 0) for name in requested_names]
        
        # Return JSON response
        response = {"marks": marks}
        self.wfile.write(json.dumps(response).encode())
