# 🎯 Vicky - AI-Powered Data Science Assistant# 🎯 IIT MADRAS TDS PROBLEM SOLVER



<div align="center">---



![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)## 🚀 System Architecture & Technology Stack

![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)![image](https://github.com/user-attachments/assets/00702ec0-816c-4706-83e8-8ca3ffe9e46c)

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)![image](https://github.com/user-attachments/assets/cf1b7fcf-5ccd-42a9-84b8-a457177de2fc)

![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)![image](https://github.com/user-attachments/assets/3d0f2fe1-279d-40de-88c0-761b24988110)

![image](https://github.com/user-attachments/assets/20e20c64-a417-445f-ad9f-62eb978ccfc3)

**An intelligent question-answering system built for IIT Madras TDS Course**

### 🏗 Core Components

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API](#-api-reference) • [Deployment](#-deployment)- **Backend Architecture**: Python-based with FastAPI framework

- **Frontend**: Responsive single-page application using HTML5, CSS3, and vanilla JavaScript

</div>- **Integration Layer**: Webhook support for Discord, Slack, and Telegram notifications

- **Data Processing**: Python core libraries with specialized modules for file handling

---- **Question Processing Engine**: Pattern matching algorithm with specialized solvers



## 📋 Overview---



**Vicky** is an AI-powered automation platform that solves **55+ types of data science problems** automatically. Originally built as a course project for IIT Madras BS Data Science program, it evolved into a comprehensive system with pattern matching, file processing, and API integrations.## 📁 Core Files

- 🖥 **vicky_app.py**: Web server, API endpoints, HTML rendering, and system management

### What Makes It Special?- 🧠 **vicky_server.py**: Question analysis, pattern matching, and solution generation



- 🧠 **Intelligent Pattern Matching** - Understands questions and routes to correct solvers---

- 📁 **Multi-Format Processing** - Handles PDF, Excel, CSV, ZIP, images, videos

- 🔗 **10+ API Integrations** - GitHub, IMDb, ESPN, OpenAI, BBC Weather, etc.## 🔍 Technical Implementation Details

- 🤖 **AI Fallback** - Gemini 2.0 Flash for questions outside the knowledge base

- 📡 **Webhook Notifications** - Discord, Slack, Telegram integration### 📡 Communication Infrastructure

#### 1️⃣ Webhook Integration System

---The webhook system uses a buffering mechanism to batch notifications, preventing overload while maintaining detailed logs.



## ✨ Features🔹 **Supported Platforms:**  

✅ **Discord**: Rich message formatting with embedded content  

### 🎓 Assignment Solvers (GA1-GA5)✅ **Telegram**: Direct messages to specified chat IDs  

✅ **Slack**: Interactive messages through incoming webhooks  

| Category | Capabilities |

|----------|-------------|### 🧩 Pattern Matching Engine

| **Data Processing** | Excel cleaning, CSV extraction, JSON sorting, PDF table extraction |The engine uses regex patterns for:

| **File Operations** | Multi-encoding support (UTF-8, UTF-16, CP-1252), ZIP handling |- 📌 **Contextual Understanding**: Detecting specific question types

| **Web Scraping** | IMDb movies, ESPN cricket stats, Hacker News RSS |- 🏷 **Command Recognition**: Identifying code commands and parameters

| **API Integration** | OpenAI embeddings, GitHub search, BBC Weather, Nominatim geocoding |- 📑 **Assignment Classification**: Routing questions to GA1-GA5 solvers

| **Image Processing** | Lossless compression, jigsaw reconstruction, brightness analysis |- 📂 **File Association**: Linking relevant uploaded files

| **Media** | YouTube video transcription, URL content extraction |

### 📂 File Management System

### 🛠️ Technical Features- 🔑 **Generates Unique IDs**: 8-character identifiers for each file

- 🏷 **Stores Metadata**: Tracks filenames, timestamps, and file types

- **Pattern Matching Engine** with domain classification and weighted scoring- 🔗 **Provides Contextual Access**: Allows referencing files by ID

- **File Manager** with type detection and content-based identification- 📌 **Type-Specific Handling**: Different processing for ZIP archives vs. README files

- **Webhook System** with buffered notifications to prevent spam

- **CORS-enabled REST API** for cross-origin requests### 🎨 Base64 Image Decoder/Encoder

- **Docker containerized** for easy deployment- 🔒 **Client-side implementation** for security and performance

- 🏷 **Intelligent Format Detection** for automatic prefix correction

---- 🚀 **Robust Error Handling** for malformed Base64 data

- 📋 **Clipboard Integration** for direct image pasting

## 🚀 Quick Start

### 🌍 HTML Viewer with CORS Proxy

### Prerequisites- 🔓 **Bypass CORS Restrictions** via third-party proxy

- 📜 **Render Live Content** in sandboxed iframe

- Python 3.11+- 📖 **Provide Source Viewing** for analysis

- pip or uv package manager- ✂ **Enable HTML Copying** for modification



### Installation### ⚡ API Layer & Documentation

- 🔹 **Multiple Response Formats**: JSON and HTML output

```bash- 🔹 **File Upload Support**: Process questions with attached files

# Clone the repository- 🔹 **Notification Integration**: Webhook notifications for API calls

git clone https://github.com/algsoch/assistant_chatbot.git- 🔹 **Security Features**: IP logging, optional rate limiting

cd assistant_chatbot

### 🔐 Authentication and Security

# Create virtual environment- 🛡 **IP Logging**: Tracks API and UI interactions

python -m venv venv- 🔑 **Admin Endpoints**: Secure access to logs and analytics

source venv/bin/activate  # On Windows: venv\Scripts\activate- 🔒 **Environment Variables**: Sensitive values stored securely

- ⚠ **XSS Protection**: HTML escaping for user-generated content

# Install dependencies- ✅ **Input Validation**: Thorough validation of user inputs

pip install -r requirements.txt

---

# Set up environment variables

cp .env.example .env## 🎨 User Interface Components

# Edit .env with your API keys

```### 💬 1. Chat Interface

- 💾 **Message History**: Displays assistant conversation

### Running the Server- 📝 **Code Formatting**: Syntax highlighting

- 📂 **File Uploads**: Drag-and-drop and button-based

```bash- 📋 **Copy Functionality**: One-click copying of code blocks

# Quick start script![image](https://github.com/user-attachments/assets/28a7b828-fa45-45a3-8cdc-9ce518489bfa)

./run.sh

### 📌 2. Question Categories & Navigation

# Or manually- 🏷 **Tab-Based Navigation** for easy category switching

python main.py- 🔄 **Dynamic Content Loading** based on selection

- 🎯 **Active State Tracking** for visual feedback

# Or with uvicorn directly![image](https://github.com/user-attachments/assets/e841ce42-2ce6-4591-8134-d96c32ba1f56)

uvicorn vicky_app:app --reload --host 0.0.0.0 --port 8000

```### 📂 3. File Management UI

- 📜 **File Listing**: Shows all uploaded files with metadata

Visit `http://localhost:8000` to access the web interface.- ⚙ **File Actions**: Use or delete files

- 📤 **Upload Interface**: Simple form-based upload

---![image](https://github.com/user-attachments/assets/fda048b4-ece9-4507-821d-f8ef698cca60)



## 🏗️ Architecture---



```## 🔗 Integration Architecture

┌─────────────────────────────────────────────────────────────┐

│                     User Interface                          │### 🔄 1. Server-Client Communication

│              (Web UI / API / Webhooks)                      │- 🌍 **RESTful API Pattern** with:

└─────────────────────────┬───────────────────────────────────┘  - 📜 Form Data: `multipart/form-data` for file uploads

                          │  - 📡 JSON Responses: Structured data

┌─────────────────────────▼───────────────────────────────────┐  - 📄 HTML Responses: Rendered content

│                    vicky_app.py                             │- 📢 **Status Updates** for real-time monitoring

│         FastAPI Server, Routes, HTML Rendering              │

└─────────────────────────┬───────────────────────────────────┘### 🔧 2. External Service Integration

                          │- ✅ **Discord**: Webhook notifications--whenever anybody hit [api](https://app.algsoch.tech/api)

┌─────────────────────────▼───────────────────────────────────┐- ✅ **Slack**: Incoming webhook events--whenever anybody hit [api](https://app.algsoch.tech/api)

│                   vicky_server.py                           │- ✅ **CORS Proxy**: Third-party service for HTML viewing

│     Pattern Matching Engine + 55+ Solution Functions        │- ✅ **Local File System**: Persistent storage for uploads

│                                                             │![image](https://github.com/user-attachments/assets/57cc2a56-ef1f-47bf-adb3-314f69f25238)

│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │

│  │ GA1 Solvers  │  │ GA2 Solvers  │  │ GA3 Solvers  │      │---

│  │  (18 funcs)  │  │  (10 funcs)  │  │  (9 funcs)   │      │

│  └──────────────┘  └──────────────┘  └──────────────┘      │## 🔀 Data Flow Architecture

│  ┌──────────────┐  ┌──────────────┐                        │1️⃣ **User Input**: Question text + optional file upload  

│  │ GA4 Solvers  │  │ GA5 Solvers  │                        │2️⃣ **Pattern Analysis**: Classification of intent  

│  │  (10 funcs)  │  │  (10 funcs)  │                        │3️⃣ **Solver Selection**: Routing to correct solver function  

│  └──────────────┘  └──────────────┘                        │4️⃣ **Response Generation**: Formatted answer creation  

└─────────────────────────────────────────────────────────────┘5️⃣ **Data Enrichment**: Code blocks and structured formatting  

```6️⃣ **Client Delivery**: Rendering in chat interface  



### Project Structure---



```## 📊 Administrative Features

assistant_chatbot/- 📈 **Usage Analytics**: Feature usage statistics

├── main.py              # Entry point with banner- 🔍 **IP Logs**: System access records

├── vicky_app.py         # FastAPI application (7700+ lines)- 📊 **API Statistics**: Endpoint usage data

├── vicky_server.py      # Question engine (14200+ lines)- 📌 **Tool Usage Tracking**: Popularity insights

├── vickys.json          # Question database- 🚨 **Error Monitoring**: Centralized logging

├── requirements.txt     # Python dependencies

├── Dockerfile           # Container configuration---

├── run.sh               # Quick start script

│## 🏆 Conclusion

├── src/                 # Modular source codeThe **Vicky Data Science Assistant Platform** is a **multi-layered system** integrating modern web technologies with an advanced Python backend. The **modular architecture** ensures scalability and easy maintenance, while the **comprehensive API** enables external integrations. Its emphasis on **user experience** and **powerful data processing** makes it a **robust tool for data science education and assistance**. 🚀

│   ├── core/            # Configuration, settings

│   ├── api/             # API routes (future)---

│   ├── solvers/         # Solution functions (future)

│   └── utils/           # Webhooks, helpers# 📜 vicky_server.py Documentation

│

├── static/              # CSS, JS, images## 🔍 Overview

├── templates/           # HTML templates**vicky_server.py** is the core component of the **Vicky Data Science Assistant Platform**, responsible for **question processing, pattern matching, and executing specialized solution functions** for assignments GA1-GA5.

├── config/              # Deployment configs

├── docs/                # Documentation### 📂 Module Structure

├── tests/               # Test suites- 🧩 **GA1 Solutions**: Data processing and file handling

└── _archive/            # Legacy experimental files- 🛠 **GA2 Solutions**: API integration, Docker, FastAPI, and deployment

```- 🔍 **GA3 Solutions**: Network requests, text processing, data manipulation

- 🌐 **GA4 Solutions**: Web scraping, data extraction, automation

---- 📊 **GA5 Solutions**: Advanced data analysis and cleaning operations



## 📡 API ReferenceEach function follows a **consistent structure**, with docstrings documenting parameters, return values, and purpose.



### Main Endpoint---



```http## 📝 Sample Implementations

POST /api

Content-Type: multipart/form-data### 🏞 GA2: Image Compression

``````python

# Compress an image losslessly to be under 1,500 bytes

| Parameter | Type | Description |def ga2_second_solution(query=None):

|-----------|------|-------------|    import os

| `question` | string | The question to answer |    from PIL import Image

| `file` | file | Optional file attachment |    

    default_image_path = "E:\\data science tool\\GA2\\iit_madras.png"

**Response:**    image_path = file_manager.get_file(default_image_path, query, "image")

```json    max_bytes = 1500

{    

  "answer": "The solution to your question..."    with Image.open(image_path) as img:

}        compressed_path = "compressed_output.png"

```        img.save(compressed_path, format="PNG", optimize=True, compress_level=9)

    

### Health Check    return compressed_path

```

```http

GET /api/info### 🎬 GA4: IMDb Web Scraper

``````python

# Extract movie data from IMDb within a specified rating range

### Chat Interfacedef ga4_second_solution(query=None):

    from selenium import webdriver

```http    from selenium.webdriver.chrome.options import Options

POST /chat    

Content-Type: application/json    options = Options()

    options.add_argument("--headless")

{    driver = webdriver.Chrome(options=options)

  "message": "Your question here",    driver.get("https://www.imdb.com/chart/top")

  "history": []    # Scrape and return movies within rating range

}```

```

---

---

## 🎯 Conclusion

## 🐳 DeploymentThe **vicky_server.py** module powers the **Vicky Data Science Assistant** with **pattern recognition** and **specialized solvers**, providing an **efficient and scalable approach** to data science queries. 🚀


### Docker

```bash
# Build and run
docker-compose up -d

# Or using Makefile
make build
make run
```

### Render / Vercel

Configuration files are included:
- `config/render.yaml` - Render deployment
- `vercel_deploy/vercel.json` - Vercel serverless

### Environment Variables

```env
GEMINI_API_KEY=your_gemini_api_key
DISCORD_WEBHOOK=your_discord_webhook
SLACK_WEBHOOK=your_slack_webhook
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 📊 Stats

| Metric | Value |
|--------|-------|
| **Total Lines of Code** | 22,000+ |
| **Solution Functions** | 55+ |
| **File Types Supported** | 15+ |
| **External APIs** | 10+ |
| **Assignment Coverage** | GA1-GA5 (100%) |

---

## 🛣️ Roadmap

- [ ] **Phase 1:** ReAct (Reason + Act) loop implementation
- [ ] **Phase 2:** Tool registry for dynamic tool selection
- [ ] **Phase 3:** Memory system (short-term + long-term)
- [ ] **Phase 4:** Self-correction capabilities
- [ ] **Phase 5:** Full AI Agent architecture

---

## 🤝 Contributing

This is a student project, but contributions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Vicky Kumar**
- BS Data Science @ IIT Madras
- GitHub: [@algsoch](https://github.com/algsoch)

---

<div align="center">

**Built with ❤️ for the IIT Madras TDS Course**

*If you found this helpful, consider giving it a ⭐!*

</div>
