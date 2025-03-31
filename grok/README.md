# Question Execution System

A system for executing questions from questions.py with a chatbot interface. This system allows you to:

- Execute questions from questions.py through a web interface
- Upload required files for questions that need them
- Get real-time responses and error messages
- Interact with a user-friendly chatbot interface

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have a questions.py file in the root directory with your questions and functions.
3. Create the necessary directories:

```bash
mkdir static uploads
```

4. Move the index.html file to the static directory.

## Running the System

1. Start the server:

```bash
python server.py
```

2. Open your web browser and navigate to:

```
http://localhost:8000
```

## Usage

1. The chatbot interface will appear in your browser.
2. If your question requires files:

   - Use the file upload button to upload necessary files
   - Wait for the upload confirmation
3. Type your question in the input field and press Enter or click Send.
4. The system will:

   - Match your question to a function in questions.py
   - Execute the function with any provided parameters
   - Return the result or error message

## API Endpoints

- `GET /` - Serves the chatbot interface
- `POST /execute` - Executes a question
- `POST /upload` - Handles file uploads

## File Structure

```
.
├── server.py           # Main FastAPI server
├── question_api.py     # Question execution logic
├── requirements.txt    # Python dependencies
├── static/            # Static files directory
│   └── index.html     # Chatbot interface
└── uploads/           # Directory for uploaded files
```

## Error Handling

The system provides detailed error messages for:

- Missing questions.py file
- No matching function found
- Function execution errors
- File upload issues

## Contributing

Feel free to submit issues and enhancement requests!
