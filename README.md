# 🎯 IIT Madras TDS Problem Solver# 🎯 Vicky - AI-Powered Data Science Assistant | IIT MADRAS TDS PROBLEM SOLVER



![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)---



**A rule-based automation system that solves 55+ assignment questions for IIT Madras TDS Course**![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)



🔗 [Live Demo](https://app.algsoch.tech) • [API Endpoint](https://app.algsoch.tech/api)## 🚀 System Architecture & Technology Stack



---![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)![image](https://github.com/user-attachments/assets/00702ec0-816c-4706-83e8-8ca3ffe9e46c)



## 📋 What This Project Does![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)![image](https://github.com/user-attachments/assets/cf1b7fcf-5ccd-42a9-84b8-a457177de2fc)



This is a **pattern matching engine** that automatically solves specific assignment questions from GA1-GA5 of the IIT Madras Tools in Data Science course.![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)![image](https://github.com/user-attachments/assets/3d0f2fe1-279d-40de-88c0-761b24988110)



**Key Point:** This is NOT an AI that "thinks" - it's a deterministic system with 55+ hardcoded solver functions that recognize question patterns and execute the correct solution.![image](https://github.com/user-attachments/assets/20e20c6d-a417-445f-ad9f-62eb978ccfc3)



### How It Works**An intelligent question-answering system built for IIT Madras TDS Course**



```### 🔧 Core Components

User Question → Pattern Matcher → Correct Solver Function → Answer

```[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [API](#api-reference) • [Deployment](#deployment)



1. User submits a question (with optional file)- **Backend Architecture**: Python-based with FastAPI framework

2. Pattern matching engine identifies the question type

3. Routes to the correct solver function (e.g., `ga1_first_solution()`)- **Frontend**: Responsive single-page application using HTML5, CSS3, and vanilla JavaScript

4. Executes the solution and returns the answer

- **Integration Layer**: Webhook support for Discord, Slack, and Telegram notifications

---

- **Data Processing**: Python core libraries with specialized modules for file handling

## 🏗️ Architecture

- **Question Processing Engine**: Pattern matching algorithm with specialized solvers

### Core Files (Everything else is extra)

## 📋 Overview

| File | Lines | Purpose |

|------|-------|---------|Vicky is an advanced AI assistant specifically designed to help students with the IIT Madras Tools in Data Science (TDS) course. Built with FastAPI and powered by Groq's LLaMA model, it provides instant, accurate answers to course-related questions.

| `vicky_app.py` | 7,700+ | FastAPI server, API endpoints, web interface |

| `vicky_server.py` | 14,200+ | Pattern matching + 55 solver functions |### ✨ Key Features

| `vickys.json` | - | Question database for pattern matching |

- 🤖 **Intelligent Q&A**: Context-aware responses using advanced NLP

### What Each Component Does- 📚 **Course-Specific**: Tailored for IIT Madras TDS curriculum

- ⚡ **Fast Response**: Sub-second query processing

```- 🎨 **Modern UI**: Clean, responsive interface

┌─────────────────────────────────────────────────────────┐- 🔔 **Multi-Platform Notifications**: Discord, Slack, and Telegram integration

│                    vicky_app.py                         │- 🐳 **Docker Ready**: Easy deployment with containerization

│         FastAPI Server + Web Interface                  │- 🔒 **Secure**: API key authentication and rate limiting

│    • /api endpoint for questions                        │

│    • /chat endpoint for Gemini chatbot (feedback only)  │## 🏗️ Architecture

│    • Discord/Slack webhook notifications                │

└─────────────────────────┬───────────────────────────────┘```

                          │┌─────────────────┐

┌─────────────────────────▼───────────────────────────────┐│   Frontend UI   │

│                   vicky_server.py                       ││  (HTML/CSS/JS)  │

│            Pattern Matching Engine                      │└────────┬────────┘

│                                                         │         │

│   Question → Pattern Match → Solver Function → Answer   │         ▼

│                                                         │┌─────────────────┐

│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      ││   FastAPI App   │

│   │   GA1   │ │   GA2   │ │   GA3   │ │   GA4   │      ││  (Backend API)  │

│   │18 funcs │ │10 funcs │ │ 9 funcs │ │10 funcs │      │└────────┬────────┘

│   └─────────┘ └─────────┘ └─────────┘ └─────────┘      │         │

│   ┌─────────┐                                          │         ├─────────────┐

│   │   GA5   │                                          │         ▼             ▼

│   │10 funcs │                                          │┌──────────────┐  ┌──────────────┐

│   └─────────┘                                          ││  Groq LLM    │  │  Webhook     │

└─────────────────────────────────────────────────────────┘│  Integration │  │  Service     │

```└──────────────┘  └──────────────┘

```

### About Gemini API

## 🚀 Quick Start

The Gemini API is **only used for the chatbot feature** (`/chat` endpoint) - for general conversation and feedback. It does **NOT** solve the assignment questions. All 55+ question types are solved by hardcoded Python functions.

### Prerequisites

---

- Python 3.11+

## ✨ Features- Groq API key

- Docker (optional)

### Assignment Coverage (GA1-GA5)

### Installation

| Assignment | Questions | Example Topics |

|------------|-----------|----------------|1. Clone the repository

| **GA1** | 18 | VS Code, Git, CSV processing, JSON sorting |```bash

| **GA2** | 10 | Image compression, API integration, Docker |git clone https://github.com/algsoch/assistant_chatbot.git

| **GA3** | 9 | Web scraping, HTTP requests, data extraction |cd assistant_chatbot

| **GA4** | 10 | IMDb scraping, Wikipedia, BBC Weather API |```

| **GA5** | 10 | Excel cleaning, PDF extraction, data analysis |

2. Create virtual environment

### Technical Capabilities```bash

python -m venv venv

- **File Processing**: CSV, Excel, PDF, ZIP, imagessource venv/bin/activate  # On Windows: venv\Scripts\activate

- **Web Scraping**: IMDb, ESPN, Hacker News, Wikipedia```

- **API Integration**: GitHub, BBC Weather, OpenAI embeddings

- **Image Processing**: Compression, brightness analysis3. Install dependencies

- **Video**: YouTube transcript extraction```bash

pip install -r requirements.txt

### Webhook Notifications```



Every API call triggers notifications to:4. Set up environment variables

- Discord (rich embeds)```bash

- Slack (incoming webhooks)cp .env.example .env

- Telegram (bot messages)# Edit .env with your Groq API key

```

---

5. Run the application

## 🚀 Quick Start```bash

uvicorn app.main:app --reload

### Prerequisites```



- Python 3.11+Visit `http://localhost:8000` to use the assistant!

- pip

## 🐳 Docker Deployment

### Installation

```bash

```bash# Build the image

# Clonedocker build -t vicky-assistant .

git clone https://github.com/algsoch/assistant_chatbot.git

cd assistant_chatbot# Run the container

docker run -p 8000:8000 --env-file .env vicky-assistant

# Virtual environment```

python -m venv venv

source venv/bin/activate  # Windows: venv\Scripts\activate## 📚 API Reference



# Dependencies### Ask Question

pip install -r requirements.txt

**POST** `/ask`

# Run

python main.py```json

# or{

./run.sh  "question": "What is pandas in Python?"

```}

```

Visit `http://localhost:8000`

**Response:**

### Environment Variables (Optional)```json

{

```env  "answer": "Pandas is a powerful data manipulation library...",

GEMINI_API_KEY=your_key          # For chatbot feature only  "timestamp": "2025-11-25T18:00:00Z"

DISCORD_WEBHOOK=your_webhook     # Notifications}

SLACK_WEBHOOK=your_webhook       # Notifications```

```

### Health Check

---

**GET** `/health`

## 📡 API Reference

```json

### Solve a Question{

  "status": "healthy",

```http  "version": "1.0.0"

POST /api}

Content-Type: multipart/form-data```



question: "Your question text"## 🎯 Usage Examples

file: (optional file attachment)

```### Python SDK



**Response:**```python

import requests

```json

{response = requests.post(

  "answer": "The solution..."    "http://localhost:8000/ask",

}    json={"question": "Explain numpy arrays"}

```)

print(response.json()["answer"])

### Chat (Gemini - feedback only)```



```http### cURL

POST /chat

Content-Type: application/json```bash

curl -X POST http://localhost:8000/ask \

{  -H "Content-Type: application/json" \

  "message": "Your message",  -d '{"question":"What is machine learning?"}'

  "history": []```

}

```## 🔔 Webhook Integration



### Health CheckConfigure webhooks in `.env`:



```http```env

GET /api/infoDISCORD_WEBHOOK_URL=your_discord_webhook_url

```SLACK_WEBHOOK_URL=your_slack_webhook_url

TELEGRAM_BOT_TOKEN=your_telegram_bot_token

---```



## 🐳 Deployment## 📁 Project Structure



### Docker```

assistant_chatbot/

```bash│

docker-compose up -d├── app/

```│   ├── main.py              # FastAPI application

│   ├── models.py            # Data models

### Render│   ├── groq_client.py       # Groq API integration

│   └── webhooks.py          # Notification services

Uses `config/render.yaml`│

├── static/

### Project Structure│   ├── index.html           # Frontend UI

│   ├── style.css            # Styling

```│   └── script.js            # JavaScript logic

assistant_chatbot/│

├── vicky_app.py         # Main server (7700+ lines)├── tests/

├── vicky_server.py      # Question engine (14200+ lines)│   └── test_api.py          # API tests

├── vickys.json          # Question patterns│

├── main.py              # Entry point├── Dockerfile               # Docker configuration

├── requirements.txt     # Dependencies├── requirements.txt         # Python dependencies

├── Dockerfile           # Container config├── .env.example            # Environment template

├── static/              # CSS, JS└── README.md               # This file

├── templates/           # HTML templates```

├── config/              # Deployment configs

├── docs/                # Documentation## 🛠️ Technologies Used

├── tests/               # Test files

└── _archive/            # Old experimental files- **Backend**: FastAPI, Python 3.11+

```- **AI Model**: Groq LLaMA 3.1-70B

- **Frontend**: HTML5, CSS3, Vanilla JavaScript

---- **Deployment**: Docker, Uvicorn

- **Testing**: Pytest

## 📊 Stats- **Webhooks**: Discord, Slack, Telegram



| Metric | Value |## 📊 Features in Detail

|--------|-------|

| **Lines of Code** | 22,000+ |### Intelligent Context Understanding

| **Solver Functions** | 55+ |

| **Assignments Covered** | GA1-GA5 (100%) |Vicky uses advanced NLP techniques to:

| **File Types** | 15+ |- Understand context from previous questions

- Provide relevant follow-up suggestions

---- Handle ambiguous queries intelligently



## ⚠️ Limitations### Course-Specific Knowledge Base



- This solves **specific** IIT Madras TDS assignment questions onlyOptimized for:

- Pattern matching may fail on rephrased questions- Python programming concepts

- Not a general-purpose AI assistant- Data analysis with pandas, numpy

- Gemini chatbot is just for conversation, not problem-solving- Statistical methods

- Machine learning basics

---- Data visualization



## 👨‍💻 Author## 🤝 Contributing



**Vicky Kumar**  Contributions are welcome! Please follow these steps:

BS Data Science @ IIT Madras  

GitHub: [@algsoch](https://github.com/algsoch)1. Fork the repository

2. Create a feature branch (`git checkout -b feature/amazing-feature`)

---3. Commit your changes (`git commit -m "Add amazing feature"`)

4. Push to the branch (`git push origin feature/amazing-feature`)

**Built for IIT Madras TDS Course**5. Open a Pull Request


---

## 📜 License

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
