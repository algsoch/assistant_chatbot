import requests

url = "http://localhost:8000/api/"

# For a simple question
response = requests.post(
    url,
    data={"question": "What is the output of code -s?"}
)
print(response.json())

# For a question with a file
files = {"file": open("path/to/your/file.zip", "rb")}
# data = {"question": "Download q-list-files-attributes.zip and extract it."}
response = requests.post(url)
print(response.json())