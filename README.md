# 🎯 Vicky - AI-Powered Data Science Assistant | IIT MADRAS TDS PROBLEM SOLVER

<div align="center">

---

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)

## 🚀 System Architecture & Technology Stack

![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)![image](https://github.com/user-attachments/assets/00702ec0-816c-4706-83e8-8ca3ffe9e46c)

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)![image](https://github.com/user-attachments/assets/cf1b7fcf-5ccd-42a9-84b8-a457177de2fc)

![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)![image](https://github.com/user-attachments/assets/3d0f2fe1-279d-40de-88c0-761b24988110)

![image](https://github.com/user-attachments/assets/20e20c6d-a417-445f-ad9f-62eb978ccfc3)

**An intelligent question-answering system built for IIT Madras TDS Course**

### 🔧 Core Components

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [API](#api-reference) • [Deployment](#deployment)

- **Backend Architecture**: Python-based with FastAPI framework

- **Frontend**: Responsive single-page application using HTML5, CSS3, and vanilla JavaScript

- **Integration Layer**: Webhook support for Discord, Slack, and Telegram notifications

- **Data Processing**: Python core libraries with specialized modules for file handling

- **Question Processing Engine**: Pattern matching algorithm with specialized solvers

## 📋 Overview

Vicky is an advanced AI assistant specifically designed to help students with the IIT Madras Tools in Data Science (TDS) course. Built with FastAPI and powered by Groq's LLaMA model, it provides instant, accurate answers to course-related questions.

### ✨ Key Features

- 🤖 **Intelligent Q&A**: Context-aware responses using advanced NLP
- 📚 **Course-Specific**: Tailored for IIT Madras TDS curriculum
- ⚡ **Fast Response**: Sub-second query processing
- 🎨 **Modern UI**: Clean, responsive interface
- 🔔 **Multi-Platform Notifications**: Discord, Slack, and Telegram integration
- 🐳 **Docker Ready**: Easy deployment with containerization
- 🔒 **Secure**: API key authentication and rate limiting

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend UI   │
│  (HTML/CSS/JS)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI App   │
│  (Backend API)  │
└────────┬────────┘
         │
         ├─────────────┐
         ▼             ▼
┌──────────────┐  ┌──────────────┐
│  Groq LLM    │  │  Webhook     │
│  Integration │  │  Service     │
└──────────────┘  └──────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Groq API key
- Docker (optional)

### Installation

1. Clone the repository
```bash
git clone https://github.com/algsoch/assistant_chatbot.git
cd assistant_chatbot
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your Groq API key
```

5. Run the application
```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` to use the assistant!

## 🐳 Docker Deployment

```bash
# Build the image
docker build -t vicky-assistant .

# Run the container
docker run -p 8000:8000 --env-file .env vicky-assistant
```

## 📚 API Reference

### Ask Question

**POST** `/ask`

```json
{
  "question": "What is pandas in Python?"
}
```

**Response:**
```json
{
  "answer": "Pandas is a powerful data manipulation library...",
  "timestamp": "2025-11-25T18:00:00Z"
}
```

### Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## 🎯 Usage Examples

### Python SDK

```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "Explain numpy arrays"}
)
print(response.json()["answer"])
```

### cURL

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is machine learning?"}'
```

## 🔔 Webhook Integration

Configure webhooks in `.env`:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SLACK_WEBHOOK_URL=your_slack_webhook_url
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

## 📁 Project Structure

```
assistant_chatbot/
│
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Data models
│   ├── groq_client.py       # Groq API integration
│   └── webhooks.py          # Notification services
│
├── static/
│   ├── index.html           # Frontend UI
│   ├── style.css            # Styling
│   └── script.js            # JavaScript logic
│
├── tests/
│   └── test_api.py          # API tests
│
├── Dockerfile               # Docker configuration
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

## 🛠️ Technologies Used

- **Backend**: FastAPI, Python 3.11+
- **AI Model**: Groq LLaMA 3.1-70B
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Deployment**: Docker, Uvicorn
- **Testing**: Pytest
- **Webhooks**: Discord, Slack, Telegram

## 📊 Features in Detail

### Intelligent Context Understanding

Vicky uses advanced NLP techniques to:
- Understand context from previous questions
- Provide relevant follow-up suggestions
- Handle ambiguous queries intelligently

### Course-Specific Knowledge Base

Optimized for:
- Python programming concepts
- Data analysis with pandas, numpy
- Statistical methods
- Machine learning basics
- Data visualization

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m "Add amazing feature"`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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
