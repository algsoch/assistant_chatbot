# 🎯 IIT MADRAS TDS PROBLEM SOLVER

---

## 🚀 System Architecture & Technology Stack
![image](https://github.com/user-attachments/assets/00702ec0-816c-4706-83e8-8ca3ffe9e46c)
![image](https://github.com/user-attachments/assets/cf1b7fcf-5ccd-42a9-84b8-a457177de2fc)
![image](https://github.com/user-attachments/assets/3d0f2fe1-279d-40de-88c0-761b24988110)
![image](https://github.com/user-attachments/assets/20e20c64-a417-445f-ad9f-62eb978ccfc3)

### 🏗 Core Components
- **Backend Architecture**: Python-based with FastAPI framework
- **Frontend**: Responsive single-page application using HTML5, CSS3, and vanilla JavaScript
- **Integration Layer**: Webhook support for Discord, Slack, and Telegram notifications
- **Data Processing**: Python core libraries with specialized modules for file handling
- **Question Processing Engine**: Pattern matching algorithm with specialized solvers

---

## 📁 Core Files
- 🖥 **vicky_app.py**: Web server, API endpoints, HTML rendering, and system management
- 🧠 **vicky_server.py**: Question analysis, pattern matching, and solution generation

---

## 🔍 Technical Implementation Details

### 📡 Communication Infrastructure
#### 1️⃣ Webhook Integration System
The webhook system uses a buffering mechanism to batch notifications, preventing overload while maintaining detailed logs.

🔹 **Supported Platforms:**  
✅ **Discord**: Rich message formatting with embedded content  
✅ **Telegram**: Direct messages to specified chat IDs  
✅ **Slack**: Interactive messages through incoming webhooks  

### 🧩 Pattern Matching Engine
The engine uses regex patterns for:
- 📌 **Contextual Understanding**: Detecting specific question types
- 🏷 **Command Recognition**: Identifying code commands and parameters
- 📑 **Assignment Classification**: Routing questions to GA1-GA5 solvers
- 📂 **File Association**: Linking relevant uploaded files

### 📂 File Management System
- 🔑 **Generates Unique IDs**: 8-character identifiers for each file
- 🏷 **Stores Metadata**: Tracks filenames, timestamps, and file types
- 🔗 **Provides Contextual Access**: Allows referencing files by ID
- 📌 **Type-Specific Handling**: Different processing for ZIP archives vs. README files

### 🎨 Base64 Image Decoder/Encoder
- 🔒 **Client-side implementation** for security and performance
- 🏷 **Intelligent Format Detection** for automatic prefix correction
- 🚀 **Robust Error Handling** for malformed Base64 data
- 📋 **Clipboard Integration** for direct image pasting

### 🌍 HTML Viewer with CORS Proxy
- 🔓 **Bypass CORS Restrictions** via third-party proxy
- 📜 **Render Live Content** in sandboxed iframe
- 📖 **Provide Source Viewing** for analysis
- ✂ **Enable HTML Copying** for modification

### ⚡ API Layer & Documentation
- 🔹 **Multiple Response Formats**: JSON and HTML output
- 🔹 **File Upload Support**: Process questions with attached files
- 🔹 **Notification Integration**: Webhook notifications for API calls
- 🔹 **Security Features**: IP logging, optional rate limiting

### 🔐 Authentication and Security
- 🛡 **IP Logging**: Tracks API and UI interactions
- 🔑 **Admin Endpoints**: Secure access to logs and analytics
- 🔒 **Environment Variables**: Sensitive values stored securely
- ⚠ **XSS Protection**: HTML escaping for user-generated content
- ✅ **Input Validation**: Thorough validation of user inputs

---

## 🎨 User Interface Components

### 💬 1. Chat Interface
- 💾 **Message History**: Displays assistant conversation
- 📝 **Code Formatting**: Syntax highlighting
- 📂 **File Uploads**: Drag-and-drop and button-based
- 📋 **Copy Functionality**: One-click copying of code blocks
![image](https://github.com/user-attachments/assets/28a7b828-fa45-45a3-8cdc-9ce518489bfa)

### 📌 2. Question Categories & Navigation
- 🏷 **Tab-Based Navigation** for easy category switching
- 🔄 **Dynamic Content Loading** based on selection
- 🎯 **Active State Tracking** for visual feedback
![image](https://github.com/user-attachments/assets/e841ce42-2ce6-4591-8134-d96c32ba1f56)

### 📂 3. File Management UI
- 📜 **File Listing**: Shows all uploaded files with metadata
- ⚙ **File Actions**: Use or delete files
- 📤 **Upload Interface**: Simple form-based upload
![image](https://github.com/user-attachments/assets/fda048b4-ece9-4507-821d-f8ef698cca60)

---

## 🔗 Integration Architecture

### 🔄 1. Server-Client Communication
- 🌍 **RESTful API Pattern** with:
  - 📜 Form Data: `multipart/form-data` for file uploads
  - 📡 JSON Responses: Structured data
  - 📄 HTML Responses: Rendered content
- 📢 **Status Updates** for real-time monitoring

### 🔧 2. External Service Integration
- ✅ **Discord**: Webhook notifications--whenever anybody hit [api](https://app.algsoch.tech/api)
- ✅ **Slack**: Incoming webhook events--whenever anybody hit [api](https://app.algsoch.tech/api)
- ✅ **CORS Proxy**: Third-party service for HTML viewing
- ✅ **Local File System**: Persistent storage for uploads
![image](https://github.com/user-attachments/assets/57cc2a56-ef1f-47bf-adb3-314f69f25238)

---

## 🔀 Data Flow Architecture
1️⃣ **User Input**: Question text + optional file upload  
2️⃣ **Pattern Analysis**: Classification of intent  
3️⃣ **Solver Selection**: Routing to correct solver function  
4️⃣ **Response Generation**: Formatted answer creation  
5️⃣ **Data Enrichment**: Code blocks and structured formatting  
6️⃣ **Client Delivery**: Rendering in chat interface  

---

## 📊 Administrative Features
- 📈 **Usage Analytics**: Feature usage statistics
- 🔍 **IP Logs**: System access records
- 📊 **API Statistics**: Endpoint usage data
- 📌 **Tool Usage Tracking**: Popularity insights
- 🚨 **Error Monitoring**: Centralized logging

---

## 🏆 Conclusion
The **Vicky Data Science Assistant Platform** is a **multi-layered system** integrating modern web technologies with an advanced Python backend. The **modular architecture** ensures scalability and easy maintenance, while the **comprehensive API** enables external integrations. Its emphasis on **user experience** and **powerful data processing** makes it a **robust tool for data science education and assistance**. 🚀

---

# 📜 vicky_server.py Documentation

## 🔍 Overview
**vicky_server.py** is the core component of the **Vicky Data Science Assistant Platform**, responsible for **question processing, pattern matching, and executing specialized solution functions** for assignments GA1-GA5.

### 📂 Module Structure
- 🧩 **GA1 Solutions**: Data processing and file handling
- 🛠 **GA2 Solutions**: API integration, Docker, FastAPI, and deployment
- 🔍 **GA3 Solutions**: Network requests, text processing, data manipulation
- 🌐 **GA4 Solutions**: Web scraping, data extraction, automation
- 📊 **GA5 Solutions**: Advanced data analysis and cleaning operations

Each function follows a **consistent structure**, with docstrings documenting parameters, return values, and purpose.

---

## 📝 Sample Implementations

### 🏞 GA2: Image Compression
```python
# Compress an image losslessly to be under 1,500 bytes
def ga2_second_solution(query=None):
    import os
    from PIL import Image
    
    default_image_path = "E:\\data science tool\\GA2\\iit_madras.png"
    image_path = file_manager.get_file(default_image_path, query, "image")
    max_bytes = 1500
    
    with Image.open(image_path) as img:
        compressed_path = "compressed_output.png"
        img.save(compressed_path, format="PNG", optimize=True, compress_level=9)
    
    return compressed_path
```

### 🎬 GA4: IMDb Web Scraper
```python
# Extract movie data from IMDb within a specified rating range
def ga4_second_solution(query=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.imdb.com/chart/top")
    # Scrape and return movies within rating range
```

---

## 🎯 Conclusion
The **vicky_server.py** module powers the **Vicky Data Science Assistant** with **pattern recognition** and **specialized solvers**, providing an **efficient and scalable approach** to data science queries. 🚀
