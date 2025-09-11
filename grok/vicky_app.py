import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import urllib
import os
from pathlib import Path
import shutil
from datetime import datetime
import sys
from typing import Dict, Any, List, Optional
import logging
import re
import base64
import tempfile
from collections import defaultdict
import requests
import time
import threading
import ipaddress
import requests
import tempfile
import subprocess
import google.generativeai as genai
from gtts import gTTS
import uuid
import os
import textwrap
import json
import numpy as np

# Utility function for Discord notifications
async def send_discord_notification(ip_address: str, user_agent: str = None):
    """Send visitor notification to Discord webhook"""
    try:
        discord_webhook = os.environ.get("DISCORD_WEBHOOK")
        if not discord_webhook:
            logger.warning("DISCORD_WEBHOOK not found in environment variables")
            return
        
        import requests
        from datetime import datetime
        
        # Get location info (basic info without external API)
        location_info = "Unknown"
        if ip_address and ip_address != "127.0.0.1":
            try:
                # You can enhance this with a geolocation API later
                location_info = f"IP: {ip_address}"
            except:
                location_info = f"IP: {ip_address}"
        
        # Create Discord embed
        embed = {
            "title": "🌐 New Website Visitor",
            "color": 0x4c2882,  # Purple color
            "fields": [
                {
                    "name": "IP Address",
                    "value": ip_address or "Unknown",
                    "inline": True
                },
                {
                    "name": "Time",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "inline": True
                },
                {
                    "name": "User Agent",
                    "value": (user_agent[:100] + "...") if user_agent and len(user_agent) > 100 else (user_agent or "Unknown"),
                    "inline": False
                }
            ],
            "footer": {
                "text": "TDS - Tools for Data Science"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        payload = {
            "embeds": [embed]
        }
        
        # Send to Discord (non-blocking)
        response = requests.post(discord_webhook, json=payload, timeout=5)
        if response.status_code == 204:
            logger.info(f"Discord notification sent for visitor: {ip_address}")
        else:
            logger.warning(f"Discord webhook failed with status: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")

# Pydantic models for API endpoints
class SimilarityRequest(BaseModel):
    docs: List[str]
    query: str

class SimilarityResponse(BaseModel):
    matches: List[str]

# Mock embedding function for similarity search
def get_mock_embedding(text: str) -> List[float]:
    """Generate a mock embedding for text similarity"""
    # Simple hash-based embedding for demonstration
    import hashlib
    hash_obj = hashlib.md5(text.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    
    # Convert to float vector
    embedding = []
    for i in range(10):  # 10-dimensional vector
        embedding.append((hash_int >> (i * 3)) % 1000 / 1000.0)
    
    return embedding

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    import math
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2)
import re
from dotenv import load_dotenv
import json
from pydantic import BaseModel, Field

# Set up CORS for API access from any domain

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tds_app")

# Try to import the question-answering system
try:
    from vicky_server import answer_question
    logger.info("Successfully imported answer_question from vicky_server")
except ImportError as e:
    logger.error(f"Failed to import from vicky_server: {e}")
    sys.exit("Error: Could not import answer_question from vicky_server. Make sure the file exists in the same directory.")

app = FastAPI(title="TDS - Tools for Data Science",
              description="Interactive assistant for data science questions")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
# Create directories for templates and static files if they don't exist
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
UPLOADS_DIR = Path("uploads")

# Create a file to store IP logs
IP_LOGS_FILE = Path("ip_logs.json")

def log_ip_address(request: Request, endpoint: str, query: str = None):
    """Log the IP address and other request details"""
    try:
        # Get IP address considering forwarded headers (for proxies/load balancers)
        ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        
        if forwarded:
            # Get the first IP in the chain (client's real IP)
            ip = forwarded.split(',')[0].strip()
        
        # Validate that this is a real IP address
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            ip = "Invalid IP"
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "ip_address": ip,
            "endpoint": endpoint,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "query": query[:100] if query else None  # Limit query length
        }
        
        # Load existing logs
        logs = []
        if IP_LOGS_FILE.exists():
            try:
                with open(IP_LOGS_FILE, "r") as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        
        # Add new entry and save
        logs.append(log_entry)
        with open(IP_LOGS_FILE, "w") as f:
            json.dump(logs, f, indent=2)
            
        logger.info(f"Logged IP {ip} accessing {endpoint}")
        
    except Exception as e:
        logger.error(f"Error logging IP address: {e}")

# Load environment variables
load_dotenv()

# API access notification settings
API_NOTIF_COUNT = 0
API_NOTIF_LAST_TIME = time.time()
API_NOTIF_LOCK = threading.Lock()
API_NOTIF_BUFFER = []
API_NOTIF_THREAD = None

def send_api_notification(request, question):
    """Send notification about API access via webhook"""
    global API_NOTIF_COUNT, API_NOTIF_LAST_TIME, API_NOTIF_BUFFER, API_NOTIF_THREAD
    
    # Get notification URLs from environment
    discord_webhook = os.environ.get("DISCORD_WEBHOOK")
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    slack_webhook = os.environ.get("SLACK_WEBHOOK")
    
    # Get notification settings
    min_notification_interval = int(os.environ.get("NOTIF_INTERVAL_SECONDS", "300"))  # Default: 5 minutes
    
    # Extract client info
    ip = request.client.host
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(',')[0].strip()
    
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    # Create notification message
    notification = {
        "timestamp": datetime.now().isoformat(),
        "ip": ip,
        "user_agent": user_agent,
        "question": question[:100] + ("..." if len(question) > 100 else "")
    }
    
    with API_NOTIF_LOCK:
        # Add to buffer
        API_NOTIF_BUFFER.append(notification)
        API_NOTIF_COUNT += 1
        
        # Check if we should send immediately
        current_time = time.time()
        time_since_last = current_time - API_NOTIF_LAST_TIME
        
        # Only send if enough time has passed since the last notification
        if time_since_last >= min_notification_interval:
            if API_NOTIF_THREAD is None or not API_NOTIF_THREAD.is_alive():
                API_NOTIF_THREAD = threading.Thread(target=_send_buffered_notifications)
                API_NOTIF_THREAD.daemon = True
                API_NOTIF_THREAD.start()
                API_NOTIF_LAST_TIME = current_time

def _send_buffered_notifications():
    """Send buffered notifications in a separate thread"""
    global API_NOTIF_BUFFER, API_NOTIF_COUNT
    
    with API_NOTIF_LOCK:
        notifications = API_NOTIF_BUFFER.copy()
        count = API_NOTIF_COUNT
        API_NOTIF_BUFFER = []
        API_NOTIF_COUNT = 0
    
    # Get notification URLs from environment
    discord_webhook = os.environ.get("DISCORD_WEBHOOK")
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    slack_webhook = os.environ.get("SLACK_WEBHOOK")
    
    if not notifications:
        return
        
    # Create summary message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = f"**API Access Summary** ({timestamp})\n"
    summary += f"- Total requests: {count}\n"
    
    # Group by IP address
    ip_counts = {}
    for notif in notifications:
        ip = notif["ip"]
        if ip not in ip_counts:
            ip_counts[ip] = 0
        ip_counts[ip] += 1
    
    # Add IP statistics
    summary += "- IP addresses:\n"
    for ip, count in ip_counts.items():
        summary += f"  - {ip}: {count} requests\n"
    
    # Add recent questions
    summary += "- Recent queries:\n"
    for notif in notifications[-5:]:  # Show last 5 questions
        summary += f"  - {notif['question']}\n"
    
    try:
        # Send to Discord
        if discord_webhook:
            payload = {"content": summary}
            requests.post(discord_webhook, json=payload, timeout=5)
            logger.info("Sent API access notification to Discord")
        
        # Send to Telegram
        if telegram_bot_token and telegram_chat_id:
            telegram_api = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": telegram_chat_id,
                "text": summary,
                "parse_mode": "Markdown"
            }
            requests.post(telegram_api, json=payload, timeout=5)
            logger.info("Sent API access notification to Telegram")
        
        # Send to Slack
        if slack_webhook:
            payload = {"text": summary}
            requests.post(slack_webhook, json=payload, timeout=5)
            logger.info("Sent API access notification to Slack")
            
    except Exception as e:
        logger.error(f"Error sending API access notification: {e}")
# Add these imports if not already present
import asyncio
import aiohttp
from datetime import datetime, timedelta

# Add these global variables near the other API notification variables
API_STATUS = "unknown"  # "up", "down", or "unknown"
API_LAST_CHECK = None
API_MONITOR_RUNNING = False
API_CHECK_INTERVAL = int(os.environ.get("API_CHECK_INTERVAL_SECONDS", "300"))  # 5 minutes by default
API_STATUS_LOCK = threading.Lock()

async def monitor_api_status():
    """Background task to monitor API status and report changes"""
    global API_STATUS, API_LAST_CHECK, API_MONITOR_RUNNING
    
    API_MONITOR_RUNNING = True
    logger.info("Starting API status monitoring")
    
    while API_MONITOR_RUNNING:
        try:
            # Check API status
            new_status = await check_api_status()
            last_status = API_STATUS
            
            with API_STATUS_LOCK:
                API_STATUS = new_status
                API_LAST_CHECK = datetime.now()
            
            # Send notification if status changed or periodic update is due
            if new_status != last_status:
                send_status_notification(new_status, is_change=True)
            elif last_status == "up" and (datetime.now().hour % 12 == 0 and datetime.now().minute < 5):
                # Send "all clear" notification once every 12 hours (around midnight and noon)
                send_status_notification(new_status, is_change=False)
                
            # Wait before next check
            await asyncio.sleep(API_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in API monitoring: {e}")
            await asyncio.sleep(60)  # Wait a minute before retry after error
            
    logger.info("API status monitoring stopped")

async def check_api_status():
    """Check if the API is available and responding correctly"""
    try:
        # First check local health endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get("https://app.algsoch.tech/health", timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Health check failed with status {response.status}")
                    return "down"
                
        # Then check the main API endpoint
        async with aiohttp.ClientSession() as session:
            # Just checking if endpoint is accessible, not submitting actual data
            async with session.post("https://app.algsoch.tech/api", 
                                   data={"question": "health_check"}, 
                                   timeout=15) as response:
                if response.status != 200:
                    logger.warning(f"API check failed with status {response.status}")
                    return "down"
                
        return "up"
    except Exception as e:
        logger.error(f"Error checking API status: {e}")
        return "down"

def send_status_notification(status, is_change=True):
    """Send API status notification through webhooks"""
    # Get notification URLs from environment
    discord_webhook = os.environ.get("DISCORD_WEBHOOK")
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    slack_webhook = os.environ.get("SLACK_WEBHOOK")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create appropriate message based on status
    if status == "up":
        if is_change:
            emoji = "🟢"
            title = "API is now UP"
            message = f"{emoji} **API Status Alert** - {timestamp}\nThe API at app.algsoch.tech is now UP and responding correctly."
        else:
            emoji = "✅"
            title = "API Status Report"
            message = f"{emoji} **API Status Report** - {timestamp}\nThe API at app.algsoch.tech is operating normally."
    else:
        emoji = "🔴"
        title = "API is DOWN"
        message = f"{emoji} **ALERT: API Status** - {timestamp}\nThe API at app.algsoch.tech is currently DOWN or experiencing issues."
    
    try:
        # Send to Discord
        if discord_webhook:
            payload = {
                "content": message,
                "embeds": [{
                    "title": title,
                    "color": 0x00ff00 if status == "up" else 0xff0000,
                    "description": f"Status: **{status.upper()}**\nLast checked: {timestamp}"
                }]
            }
            requests.post(discord_webhook, json=payload, timeout=5)
            logger.info(f"Sent API status notification to Discord: {status}")
        
        # Send to Slack
        if slack_webhook:
            status_icon = "✅" if status == "up" else "❌"
            payload = {
                "text": message,
                "attachments": [
                    {
                        "color": "#36a64f" if status == "up" else "#ff0000",
                        "fields": [
                            {
                                "title": "Status",
                                "value": f"{status_icon} {status.upper()}", 
                                "short": True
                            },
                            {
                                "title": "Last Checked",
                                "value": timestamp,
                                "short": True
                            }
                        ]
                    }
                ]
            }
            requests.post(slack_webhook, json=payload, timeout=5)
            logger.info(f"Sent API status notification to Slack: {status}")
            
        # You can add Telegram implementation here
        
    except Exception as e:
        logger.error(f"Error sending API status notification: {e}")

# Add this to your startup code to begin monitoring
# Set up Gemini API
@app.post("/transcribe-video")
async def transcribe_video(
    request: Request,
    video_url: str = Form(None),
    start_time: float = Form(0),
    end_time: float = Form(None),
    translate_to_hindi: bool = Form(False),
    correct_text: bool = Form(False)
):
    """Transcribe a video from a URL using YouTube Transcript API"""
    try:
        if not video_url:
            return {"success": False, "error": "Video URL is required"}
        
        # Extract video ID from the URL
        video_id = None
        
        # Check for youtu.be format
        if 'youtu.be' in video_url:
            video_id_match = re.search(r'youtu\.be/([^?&]+)', video_url)
            if video_id_match:
                video_id = video_id_match.group(1)
        # Check for youtube.com format
        elif 'youtube.com' in video_url:
            parsed_url = urllib.parse.urlparse(video_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
        
        if not video_id:
            return {"success": False, "error": "Could not extract video ID from URL"}
        
        # Get the transcript
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Filter transcript entries by time range
        filtered_transcript = []
        
        # First attempt: Get only entries that start within our range
        for entry in transcript:
            entry_start = entry['start']
            entry_end = entry_start + entry['duration']
            
            # Only include entries that start within our range
            if start_time <= entry_start and (end_time is None or entry_start < end_time):
                filtered_transcript.append(entry)
        
        # If we didn't get any entries with strict filtering, try with overlaps
        if not filtered_transcript and end_time is not None:
            for entry in transcript:
                entry_start = entry['start']
                entry_end = entry_start + entry['duration']
                
                # Include entries that overlap with our range
                if entry_end > start_time and entry_start < end_time:
                    filtered_transcript.append(entry)
        
        if not filtered_transcript:
            return {"success": False, "error": f"No transcript found for the specified time range"}
        
        # Sort by start time
        filtered_transcript.sort(key=lambda x: x['start'])
        
        # Combine the text from all matched entries
        transcript_text = " ".join(entry['text'] for entry in filtered_transcript)
        
        # Initialize result objects
        corrected_transcript = None
        hindi_transcript = None
        audio_english_id = None
        audio_hindi_id = None
        
        # Correct text with Gemini if requested
        if correct_text:
            try:
                # Configure Gemini API
                import google.generativeai as genai
                api_key = os.environ.get("GEMINI_API_KEY")
                genai.configure(api_key=api_key)
                
                # Initialize the model
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Prompt for text correction
                prompt = f"""
                Correct the following text by adding proper punctuation, capitalization, and grammar fixes. 
                Return ONLY the corrected text, no additional commentary:

                {transcript_text}
                """
                
                # Generate corrected text
                response = model.generate_content(prompt)
                corrected_transcript = response.text.strip()
            except Exception as e:
                logger.error(f"Error correcting transcript: {str(e)}")
        
        # Translate to Hindi if requested
        if translate_to_hindi:
            try:
                import google.generativeai as genai
                if not 'genai' in locals():
                    api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyAxVcXI5O6fviXNRF1TZh9YnCS8rSrjoSk")
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Use corrected text if available, otherwise use original
                text_to_translate = corrected_transcript if corrected_transcript else transcript_text
                
                # Generate Hindi translation
                translation_prompt = f"Translate this text to Hindi: {text_to_translate}"
                response = model.generate_content(translation_prompt)
                hindi_transcript = response.text.strip()
            except Exception as e:
                logger.error(f"Error translating to Hindi: {str(e)}")
        
        # Generate audio files for speaking
        try:
            from gtts import gTTS
            import uuid
            
            # Generate English audio
            text_for_audio = corrected_transcript if corrected_transcript else transcript_text
            if text_for_audio:
                audio_english_id = str(uuid.uuid4())
                tts = gTTS(text=text_for_audio, lang='en', slow=False)
                
                # Create audio directory if it doesn't exist
                audio_dir = Path("static/audio")
                audio_dir.mkdir(parents=True, exist_ok=True)
                
                tts.save(f"static/audio/{audio_english_id}.mp3")
            
            # Generate Hindi audio if translation is available
            if hindi_transcript:
                audio_hindi_id = str(uuid.uuid4())
                tts = gTTS(text=hindi_transcript, lang='hi', slow=False)
                tts.save(f"static/audio/{audio_hindi_id}.mp3")
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
        
        return {
            "success": True,
            "video_id": video_id,
            "transcript": transcript_text,
            "corrected_transcript": corrected_transcript,
            "hindi_transcript": hindi_transcript,
            "audio_english_id": audio_english_id,
            "audio_hindi_id": audio_hindi_id,
            "time_range": {
                "start": start_time,
                "end": end_time
            }
        }
    except Exception as e:
        logger.error(f"Error transcribing video: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Serve audio files"""
    audio_path = f"static/audio/{audio_id}.mp3"
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(audio_path, media_type="audio/mpeg")
@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(monitor_api_status())

@app.on_event("shutdown")
async def stop_background_tasks():
    global API_MONITOR_RUNNING
    API_MONITOR_RUNNING = False
def load_file_based_questions():
    """Load questions from vickys.json grouped by file"""
    try:
        json_path = Path("vickys.json")
        if not json_path.exists():
            json_path = Path("main/grok/vickys.json")
        if not json_path.exists():
            json_path = Path("e:/data science tool/main/grok/vickys.json")
            
        if not json_path.exists():
            logger.warning("vickys.json file not found")
            return {}
            
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Group questions by file
        questions_by_file = defaultdict(list)
        for i, item in enumerate(data):
            if "question" not in item:
                continue
                
            file_name = item.get("file", "General Questions")
            # Extract just the filename if it's a path
            if "/" in file_name or "\\" in file_name:
                file_name = file_name.replace("\\", "/").split("/")[-1]
                
            questions_by_file[file_name].append({
                "id": f"file-q-{i}",
                "file": item.get("file", ""),
                "question": item["question"]
            })
        
        logger.info(f"Loaded {len(data)} questions from vickys.json, grouped into {len(questions_by_file)} files")
        return questions_by_file
        
    except Exception as e:
        logger.error(f"Error loading questions from vickys.json: {e}")
        return {}
for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        logger.info(f"Directory {directory} is ready")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        sys.exit(f"Error: Could not create directory {directory}")

# Create the HTML template file - same as your original implementation
# Replace your existing HTML template with this enhanced version
with open(TEMPLATES_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS - Tools for Data Science</title>
    <link rel="icon" type="image/png" href="/static/logo.png">
    <link rel="shortcut icon" type="image/png" href="/static/logo.png">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #4c2882;
            --primary-light: #6b3eb6;
            --secondary-color: #37bb9c;
            --dark-color: #2c2c2c;
            --light-color: #f5f5f5;
            --success-color: #4CAF50;
            --error-color: #f44336;
            --warning-color: #ff9800;
            --text-color: #333;
            --border-radius: 8px;
            --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--light-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }
        
        header::after {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            background: radial-gradient(circle at top right, rgba(255,255,255,0.2), transparent);
            pointer-events: none;
        }
        
        h1 {
            margin: 0;
            font-size: 32px;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        }
        
        .subtitle {
            font-style: italic;
            opacity: 0.9;
            margin-top: 10px;
            font-weight: 300;
        }
        
        .header-buttons {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }
        
        .header-button {
            background-color: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .header-button:hover {
            background-color: rgba(255,255,255,0.3);
        }
        
        .main-section {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .chat-container {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .chat-box {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            background-color: white;
        }
        
        .message {
            padding: 12px 18px;
            border-radius: 18px;
            margin-bottom: 15px;
            max-width: 85%;
            word-wrap: break-word;
            position: relative;
            animation: fadeIn 0.3s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            background-color: #e3f2fd;
            margin-left: auto;
            border-top-right-radius: 4px;
            text-align: right;
        }
        
        .bot-message {
            background-color: #f5f5f5;
            margin-right: auto;
            border-top-left-radius: 4px;
            white-space: pre-wrap;
        }
        
        .bot-message.loading {
            background-color: #f0f0f0;
            color: #666;
        }
        
        .bot-message.loading::after {
            content: '⏳';
            margin-left: 5px;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.5; }
            50% { opacity: 1; }
            100% { opacity: 0.5; }
        }
        
        .input-area {
            padding: 15px;
            background-color: #f9f9f9;
            border-top: 1px solid #eee;
        }
        
        .input-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
                .base64-decoder-section {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .decoder-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: bold;
            position: relative;
        }
        
        .decoder-content {
            padding: 15px;
        }
        
        .decoder-textarea {
            width: 100%;
            min-height: 70px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            font-family: monospace;
            font-size: 13px;
            resize: vertical;
        }
        
        .image-preview {
            margin-top: 15px;
            border: 1px solid #eee;
            border-radius: var(--border-radius);
            padding: 15px;
        }
        
        .preview-container {
            margin: 10px 0;
            text-align: center;
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: var(--border-radius);
        }
        
        #previewImage {
            max-width: 100%;
            max-height: 300px;
            border: 1px solid #ddd;
        }
        
        .image-actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        
        .action-btn {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: var(--transition);
        }
        
        .action-btn:hover {
            background-color: var(--primary-light);
        }
        
        .action-btn.secondary {
            background-color: var(--secondary-color);
        }
        
        .action-btn.secondary:hover {
            background-color: #2ea58a;
        }
        
        .action-btn.clear {
            background-color: #6c757d;
        }
        
        .action-btn.clear:hover {
            background-color: #5a6268;
        }
        
        .encoder-section {
            margin-top: 15px;
            border-top: 1px solid #eee;
            padding-top: 15px;
            display: flex;
            justify-content: center;
        }
        
        .file-upload-btn {
            display: inline-block;
            background-color: var(--secondary-color);
            color: white;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .file-upload-btn:hover {
            background-color: #2ea58a;
        }
        
        .usage-badge {
            position: absolute;
            right: 15px;
            background-color: rgba(0,0,0,0.2);
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: normal;
        }
        
        .question-input {
            flex-grow: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 16px;
            background-color: white;
            transition: var(--transition);
        }
        
        .question-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(76, 40, 130, 0.1);
        }
        
        .file-attach {
            position: relative;
        }
        
        .file-attach input[type="file"] {
            position: absolute;
            width: 0.1px;
            height: 0.1px;
            opacity: 0;
            overflow: hidden;
            z-index: -1;
        }
        
        .file-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: var(--secondary-color);
            color: white;
            border-radius: 50%;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .file-button:hover {
            background-color: #2ea58a;
        }
        
        .send-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            transition: var(--transition);
        }
        
        .send-button:hover {
            background-color: var(--primary-light);
        }
        
        .sidebar {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
        }
        
        .sidebar-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            font-weight: bold;
        }
        
        .question-categories {
            display: flex;
            border-bottom: 1px solid #eee;
        }
        
        .category-tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            transition: var(--transition);
        }
        
        .category-tab.active {
            border-bottom-color: var(--primary-color);
            color: var(--primary-color);
        }
        
        .preloaded-questions {
            flex-grow: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .question-item {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .question-item:hover {
            background-color: #f5f5f5;
        }
        
        .question-item:last-child {
            border-bottom: none;
        }
        
        .file-upload-section {
            margin-top: 20px;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        
        .file-upload-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .file-upload-content {
            padding: 20px;
        }
        
        .file-input-container {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .file-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            background-color: white;
        }
        
        .upload-button {
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: var(--transition);
        }
        
        .upload-button:hover {
            background-color: var(--primary-light);
        }
        
        .uploaded-files h4 {
            margin-top: 0;
            margin-bottom: 10px;
            color: var(--primary-color);
        }
        
        .uploaded-files ul {
            list-style: none;
            padding: 0;
        }
        
        .uploaded-files li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .uploaded-files li:last-child {
            border-bottom: none;
        }
        
        .uploaded-files a {
            color: var(--primary-color);
            text-decoration: none;
            font-size: 14px;
            margin-left: 10px;
        }
        
        .status-bar {
            background-color: var(--primary-color);
            color: white;
            padding: 8px 15px;
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            text-align: center;
            font-size: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            z-index: 1000;
        }
        .api-status-section {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    margin: 0 15px;
} 
.status-indicator#apiStatus {
    padding: 4px 8px;
    border-radius: 4px;
    margin: 0;
}
status-indicator#apiStatus.status-up {
    background-color: rgba(76, 175, 80, 0.2);
}

.status-indicator#apiStatus.status-down {
    background-color: rgba(244, 67, 54, 0.2);
}

.status-indicator#apiStatus.status-unknown {
    background-color: rgba(255, 152, 0, 0.2);
}

.last-checked {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.7);
    margin-top: 2px;
}

@media (max-width: 768px) {
    .api-status-section {
        margin: 5px 0;
        width: 100%;
    }
}

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success-color);
            border-radius: 50%;
        }
        
        code {
            background-color: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }
        
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #eee;
            margin: 10px 0;
        }
        
        .code-block {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            margin: 10px 0;
            position: relative;
        }
        
        .code-block::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 8px;
            background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        .copy-button {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #ddd;
            border-radius: 3px;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            transition: var(--transition);
        }
        
        .copy-button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        @media (max-width: 900px) {
            .main-section {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                height: 300px;
            }
            
            .status-bar {
                flex-direction: column;
                gap: 5px;
                padding: 5px;
            }
        }
        /* Add to your existing CSS in the style section */
.question-type-selector {
    margin-bottom: 15px;
    display: flex;
    gap: 10px;
}
        .html-viewer-section {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            margin-top: 20px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .viewer-header {
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: bold;
            position: relative;
        }
        
        .viewer-content {
            padding: 15px;
        }
        
        .url-input-container {
            display: flex;
            gap: 10px;
        }
        
        .url-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            font-family: inherit;
        }
        
        .html-preview {
            margin-top: 15px;
            border: 1px solid #eee;
            border-radius: var(--border-radius);
            padding: 15px;
        }
        
        #previewFrame {
            width: 100%;
            height: 400px;
            border: 1px solid #ddd;
            background-color: white;
            border-radius: var(--border-radius);
        }
        
        .viewer-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        .source-view {
            width: 100%;
            height: 200px;
            overflow: auto;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            padding: 10px;
            font-family: monospace;
            font-size: 12px;
            margin-top: 10px;
            white-space: pre-wrap;
            display: none;
        }
.file-questions {
    flex-grow: 1;
    overflow-y: auto;
    padding: 10px;
    max-height: calc(100% - 100px); /* Adjust based on header and categories height */
    display: flex;
    flex-direction: column;
}

/* Optional: Add some styling for the notice message when no questions are found */
.file-questions .notice {
    padding: 15px;
    text-align: center;
    color: #666;
    font-style: italic;
}
.question-type-btn {
    padding: 8px 15px;
    background-color: #f0f0f0;
    border: 1px solid #ddd;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: var(--transition);
}

.question-type-btn.active {
    background-color: var(--primary-color);
    color: white;
}

.file-categories {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 10px;
    border-bottom: 1px solid #eee;
}

.file-category {
    padding: 5px 10px;
    background-color: #f0f0f0;
    border-radius: 15px;
    cursor: pointer;
    font-size: 13px;
    transition: var(--transition);
}

.file-category.active {
    background-color: var(--primary-color);
    color: white;
}

.file-question-item {
    padding: 12px 15px;
    border-bottom: 1px solid #eee;
    position: relative;
}

.file-question-item:last-child {
    border-bottom: none;
}

.question-text {
    margin-bottom: 8px;
}

.question-file-path {
    font-size: 12px;
    color: #888;
    font-style: italic;
}

.ask-button {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.file-question-item:hover .ask-button {
    opacity: 1;
}
/* Feedback Button */
.feedback-btn {
    position: fixed;
    bottom: 70px;
    right: 20px;
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 30px;
    padding: 10px 20px;
    cursor: pointer;
    box-shadow: var(--shadow);
    z-index: 999;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: var(--transition);
}

.feedback-btn:hover {
    background-color: var(--primary-light);
    transform: scale(1.05);
}

/* Feedback Dialog and Form Common Styles */
.feedback-dialog,
.feedback-form,
.feedback-success {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background-color: white;
    border-radius: var(--border-radius);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    z-index: 1001;
    display: none;
    max-width: 90%;
}

.feedback-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 1000;
    display: none;
}

/* Initial Dialog */
.feedback-dialog {
    width: 400px;
}

.feedback-dialog-content {
    padding: 25px;
}

.feedback-dialog h3 {
    color: var(--primary-color);
    margin-bottom: 15px;
}

.feedback-dialog p {
    margin-bottom: 20px;
}

.feedback-dialog-buttons {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

/* Feedback Form */
.feedback-form {
    width: 500px;
}

.feedback-form-header {
    padding: 15px 25px;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.close-btn {
    background: transparent;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #888;
}

.close-btn:hover {
    color: var(--error-color);
}

.feedback-form-body {
    padding: 20px 25px;
    max-height: 60vh;
    overflow-y: auto;
}

.feedback-form-footer {
    padding: 15px 25px;
    border-top: 1px solid #eee;
    text-align: right;
}

.form-group {
    margin-bottom: 15px;
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
}

/* Success Message */
.feedback-success {
    width: 400px;
    text-align: center;
}

.feedback-success-content {
    padding: 30px;
}

.feedback-success i {
    font-size: 50px;
    color: var(--success-color);
    margin-bottom: 15px;
}

.feedback-success h3 {
    color: var(--primary-color);
    margin-bottom: 15px;
}

.feedback-success p {
    margin-bottom: 20px;
}
/* Video Transcription Styles */
.video-transcription-section {
    background-color: white;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow);
    margin-top: 20px;
    margin-bottom: 20px;
    overflow: hidden;
}

.transcription-header {
    padding: 15px;
    background-color: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: bold;
    position: relative;
}

.transcription-content {
    padding: 15px;
}

.transcription-tabs, .result-tabs {
    display: flex;
    border-bottom: 1px solid #eee;
    margin-bottom: 15px;
}

.transcription-tab, .result-tab {
    padding: 8px 16px;
    cursor: pointer;
    border-bottom: 3px solid transparent;
    transition: var(--transition);
}

.transcription-tab.active, .result-tab.active {
    border-bottom-color: var(--primary-color);
    color: var(--primary-color);
}

.transcription-tab-content {
    display: none;
    margin-bottom: 15px;
}

.transcription-tab-content.active {
    display: block;
}

.time-inputs {
    display: flex;
    gap: 10px;
}

.time-input {
    flex: 1;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: var(--border-radius);
}

.form-input {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: var(--border-radius);
    margin-bottom: 10px;
}

.checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
    margin: 15px 0;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 5px;
    cursor: pointer;
}

.transcription-results {
    margin-top: 20px;
    border-top: 1px solid #eee;
    padding-top: 15px;
}

.result-container {
    display: none;
    margin-bottom: 15px;
}

.result-container.active {
    display: block;
}

.transcript-text {
    max-height: 300px;
    overflow-y: auto;
    padding: 15px;
    background-color: #f5f5f5;
    border-radius: var(--border-radius);
    white-space: pre-wrap;
    margin-bottom: 15px;
    font-size: 14px;
    line-height: 1.6;
}

.audio-player {
    margin-bottom: 15px;
}

.audio-player audio {
    width: 100%;
}

.transcription-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.loading-indicator {
    text-align: center;
    padding: 20px;
    display: none;
}

.loading-indicator i {
    animation: spin 1s linear infinite;
    font-size: 24px;
    color: var(--primary-color);
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
/* Mobile Styles */
@media (max-width: 576px) {
    .feedback-dialog,
    .feedback-form,
    .feedback-success {
        width: 90%;
    }
    
    .feedback-btn {
        padding: 8px 15px;
        font-size: 14px;
    }
}

/* Gemini Chatbot Styles */
/* Enhanced Gemini Chatbot Styles */
.gemini-chatbot {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
}

.chatbot-trigger {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #4285f4, #34a853);
    color: white;
    border: none;
    cursor: pointer;
    font-size: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

.chatbot-trigger:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.chatbot-window {
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 400px;
    height: 600px;
    background: white;
    border-radius: 15px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    display: none;
    flex-direction: column;
    overflow: hidden;
    z-index: 1001;
}

.chatbot-header {
    background: linear-gradient(135deg, #4285f4, #34a853);
    color: white;
    padding: 15px;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.chatbot-close {
    background: none;
    border: none;
    color: white;
    font-size: 20px;
    cursor: pointer;
}

.gemini-chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    background: #f8f9fa;
}

.gemini-message {
    margin-bottom: 15px;
    padding: 12px 16px;
    border-radius: 18px;
    max-width: 85%;
    word-wrap: break-word;
    animation: fadeInUp 0.3s ease;
    line-height: 1.5;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.gemini-user-message {
    background: linear-gradient(135deg, #007bff, #0056b3);
    color: white;
    margin-left: auto;
    border-bottom-right-radius: 4px;
}

.gemini-ai-message {
    background: white;
    color: #333;
    margin-right: auto;
    border-bottom-left-radius: 4px;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.gemini-ai-message.formatted {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.gemini-ai-message.formatted p {
    margin: 0 0 12px 0;
}

.gemini-ai-message.formatted p:last-child {
    margin-bottom: 0;
}

.gemini-ai-message.formatted strong {
    color: #2c3e50;
    font-weight: 600;
}

.gemini-ai-message.formatted em {
    color: #34495e;
    font-style: italic;
}

.gemini-ai-message.formatted .code-block {
    background: #2d3748;
    color: #e2e8f0;
    padding: 12px;
    border-radius: 8px;
    margin: 10px 0;
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 13px;
    overflow-x: auto;
    position: relative;
}

.gemini-ai-message.formatted .inline-code {
    background: #f1f3f4;
    color: #d73a49;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Monaco', 'Consolas', monospace;
    font-size: 12px;
}

.gemini-ai-message.formatted .list-item {
    margin: 8px 0;
    padding-left: 16px;
}

.gemini-ai-message.formatted .list-item.numbered {
    counter-increment: list-counter;
}

.gemini-ai-message.formatted .list-item.numbered::before {
    content: counter(list-counter) ". ";
    font-weight: bold;
    color: #4285f4;
}

.gemini-ai-message.formatted .list-item.bullet {
    color: #4285f4;
}

.copy-code-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.copy-code-btn:hover {
    background: rgba(255, 255, 255, 0.2);
}

.gemini-input-area {
    padding: 15px;
    border-top: 1px solid #e0e0e0;
    background: white;
}

.gemini-input-form {
    display: flex;
    gap: 10px;
}

.gemini-input {
    flex: 1;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 20px;
    outline: none;
    font-size: 14px;
    transition: border-color 0.2s ease;
}

.gemini-input:focus {
    border-color: #4285f4;
    box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.1);
}

.gemini-send-btn {
    padding: 12px 16px;
    background: linear-gradient(135deg, #4285f4, #34a853);
    color: white;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s ease;
}

.gemini-send-btn:hover {
    transform: scale(1.05);
}

// Replace the existing no-match alert styles in the <style> section with this enhanced version:

/* Enhanced No Match Alert with Animation */
.no-match-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.6);
    z-index: 1000;
    display: none;
    backdrop-filter: blur(5px);
    animation: fadeIn 0.3s ease;
}

.no-match-alert {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: linear-gradient(135deg, #ffffff, #f8f9fa);
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    z-index: 1002;
    max-width: 500px;
    width: 90%;
    text-align: center;
    display: none;
    border: 2px solid #e9ecef;
    animation: slideInScale 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes slideInScale {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.7) translateY(20px);
    }
    100% {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1) translateY(0);
    }
}

.alert-icon {
    font-size: 48px;
    margin-bottom: 20px;
    animation: bounce 2s infinite;
}

@keyframes bounce {
    0%, 20%, 50%, 80%, 100% {
        transform: translateY(0);
    }
    40% {
        transform: translateY(-10px);
    }
    60% {
        transform: translateY(-5px);
    }
}

.alert-title {
    font-size: 24px;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 15px;
}

.alert-message {
    font-size: 16px;
    color: #666;
    margin-bottom: 25px;
    line-height: 1.6;
}

/* Enhanced Countdown Timer */
.countdown-container {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 15px;
    border-radius: 15px;
    margin: 20px 0;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
}

.countdown-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
}

.countdown-text {
    font-size: 14px;
    margin-bottom: 8px;
    opacity: 0.9;
}

.countdown-timer {
    font-size: 32px;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    animation: pulse 1s ease-in-out infinite alternate;
}

@keyframes pulse {
    0% { transform: scale(1); }
    100% { transform: scale(1.05); }
}

.countdown-progress {
    width: 100%;
    height: 6px;
    background: rgba(255,255,255,0.3);
    border-radius: 3px;
    margin-top: 10px;
    overflow: hidden;
}

.countdown-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb);
    border-radius: 3px;
    transition: width 0.1s ease;
    animation: progressGlow 1s ease-in-out infinite alternate;
}

@keyframes progressGlow {
    0% { box-shadow: 0 0 5px rgba(255,255,255,0.5); }
    100% { box-shadow: 0 0 15px rgba(255,255,255,0.8); }
}

.alert-buttons {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 25px;
}

.alert-btn {
    padding: 12px 24px;
    border: none;
    border-radius: 25px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
    min-width: 120px;
}

.alert-btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s ease;
}

.alert-btn:hover::before {
    left: 100%;
}

.alert-btn-primary {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.alert-btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
}

.alert-btn-secondary {
    background: linear-gradient(135deg, #4285f4, #34a853);
    color: white;
    box-shadow: 0 4px 15px rgba(66, 133, 244, 0.4);
}

.alert-btn-secondary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(66, 133, 244, 0.6);
}

.alert-btn-tertiary {
    background: linear-gradient(135deg, #ff9a9e, #fecfef);
    color: #2c3e50;
    box-shadow: 0 4px 15px rgba(255, 154, 158, 0.4);
}

.alert-btn-tertiary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(255, 154, 158, 0.6);
}

@media (max-width: 768px) {
    .no-match-alert {
        padding: 30px 20px;
        margin: 0 10px;
    }
    
    .alert-buttons {
        flex-direction: column;
    }
    
    .alert-btn {
        width: 100%;
        margin: 5px 0;
    }
    
    .countdown-timer {
        font-size: 28px;
    }
}

/* Replace the debug section styles with these: */

/* Tools Section Container */
.tools-section-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;
    margin-bottom: 20px;
}

/* Debug Section Styles */
.debug-section {
    background-color: white;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow);
    overflow: hidden;
}

.debug-header {
    padding: 15px;
    background-color: #e74c3c;
    color: white;
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: bold;
    position: relative;
}

.debug-content {
    padding: 15px;
}

.debug-btn {
    background: linear-gradient(135deg, #e74c3c, #c0392b);
    color: white;
    border: none;
    padding: 12px 20px;
    border-radius: 25px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: var(--transition);
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
    width: 100%;
    justify-content: center;
}

.debug-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(231, 76, 60, 0.4);
}

/* Debug Expandable Area */
.debug-expandable {
    margin-top: 15px;
    border-top: 1px solid #eee;
    padding-top: 15px;
    animation: slideDown 0.3s ease;
}

@keyframes slideDown {
    from {
        opacity: 0;
        max-height: 0;
        padding-top: 0;
    }
    to {
        opacity: 1;
        max-height: 500px;
        padding-top: 15px;
    }
}

.debug-actions {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
    flex-wrap: wrap;
}

.debug-action-btn {
    flex: 1;
    padding: 8px 12px;
    background: #e74c3c;
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    font-size: 13px;
    transition: var(--transition);
    min-width: 90px;
}

.debug-action-btn:hover {
    background: #c0392b;
}

.debug-action-btn.secondary {
    background: #3498db;
}

.debug-action-btn.secondary:hover {
    background: #2980b9;
}

.debug-action-btn.tertiary {
    background: #95a5a6;
}

.debug-action-btn.tertiary:hover {
    background: #7f8c8d;
}

.debug-output {
    background: #f8f9fa;
    border-radius: var(--border-radius);
    padding: 15px;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #dee2e6;
}

.debug-message {
    margin-bottom: 10px;
    padding: 8px 12px;
    border-radius: 8px;
    background: white;
    border-left: 4px solid #e74c3c;
    font-size: 14px;
    line-height: 1.4;
}

.debug-message.success {
    border-left-color: #28a745;
    background: #d4edda;
}

.debug-message.error {
    border-left-color: #dc3545;
    background: #f8d7da;
}

.debug-message.info {
    border-left-color: #17a2b8;
    background: #d1ecf1;
}

.debug-message.question {
    border-left-color: #6f42c1;
    background: #e2d9f3;
}

.debug-message pre {
    background: #2d2d2d;
    color: #f8f8f2;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 12px;
    margin: 5px 0;
}

@media (max-width: 768px) {
    .tools-section-container {
        grid-template-columns: 1fr;
    }
    
    .debug-actions {
        flex-direction: column;
    }
    
    .debug-action-btn {
        min-width: auto;
    }
}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS - Tools for Data Science</h1>
            <div class="subtitle">Full support for Graded Assignments 1 to 5 is now available!</div>
            <div class="header-buttons">
                <button class="header-button" onclick="location.href='/files'">
                    <i class="fas fa-file"></i> Files
                </button>
                <button class="header-button" onclick="location.href='/api/docs'">
                    <i class="fas fa-code"></i> API
                </button>
            </div>
        </header>
        
        <div class="main-section">
            <!-- Chat container (left side) -->
            <div class="chat-container">
                <div class="chat-box" id="chatBox">
                    <!-- Initial welcome message -->
                    <div class="message bot-message">
                        <strong>Welcome to TDS - Tools for Data Science!</strong><br><br>
                        I can help you with various data science tasks and questions, including all assignments for GA1 to GA5. 
                        Try asking a question or select one of the preloaded examples from the sidebar.
                    </div>
                </div>
                <div class="input-area">
                    <form class="input-form" id="questionForm" enctype="multipart/form-data" onsubmit="sendQuestionWithFile(event)">
                        <div class="file-attach">
                            <input type="file" id="fileAttachment" name="file">
                            <label for="fileAttachment" class="file-button">
                                <i class="fas fa-paperclip"></i>
                            </label>
                        </div>
                        <input type="text" class="question-input" id="questionInput" placeholder="Ask me anything about data science..." autocomplete="off">
                        <button type="submit" class="send-button">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </form>
                </div>
            </div>
            
         <!-- Base64 Image Decoder - Always visible -->
            <div class="base64-decoder-section">
                <div class="decoder-header">
                    <i class="fas fa-image"></i> Base64 Image Decoder
                    <div class="usage-badge" id="decoderUsageCount">Used: 0 times</div>
                </div>
                <div class="decoder-content">
                    <div class="form-group">
                        <textarea id="base64Input" class="decoder-textarea" placeholder="Paste base64-encoded image data here (starts with data:image/...)"></textarea>
                    </div>
                    <div class="image-preview" id="imagePreview" style="display:none;">
                        <div class="preview-container">
                            <img id="previewImage" alt="Decoded image">
                        </div>
                        <div class="image-actions">
                            <button id="copyImageBtn" class="action-btn">Copy Data</button>
                            <button id="downloadImageBtn" class="action-btn secondary">Download</button>
                            <button id="clearImageBtn" class="action-btn clear">Clear</button>
                        </div>
                    </div>
                    <div class="encoder-section">
                        <div class="upload-container">
                            <label for="imageFileInput" class="file-upload-btn">
                                <i class="fas fa-upload"></i> Select Image to Encode
                            </label>
                            <input type="file" id="imageFileInput" accept="image/*" style="display:none;">
                        </div>
                    </div>
                </div>
            </div>
           
            <!-- HTML Viewer - Always visible -->
            <div class="html-viewer-section">
                <div class="viewer-header">
                    <i class="fas fa-globe"></i> HTML Viewer
                    <div class="usage-badge" id="viewerUsageCount">Used: 0 times</div>
                </div>
                <div class="viewer-content">
                    <div class="form-group">
                        <div class="url-input-container">
                            <input type="text" id="urlInput" class="url-input" placeholder="Enter website URL (https://example.com)">
                            <button id="fetchUrlBtn" class="action-btn">View</button>
                        </div>
                    </div>
                    <div class="html-preview" id="htmlPreview" style="display:none;">
                        <div class="preview-container">
                            <iframe id="previewFrame" sandbox="allow-scripts allow-same-origin"></iframe>
                        </div>
                        <div class="viewer-actions">
                            <button id="copyHtmlBtn" class="action-btn">Copy HTML</button>
                            <button id="viewSourceBtn" class="action-btn secondary">View Source</button>
                            <button id="clearViewerBtn" class="action-btn clear">Clear</button>
                        </div>
                    </div>
                </div>
            </div>
        <!-- Question type selection -->
        <div class="question-type-selector">
            <button class="question-type-btn active" data-type="ga">Graded Assignment Questions</button>
            <button class="question-type-btn" data-type="file">File-Based Questions</button>
        </div>

        <!-- Sidebar content will change based on selection -->
        <div id="gaSidebar" class="sidebar">
            <div class="sidebar-header">Graded Assignment Questions</div>
            <div class="question-categories">
                <div class="category-tab active" data-category="GA1">GA1</div>
                <div class="category-tab" data-category="GA2">GA2</div>
                <div class="category-tab" data-category="GA3">GA3</div>
                <div class="category-tab" data-category="GA4">GA4</div>
                <div class="category-tab" data-category="GA5">GA5</div>
            </div>
            <div class="preloaded-questions" id="preloadedQuestions">
                <!-- Questions will be loaded here by JavaScript -->
            </div>
        </div>

        <div id="fileSidebar" class="sidebar" style="display: none">
            <div class="sidebar-header">File-Based Questions</div>
            
            <div class="file-categories" id="fileCategories">
                <!-- File categories will be loaded here by JavaScript -->
            </div>
            <div class="file-questions" id="fileQuestions">
                <!-- File-based questions will be loaded here -->
            </div>
        </div>
         <!-- Video Transcription Section -->
<div class="video-transcription-section">
    <div class="transcription-header">
        <i class="fas fa-closed-captioning"></i> Video Transcription
        <div class="usage-badge" id="transcriptionUsageCount">Used: 0 times</div>
    </div>
    <div class="transcription-content">
        <div class="transcription-tabs">
            <div class="transcription-tab active" data-tab="url">URL</div>
            <div class="transcription-tab" data-tab="upload">Upload</div>
        </div>
        
        <div class="transcription-tab-content active" id="urlTab">
            <div class="form-group">
                <input type="text" id="videoUrl" class="form-input" placeholder="Enter YouTube or video URL">
            </div>
        </div>
        
        <div class="transcription-tab-content" id="uploadTab">
            <div class="form-group">
                <input type="file" id="videoFile" accept="video/*" class="form-input">
            </div>
        </div>
        
        <div class="transcription-options">
            <div class="form-group">
                <label>Time Range (optional):</label>
                <div class="time-inputs">
                    <input type="number" id="startTime" placeholder="Start (sec)" min="0" class="time-input">
                    <input type="number" id="endTime" placeholder="End (sec)" min="0" class="time-input">
                </div>
            </div>
            
            <div class="form-group checkboxes">
                <label class="checkbox-label">
                    <input type="checkbox" id="correctText"> 
                    Correct punctuation & grammar
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" id="translateToHindi"> 
                    Translate to Hindi
                </label>
            </div>
            
            <button id="transcribeBtn" class="action-btn">Transcribe Video</button>
        </div>
        
        <div class="transcription-results" style="display:none;">
            <div class="result-tabs">
                <div class="result-tab active" data-result="english">English</div>
                <div class="result-tab" data-result="hindi" style="display:none;">Hindi</div>
            </div>
            
            <div class="result-container active" id="englishResult">
                <div class="transcript-text" id="englishTranscript"></div>
                <div class="audio-player">
                    <audio id="englishAudio" controls></audio>
                </div>
            </div>
            
            <div class="result-container" id="hindiResult">
                <div class="transcript-text" id="hindiTranscript"></div>
                <div class="audio-player">
                    <audio id="hindiAudio" controls></audio>
                </div>
            </div>
            
            <div class="transcription-actions">
                <button id="copyTranscriptBtn" class="action-btn">Copy Text</button>
                <button id="downloadTranscriptBtn" class="action-btn secondary">Download</button>
                <button id="clearTranscriptionBtn" class="action-btn clear">Clear</button>
            </div>
        </div>
    </div>
</div>
<!-- Replace the debug section and file upload section with this: -->

        <!-- Tools Section Container -->
        <div class="tools-section-container">
            <!-- Debug Tools (Left Side) -->
            <div class="debug-section">
                <div class="debug-header">
                    <i class="fas fa-bug"></i> Debug Tools
                    <div class="usage-badge">Developer Tools</div>
                </div>
                <div class="debug-content">
                    <button id="debugFormBtn" class="debug-btn">
                        <i class="fas fa-search"></i> Debug Form Data
                    </button>
                    
                    <!-- Debug Expandable Area -->
                    <div class="debug-expandable" id="debugExpandable" style="display: none;">
                        <div class="debug-actions">
                            <button id="testFormBtn" class="debug-action-btn">
                                <i class="fas fa-play"></i> Test Form
                            </button>
                            <button id="randomQuestionBtn" class="debug-action-btn secondary">
                                <i class="fas fa-random"></i> Random Question
                            </button>
                            <button id="clearDebugBtn" class="debug-action-btn tertiary">
                                <i class="fas fa-trash"></i> Clear
                            </button>
                        </div>
                        
                        <div class="debug-output" id="debugOutput">
                            <div class="debug-message">
                                Click "Test Form" to check form data, "Random Question" to see a sample question, or "Clear" to reset.
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- File Upload Section (Right Side) -->
            <div class="file-upload-section">
                <div class="file-upload-header">
                    <i class="fas fa-cloud-upload-alt"></i> File Repository
                </div>
                <div class="file-upload-content">
                    <form class="file-input-container" action="/upload" method="post" enctype="multipart/form-data">
                        <input type="file" class="file-input" name="file">
                        <button type="submit" class="upload-button">Upload File</button>
                    </form>
                    <div class="uploaded-files">
                        <h4>Uploaded Files</h4>
                        <ul id="uploadedFilesList">
                            {% if files %}
                                {% for file in files %}
                                    <li>
                                        <span>{{ file }}</span>
                                        <div>
                                            <a href="/use-file/{{ file }}">Use</a>
                                            <a href="/delete-file/{{ file }}" class="delete-link">Delete</a>
                                        </div>
                                    </li>
                                {% endfor %}
                            {% else %}
                                <li>No files uploaded yet</li>
                            {% endif %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>

      <div class="status-bar">
        <div class="status-indicator">
            <span class="status-dot"></span>
            <span>System Online</span>
        </div>
        <div class="api-status-section">
            <div class="status-indicator" id="apiStatus">
                <span class="status-dot"></span>
                <span class="status-text">API: CHECKING</span>
            </div>
            <div class="last-checked" id="lastChecked">Last checked: Never</div>
        </div>
        <div>
            <i class="fas fa-server"></i> Full support for GA1-GA5 enabled
        </div>
        <div>
            <i class="fas fa-code"></i> API Ready
        </div>
    </div>

   

<!-- Feedback button (floating in corner) -->
<button id="feedbackBtn" class="feedback-btn">
    <i class="fas fa-comment-dots"></i> Feedback
</button>

<!-- Initial feedback dialog -->
<div id="feedbackDialog" class="feedback-dialog">
    <div class="feedback-dialog-content">
        <h3>Share Your Feedback</h3>
        <p>Would you like to give feedback or suggestions to improve our platform?</p>
        <div class="feedback-dialog-buttons">
            <button id="feedbackYesBtn" class="action-btn">Yes, I'll help</button>
            <button id="feedbackNoBtn" class="action-btn clear">Not now</button>
        </div>
    </div>
</div>

<!-- Feedback form -->
<div id="feedbackForm" class="feedback-form">
    <div class="feedback-form-content">
        <div class="feedback-form-header">
            <h3>Submit Feedback</h3>
            <button id="closeFormBtn" class="close-btn">&times;</button>
        </div>
        <div class="feedback-form-body">
            <div class="form-group">
                <label for="feedbackName">Name (optional)</label>
                <input type="text" id="feedbackName" class="form-input" placeholder="Your name">
            </div>
            <div class="form-group">
                <label for="feedbackEmail">Email (optional)</label>
                <input type="email" id="feedbackEmail" class="form-input" placeholder="Your email">
            </div>
            <div class="form-group">
                <label for="feedbackType">Feedback Type</label>
                <select id="feedbackType" class="form-input">
                    <option value="suggestion">Suggestion</option>
                    <option value="bug">Bug Report</option>
                    <option value="feature">Feature Request</option>
                    <option value="other">Other Feedback</option>
                </select>
            </div>
            <div class="form-group">
                <label for="feedbackText">Your Feedback</label>
                <textarea id="feedbackText" class="form-textarea" rows="5" placeholder="Please share your thoughts, suggestions, or report issues..."></textarea>
            </div>
        </div>
        <div class="feedback-form-footer">
            <button id="submitFeedbackBtn" class="action-btn">Submit Feedback</button>
        </div>
    </div>
</div>

<!-- Feedback success message -->
<div id="feedbackSuccess" class="feedback-success">
    <div class="feedback-success-content">
        <i class="fas fa-check-circle"></i>
        <h3>Thank You!</h3>
        <p>Your feedback has been submitted and will help us improve.</p>
        <button id="closeSuccessBtn" class="action-btn">Close</button>
    </div>
</div>

<!-- Backdrop for modals -->
<div id="feedbackBackdrop" class="feedback-backdrop"></div>
<!-- No Match Alert -->
<!-- Enhanced No Match Alert -->
<div id="noMatchBackdrop" class="no-match-backdrop"></div>
<div id="noMatchAlert" class="no-match-alert">
    <div class="alert-icon">🤔</div>
    <div class="alert-title">No Match Found</div>
    <div class="alert-message">
        We couldn't find a matching question in our database. Would you like to try asking again, 
        or get help from our AI assistant?
    </div>
    
    <!-- Enhanced Countdown Timer -->
    <div class="countdown-container">
        <div class="countdown-text">Auto-submitting to Gemini AI in:</div>
        <div class="countdown-timer" id="countdownTimer">10</div>
        <div class="countdown-progress">
            <div class="countdown-progress-bar" id="countdownProgress"></div>
        </div>
    </div>
    
    <div class="alert-buttons">
        <button class="alert-btn alert-btn-primary" id="tryAgainBtn">
            <i class="fas fa-redo"></i> Try Again
        </button>
        <button class="alert-btn alert-btn-secondary" id="askGeminiBtn">
            <i class="fas fa-robot"></i> Ask Gemini AI
        </button>
        <button class="alert-btn alert-btn-tertiary" id="uploadFileBtn">
            <i class="fas fa-upload"></i> Upload File & Ask
        </button>
    </div>
</div>

<!-- Gemini Chatbot -->
<div class="gemini-chatbot">
    <button class="chatbot-trigger" id="chatbotTrigger">
        <i class="fas fa-robot"></i>
    </button>
    
    <div class="chatbot-window" id="chatbotWindow">
        <div class="chatbot-header">
            <span>🤖 Gemini AI Assistant</span>
            <button class="chatbot-close" id="chatbotClose">&times;</button>
        </div>
        
        <div class="gemini-chat-area" id="geminiChatArea">
            <div class="gemini-message gemini-ai-message">
                Hi! I'm your AI assistant powered by Gemini 2.0 Flash. How can I help you today?
            </div>
        </div>
        
        <div class="gemini-input-area">
            <form class="gemini-input-form" id="geminiForm">
                <input type="text" class="gemini-input" id="geminiInput" placeholder="Ask me anything...">
                <button type="submit" class="gemini-send-btn">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </form>
        </div>
    </div>
<script>

    // Video Transcription Logic
document.addEventListener('DOMContentLoaded', function() {
    const videoUrlInput = document.getElementById('videoUrl');
    const videoFileInput = document.getElementById('videoFile');
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    const correctTextCheckbox = document.getElementById('correctText');
    const translateToHindiCheckbox = document.getElementById('translateToHindi');
    const transcribeBtn = document.getElementById('transcribeBtn');
    
    const transcriptionResults = document.querySelector('.transcription-results');
    const englishTranscript = document.getElementById('englishTranscript');
    const hindiTranscript = document.getElementById('hindiTranscript');
    const englishAudio = document.getElementById('englishAudio');
    const hindiAudio = document.getElementById('hindiAudio');
    
    const copyTranscriptBtn = document.getElementById('copyTranscriptBtn');
    const downloadTranscriptBtn = document.getElementById('downloadTranscriptBtn');
    const clearTranscriptionBtn = document.getElementById('clearTranscriptionBtn');
    
    const hindiResultTab = document.querySelector('.result-tab[data-result="hindi"]');
    const transcriptionUsageCount = document.getElementById('transcriptionUsageCount');
    
    // Initialize usage counter from localStorage
    let usageCount = parseInt(localStorage.getItem('transcriptionUsageCount') || '0');
    updateUsageCount(usageCount);
    
    // Function to update and display usage count
    function updateUsageCount(count) {
        usageCount = count;
        localStorage.setItem('transcriptionUsageCount', count.toString());
        transcriptionUsageCount.textContent = `Used: ${count} times`;
    }
    
    // Tab switching for URL/Upload
    document.querySelectorAll('.transcription-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // Update active tab
            document.querySelectorAll('.transcription-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding tab content
            const tabId = this.getAttribute('data-tab') + 'Tab';
            document.querySelectorAll('.transcription-tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Tab switching for results (English/Hindi)
    document.querySelectorAll('.result-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // Update active tab
            document.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding result
            const resultId = this.getAttribute('data-result') + 'Result';
            document.querySelectorAll('.result-container').forEach(container => {
                container.classList.remove('active');
            });
            document.getElementById(resultId).classList.add('active');
        });
    });
    
    // Transcribe button click
    transcribeBtn.addEventListener('click', function() {
        // Get input values
        const videoUrl = videoUrlInput.value.trim();
        const videoFile = videoFileInput.files[0];
        const startTime = startTimeInput.value ? parseInt(startTimeInput.value) : 0;
        const endTime = endTimeInput.value ? parseInt(endTimeInput.value) : null;
        const correctText = correctTextCheckbox.checked;
        const translateToHindi = translateToHindiCheckbox.checked;
        
        // Validate input
        if (!videoUrl && !videoFile) {
            alert('Please enter a video URL or upload a video file');
            return;
        }
        
        // Create form data
        const formData = new FormData();
        
        if (videoUrl) {
            formData.append('video_url', videoUrl);
        }
        
        if (videoFile) {
            formData.append('file', videoFile);
        }
        
        formData.append('start_time', startTime);
        if (endTime) formData.append('end_time', endTime);
        formData.append('correct_text', correctText);
        formData.append('translate_to_hindi', translateToHindi);
        
        // Show loading indicator
        transcribeBtn.disabled = true;
        transcribeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Transcribing...';
        
        // Hide results while processing
        transcriptionResults.style.display = 'none';
        
        // Send request to server
        fetch('/transcribe-video', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            transcribeBtn.disabled = false;
            transcribeBtn.innerHTML = 'Transcribe Video';
            
            if (data.success) {
                // Update usage count
                updateUsageCount(usageCount + 1);
                
                // Display English transcript
                englishTranscript.textContent = data.corrected_transcript || data.transcript;
                
                // Set English audio if available
                if (data.audio_english_id) {
                    englishAudio.src = `/audio/${data.audio_english_id}`;
                    englishAudio.parentElement.style.display = 'block';
                } else {
                    englishAudio.parentElement.style.display = 'none';
                }
                
                // Display Hindi transcript and tab if available
                if (data.hindi_transcript) {
                    hindiTranscript.textContent = data.hindi_transcript;
                    hindiResultTab.style.display = 'block';
                    
                    // Set Hindi audio if available
                    if (data.audio_hindi_id) {
                        hindiAudio.src = `/audio/${data.audio_hindi_id}`;
                        hindiAudio.parentElement.style.display = 'block';
                    } else {
                        hindiAudio.parentElement.style.display = 'none';
                    }
                } else {
                    hindiResultTab.style.display = 'none';
                }
                
                // Show results
                transcriptionResults.style.display = 'block';
                
                // Reset result tabs to English
                document.querySelector('.result-tab[data-result="english"]').click();
            } else {
                alert('Error: ' + (data.error || 'Failed to transcribe video'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            transcribeBtn.disabled = false;
            transcribeBtn.innerHTML = 'Transcribe Video';
            alert('Error transcribing video. Please try again.');
        });
    });
    
    // Copy transcript button
    copyTranscriptBtn.addEventListener('click', function() {
        // Get active result container
        const activeContainer = document.querySelector('.result-container.active');
        const textElement = activeContainer.querySelector('.transcript-text');
        
        // Copy text to clipboard
        navigator.clipboard.writeText(textElement.textContent).then(() => {
            this.textContent = 'Copied!';
            setTimeout(() => { this.textContent = 'Copy Text'; }, 2000);
        });
    });
    
    // Download transcript button
    downloadTranscriptBtn.addEventListener('click', function() {
        // Get active result container
        const activeContainer = document.querySelector('.result-container.active');
        const textElement = activeContainer.querySelector('.transcript-text');
        const isHindi = activeContainer.id === 'hindiResult';
        
        // Create file
        const filename = `transcript_${isHindi ? 'hindi' : 'english'}_${new Date().toISOString().slice(0,10)}.txt`;
        const blob = new Blob([textElement.textContent], {type: 'text/plain'});
        
        // Create download link and click it
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    });
    
    // Clear button
    clearTranscriptionBtn.addEventListener('click', function() {
        // Clear inputs
        videoUrlInput.value = '';
        videoFileInput.value = '';
        startTimeInput.value = '';
        endTimeInput.value = '';
        correctTextCheckbox.checked = false;
        translateToHindiCheckbox.checked = false;
        
        // Clear results
        englishTranscript.textContent = '';
        hindiTranscript.textContent = '';
        englishAudio.src = '';
        hindiAudio.src = '';
        
        // Hide results section
        transcriptionResults.style.display = 'none';
    });
});

// Preloaded questions data
const preloadedQuestions = [
    // GA1 Questions
    {"id": "ga1-1", "text": "Install and run Visual Studio Code. In your Terminal (or Command Prompt), type code -s and press Enter. Copy and paste the entire output below. What is the output of code -s?", "category": "GA1"},
    {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
    {"id": "ga1-3", "text": "How to use npx and prettier with README.md?", "category": "GA1"},
    {"id": "ga1-4", "text": "Google Sheets formula with SEQUENCE and ARRAY_CONSTRAIN", "category": "GA1"},
    {"id": "ga1-5", "text": "Excel formula with SORTBY and TAKE", "category": "GA1"},
    {"id": "ga1-6", "text": "Find hidden input value on a webpage", "category": "GA1"},
    {"id": "ga1-7", "text": "How many Wednesdays are in a date range?", "category": "GA1"},
    {"id": "ga1-8", "text": "Extract data from CSV in a ZIP file", "category": "GA1"},
    
    // GA2 Questions
    {"id": "ga2-1", "text": "Write Python code to count pixels by brightness in an image", "category": "GA2"},
    {"id": "ga2-2", "text": "How to set up a git hook to enforce commit message format?", "category": "GA2"},
    {"id": "ga2-3", "text": "Join datasets using SQLModel in Python", "category": "GA2"},
    {"id": "ga2-4", "text": "Display a world map using Matplotlib", "category": "GA2"},
    {"id": "ga2-5", "text": "Create a MIDI file with a simple melody", "category": "GA2"},
    {"id": "ga2-6", "text": "Generate a fake dataset with scikit-learn", "category": "GA2"},
    {"id": "ga2-7", "text": "Download and visualize weather data", "category": "GA2"},
    {"id": "ga2-8", "text": "Create a simple interactive dashboard with Plotly", "category": "GA2"},
    {"id": "ga2-9", "text": "Create a FastAPI server for student data", "category": "GA2"},
    {"id": "ga2-10", "text": "Set up a Llama model with ngrok tunnel", "category": "GA2"},

    // GA3 Questions
    {"id": "ga3-1", "text": "Calculate step count statistics from JSON data", "category": "GA3"},
    {"id": "ga3-2", "text": "Track view transitions in web animations", "category": "GA3"},
    {"id": "ga3-3", "text": "Clean Excel sales data for margin calculation", "category": "GA3"},
    {"id": "ga3-4", "text": "Compare commits in two Git branches", "category": "GA3"},
    {"id": "ga3-5", "text": "Parse JSON array with nested objects", "category": "GA3"},

    // GA4 Questions
    {"id": "ga4-1", "text": "Analyze GitHub users by location", "category": "GA4"},
    {"id": "ga4-2", "text": "Retrieve follower counts from GitHub API", "category": "GA4"},
    {"id": "ga4-3", "text": "Compare language preferences across regions", "category": "GA4"},
    {"id": "ga4-4", "text": "Find GitHub users who joined in 2022", "category": "GA4"},

    // GA5 Questions
    {"id": "ga5-1", "text": "Clean Excel sales data for margin calculation", "category": "GA5"},
    {"id": "ga5-2", "text": "Generate a histogram of values from data", "category": "GA5"},
    {"id": "ga5-3", "text": "Analyze log entries for error patterns", "category": "GA5"},
    {"id": "ga5-4", "text": "Prepare dataset for sentiment analysis", "category": "GA5"}
];

document.addEventListener('DOMContentLoaded', function() {
    // Get all necessary elements
    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    const categoryTabs = document.querySelectorAll('.category-tab');
    
    // Question type selector
    const fileBasedQuestions = {{ file_based_questions|tojson }};
    const questionTypeBtns = document.querySelectorAll('.question-type-btn');
    const gaSidebar = document.getElementById('gaSidebar');
    const fileSidebar = document.getElementById('fileSidebar');
    const fileCategories = document.getElementById('fileCategories');
    const fileQuestionsContainer = document.getElementById('fileQuestions');

    // Function to add a message to the chat
    function addMessage(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        if (id) messageElement.id = id;
        
        // Process code blocks if it's a bot message
        if (type === 'bot' || type === 'bot loading') {
            // Simple code block detection for ```code``` blocks
            text = text.replace(/```([^`]+)```/g, function(match, codeContent) {
                return `<div class="code-block">${codeContent}<button class="copy-button">Copy</button></div>`;
            });
            
            // Inline code detection for `code`
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        }
        
        messageElement.innerHTML = text;
        
        // Add copy functionality to code blocks
        if (type === 'bot') {
            setTimeout(() => {
                messageElement.querySelectorAll('.copy-button').forEach(button => {
                    button.addEventListener('click', function() {
                        const codeBlock = this.parentNode;
                        const code = codeBlock.textContent.replace('Copy', '').trim();
                        
                        navigator.clipboard.writeText(code).then(() => {
                            this.textContent = 'Copied!';
                            setTimeout(() => { this.textContent = 'Copy'; }, 2000);
                        });
                    });
                });
            }, 0);
        }
        
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
        return messageElement;
    }

    // Initialize file sidebar
    if (fileBasedQuestions && fileBasedQuestions.length > 0) {
        initializeFileSidebar();
    }

    // Handle question type switching
    questionTypeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active state
            questionTypeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide appropriate sidebar
            const type = this.dataset.type;
            if (type === 'ga') {
                gaSidebar.style.display = 'flex';
                fileSidebar.style.display = 'none';
            } else {
                gaSidebar.style.display = 'none';
                fileSidebar.style.display = 'flex';
            }
        });
    });

    // Initialize file sidebar content
    function initializeFileSidebar() {
        // Create file category buttons
        fileCategories.innerHTML = '';
        let firstFile = null;
        
        fileBasedQuestions.forEach(fileGroup => {
            if (!firstFile) firstFile = fileGroup.file;
            
            const fileBtn = document.createElement('div');
            fileBtn.className = 'file-category';
            if (fileGroup.file === firstFile) {
                fileBtn.classList.add('active');
            }
            fileBtn.textContent = fileGroup.file;
            fileBtn.dataset.file = fileGroup.file;
            
            fileBtn.addEventListener('click', function() {
                // Update active state
                document.querySelectorAll('.file-category').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                // Display questions for the selected file
                displayFileQuestions(this.dataset.file);
            });
            
            fileCategories.appendChild(fileBtn);
        });
        
        // Display questions for the first file
        if (firstFile) {
            displayFileQuestions(firstFile);
        }
    }

    // Display questions for a specific file
    function displayFileQuestions(fileName) {
        fileQuestionsContainer.innerHTML = '';
        
        // Find questions for this file
        const fileGroup = fileBasedQuestions.find(group => group.file === fileName);
        if (!fileGroup || !fileGroup.questions) {
            fileQuestionsContainer.innerHTML = `<div class="notice">No questions found for ${fileName}</div>`;
            return;
        }
        
        // Display each question
        fileGroup.questions.forEach(item => {
            const questionItem = document.createElement('div');
            questionItem.className = 'file-question-item';
            
            const questionText = document.createElement('div');
            questionText.className = 'question-text';
            questionText.textContent = item.question;
            
            const filePath = document.createElement('div');
            filePath.className = 'question-file-path';
            filePath.textContent = item.file || 'No file path';
            
            const askButton = document.createElement('button');
            askButton.className = 'ask-button';
            askButton.textContent = 'Ask';
            
            questionItem.appendChild(questionText);
            questionItem.appendChild(filePath);
            questionItem.appendChild(askButton);
            
            // Full item click handler
            questionItem.addEventListener('click', (e) => {
                // Don't trigger if clicking the button
                if (e.target !== askButton) {
                    questionInput.value = item.question;
                }
            });
            
            // Specific button click handler
            askButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent the item click event
                questionInput.value = item.question;
                // Auto-submit the question on button click
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            fileQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Initialize with GA1 questions
    displayPreloadedQuestions('GA1');
    
    // Handle category switching
    categoryTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Update active tab
            categoryTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Display questions for the selected category
            displayPreloadedQuestions(this.dataset.category);
        });
    });
    
    // Display preloaded questions for a specific category
    function displayPreloadedQuestions(category) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const filteredQuestions = preloadedQuestions.filter(q => q.category === category);
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.addEventListener('click', () => {
                questionInput.value = question.text;
                // Auto-submit the question on click
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
    }
    
    // Handle file upload links
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-link')) {
            if (!confirm('Are you sure you want to delete this file?')) {
                e.preventDefault();
            }
        }
    });
    
    // Function to send questions with file
    window.sendQuestionWithFile = function(event) {
        event.preventDefault();
        const question = document.getElementById('questionInput').value.trim();
        if (!question) return;
        
        // Display user question
        addMessage(question, 'user');
        
        // Clear input
        document.getElementById('questionInput').value = '';
        
        // Display loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('Thinking...', 'bot loading', loadingId);
        
        // Create form data
        const formData = new FormData();
        formData.append('question', question);
        
        // Add file if present
        const fileInput = document.getElementById('fileAttachment');
        if (fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
        }
        
        fetch('/ask_with_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            if (data.success) {
                addMessage(data.answer || "No response received", 'bot');
            } else if (data.no_match) {
                // Show no match alert instead of error message
                showNoMatchAlert(data.question, data.has_file);
            } else {
                addMessage("Error: " + (data.error || "Unknown error occurred"), 'bot');
            }
        })
        .catch(error => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            console.error('Error:', error);
            addMessage("Sorry, there was an error processing your question.", 'bot');
        });
    };
    
    // Check server status and update the status indicator
    fetch('/health')
        .then(response => {
            if (response.ok) {
                document.querySelector('.status-dot').style.backgroundColor = '#4CAF50'; // Green
            } else {
                document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
            }
        })
        .catch(() => {
            document.querySelector('.status-dot').style.backgroundColor = '#f44336'; // Red
        });
        
    // Load uploaded files list
    function loadUploadedFiles() {
        fetch('/files')
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const filesList = doc.querySelector('.files-table tbody');
                if (filesList) {
                    const uploadedFilesList = document.getElementById('uploadedFilesList');
                    uploadedFilesList.innerHTML = '';
                    
                    Array.from(filesList.querySelectorAll('tr')).forEach(row => {
                        const fileId = row.cells[0].textContent;
                        const fileName = row.cells[1].textContent;
                        
                        const li = document.createElement('li');
                        li.innerHTML = `
                            <span>${fileName} (ID: ${fileId})</span>
                            <div>
                                <a href="#" class="use-file" data-id="${fileId}">Use</a>
                                <a href="#" class="delete-file" data-id="${fileId}">Delete</a>
                            </div>
                        `;
                        uploadedFilesList.appendChild(li);
                    });
                    
                    // Add event listeners to use/delete links
                    document.querySelectorAll('.use-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const fileId = this.dataset.id;
                            questionInput.value += ` with ID ${fileId}`;
                            questionInput.focus();
                        });
                    });
                    
                    document.querySelectorAll('.delete-file').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            if (confirm('Are you sure you want to delete this file?')) {
                                const fileId = this.dataset.id;
                                fetch(`/delete-file/${fileId}`, { method: 'DELETE' })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.success) {
                                            loadUploadedFiles();
                                        }
                                    });
                            }
                        });
                    });
                }
            });
    }
    
    // Load uploaded files on page load
    loadUploadedFiles();
});

function debugForm() {
    const formData = new FormData();
    formData.append('question', 'Test question');
    
    fetch('/debug-form', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Debug data:', data);
        alert('Check console for debug info');
    });
}

// Base64 Image Decoder Logic
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const base64Input = document.getElementById('base64Input');
    const previewImage = document.getElementById('previewImage');
    const imagePreview = document.getElementById('imagePreview');
    const copyImageBtn = document.getElementById('copyImageBtn');
    const downloadImageBtn = document.getElementById('downloadImageBtn');
    const clearImageBtn = document.getElementById('clearImageBtn');
    const imageFileInput = document.getElementById('imageFileInput');
    const usageCounter = document.getElementById('decoderUsageCount');
    
    // Initialize usage counter from localStorage
    let usageCount = parseInt(localStorage.getItem('base64DecoderUsageCount') || '0');
    updateUsageCount(usageCount);
    
    // Function to update and display usage count
    function updateUsageCount(count) {
        usageCount = count;
        localStorage.setItem('base64DecoderUsageCount', count.toString());
        usageCounter.textContent = `Used: ${count} times`;
        
        // Log usage for analytics 
        if (count % 10 === 0 && count > 0) {
            // Log every 10th use for analytics
            fetch('/log-base64-usage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ count: count })
            }).catch(err => console.log('Usage tracking error:', err));
        }
    }
    
    // Process base64 input (decoding)
    base64Input.addEventListener('input', function() {
        const base64String = this.value.trim();
        
        if (!base64String) {
            imagePreview.style.display = 'none';
            return;
        }
        
        // Process the input
        let imageData = base64String;
        
        // Try to add data:image prefix if missing
        if (!base64String.startsWith('data:image')) {
            // Detect if we need to add the full prefix or just part of it
            if (base64String.includes('base64,')) {
                imageData = 'data:image/png;' + base64String.substring(base64String.indexOf('base64,'));
            } else {
                imageData = 'data:image/png;base64,' + base64String;
            }
        }
        
        // Update the image source
        try {
            previewImage.src = imageData;
            previewImage.onload = function() {
                // Successfully loaded, show the preview
                imagePreview.style.display = 'block';
                // Increment the usage count
                updateUsageCount(usageCount + 1);
            };
            
            previewImage.onerror = function() {
                // Hide preview if invalid
                imagePreview.style.display = 'none';
            };
        } catch (e) {
            console.error('Error displaying image:', e);
            imagePreview.style.display = 'none';
        }
    });
    
    // Copy image data to clipboard
    copyImageBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(previewImage.src).then(() => {
            this.textContent = 'Copied!';
            setTimeout(() => { this.textContent = 'Copy Data'; }, 2000);
        });
    });
    
    // Download the image
    downloadImageBtn.addEventListener('click', function() {
        const imageData = previewImage.src;
        const extension = imageData.includes('image/jpeg') ? 'jpg' : 
                        imageData.includes('image/png') ? 'png' :
                        imageData.includes('image/gif') ? 'gif' : 'png';
        
        const link = document.createElement('a');
        link.href = imageData;
        link.download = `decoded_image.${extension}`;
        link.click();
    });
    
    // Clear input and preview
    clearImageBtn.addEventListener('click', function() {
        base64Input.value = '';
        imagePreview.style.display = 'none';
        previewImage.src = '';
    });
    
    // Handle image file selection for encoding
    imageFileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            // Get base64 data
            const base64 = e.target.result;
            
            // Update textarea with base64 data
            base64Input.value = base64;
            
            // Update image preview
            previewImage.src = base64;
            imagePreview.style.display = 'block';
            
            // Increment the usage count
            updateUsageCount(usageCount + 1);
        };
        
        reader.readAsDataURL(file);
    });
    
    // Handle direct paste from clipboard (for images)
    base64Input.addEventListener('paste', function(e) {
        // Check if paste has image data
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        
        for (const item of items) {
            if (item.type.indexOf('image') === 0) {
                // Prevent default to stop text pasting
                e.preventDefault();
                
                // Get the image as a blob
                const blob = item.getAsFile();
                const reader = new FileReader();
                
                reader.onload = function(event) {
                    // Get base64 data
                    const base64 = event.target.result;
                    
                    // Update textarea with base64 data
                    base64Input.value = base64;
                    
                    // Update image preview
                    previewImage.src = base64;
                    imagePreview.style.display = 'block';
                    
                    // Increment the usage count
                    updateUsageCount(usageCount + 1);
                };
                
                reader.readAsDataURL(blob);
            }
        }
    });
});

// API Status Monitoring
document.addEventListener('DOMContentLoaded', function() {
    // Initialize API status elements
    const apiStatusIndicator = document.getElementById('apiStatus');
    const lastCheckedElement = document.getElementById('lastChecked');
    
    // Function to update API status in UI
    function updateApiStatusUI(status, lastChecked) {
        // Check if elements exist before trying to use them
        if (!apiStatusIndicator) {
            console.log('API status indicator not found');
            return;
        }
        
        // Remove all status classes
        apiStatusIndicator.classList.remove('status-up', 'status-down', 'status-unknown');
        
        // Add appropriate class and text
        if (status === 'up') {
            apiStatusIndicator.classList.add('status-up');
            const statusDot = apiStatusIndicator.querySelector('.status-dot');
            const statusText = apiStatusIndicator.querySelector('.status-text');
            if (statusDot) statusDot.style.backgroundColor = '#4CAF50';
            if (statusText) statusText.textContent = 'API: ONLINE';
        } else if (status === 'down') {
            apiStatusIndicator.classList.add('status-down');
            const statusDot = apiStatusIndicator.querySelector('.status-dot');
            const statusText = apiStatusIndicator.querySelector('.status-text');
            if (statusDot) statusDot.style.backgroundColor = '#f44336';
            if (statusText) statusText.textContent = 'API: OFFLINE';
        } else {
            apiStatusIndicator.classList.add('status-unknown');
            const statusDot = apiStatusIndicator.querySelector('.status-dot');
            const statusText = apiStatusIndicator.querySelector('.status-text');
            if (statusDot) statusDot.style.backgroundColor = '#ff9800';
            if (statusText) statusText.textContent = 'API: CHECKING';
        }
        
        // Update last checked time if available
        if (lastChecked && lastCheckedElement) {
            const date = new Date(lastChecked);
            lastCheckedElement.textContent = `Last checked: ${date.toLocaleTimeString()}`;
        }
    }
    
    // Function to check API status
    async function checkApiStatus() {
        try {
            const response = await fetch('/api-status');
            if (response.ok) {
                const data = await response.json();
                updateApiStatusUI(data.status, data.last_checked);
            } else {
                updateApiStatusUI('down');
            }
        } catch (error) {
            console.error('Error checking API status:', error);
            updateApiStatusUI('down');
        }
    }
    
    // Check status immediately and then every 60 seconds
    checkApiStatus();
    setInterval(checkApiStatus, 60000);
});

// HTML Viewer Logic
document.addEventListener('DOMContentLoaded', function() {
    const urlInput = document.getElementById('urlInput');
    const fetchUrlBtn = document.getElementById('fetchUrlBtn');
    const htmlPreview = document.getElementById('htmlPreview');
    const previewFrame = document.getElementById('previewFrame');
    const copyHtmlBtn = document.getElementById('copyHtmlBtn');
    const viewSourceBtn = document.getElementById('viewSourceBtn');
    const clearViewerBtn = document.getElementById('clearViewerBtn');
    const viewerUsageCount = document.getElementById('viewerUsageCount');
    
    // Initialize usage counter from localStorage
    let usageCount = parseInt(localStorage.getItem('htmlViewerUsageCount') || '0');
    updateUsageCount(usageCount);
    
    // Function to update and display usage count
    function updateUsageCount(count) {
        usageCount = count;
        localStorage.setItem('htmlViewerUsageCount', count.toString());
        viewerUsageCount.textContent = `Used: ${count} times`;
        
        // Log usage for analytics 
        if (count % 10 === 0 && count > 0) {
            fetch('/log-html-viewer-usage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ count: count })
            }).catch(err => console.log('Usage tracking error:', err));
        }
    }
    
    // Create source view element if needed
    function getSourceView() {
        let sourceView = document.getElementById('sourceView');
        if (!sourceView) {
            sourceView = document.createElement('pre');
            sourceView.id = 'sourceView';
            sourceView.className = 'source-view';
            htmlPreview.appendChild(sourceView);
        }
        return sourceView;
    }
    
    // Fetch website content
    fetchUrlBtn.addEventListener('click', function() {
        let url = urlInput.value.trim();
        if (!url) return;
        
        // Add https:// if not present
        if (!/^https?:\\/\\//i.test(url)) {
            url = 'https://' + url;
            urlInput.value = url;
        }
        
        // Show loading state
        previewFrame.srcdoc = '<div style="padding:20px; text-align:center;"><p>Loading...</p></div>';
        htmlPreview.style.display = 'block';
        
        // Hide source view if visible
        const sourceView = getSourceView();
        sourceView.style.display = 'none';
        
        // Using a CORS proxy to fetch the content
        fetch(`https://api.allorigins.win/get?url=${encodeURIComponent(url)}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.contents) {
                    // Display the HTML in the iframe
                    previewFrame.srcdoc = data.contents;
                    
                    // Store the source for later viewing
                    sourceView.textContent = data.contents;
                    
                    // Increment the usage count
                    updateUsageCount(usageCount + 1);
                } else {
                    previewFrame.srcdoc = '<div style="padding:20px; color:red;">Error: Could not fetch content.</div>';
                }
            })
            .catch(error => {
                previewFrame.srcdoc = `<div style="padding:20px; color:red;">Error: ${error.message}</div>`;
            });
    });
    
    // Copy HTML content
    copyHtmlBtn.addEventListener('click', function() {
        const sourceView = getSourceView();
        const html = sourceView.textContent;
        
        navigator.clipboard.writeText(html).then(() => {
            this.textContent = 'Copied!';
            setTimeout(() => { this.textContent = 'Copy HTML'; }, 2000);
        });
    });
    
    // View source HTML
    viewSourceBtn.addEventListener('click', function() {
        const sourceView = getSourceView();
        if (sourceView.style.display === 'block') {
            sourceView.style.display = 'none';
            this.textContent = 'View Source';
        } else {
            sourceView.style.display = 'block';
            this.textContent = 'Hide Source';
        }
    });
    
    // Clear the viewer
    clearViewerBtn.addEventListener('click', function() {
        urlInput.value = '';
        htmlPreview.style.display = 'none';
        previewFrame.srcdoc = '';
        
        const sourceView = getSourceView();
        sourceView.style.display = 'none';
        sourceView.textContent = '';
        viewSourceBtn.textContent = 'View Source';
    });
    
    // Handle Enter key in URL input
    urlInput.addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            fetchUrlBtn.click();
        }
    });
});

// Feedback System
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const feedbackBtn = document.getElementById('feedbackBtn');
    const feedbackDialog = document.getElementById('feedbackDialog');
    const feedbackYesBtn = document.getElementById('feedbackYesBtn');
    const feedbackNoBtn = document.getElementById('feedbackNoBtn');
    const feedbackForm = document.getElementById('feedbackForm');
    const closeFormBtn = document.getElementById('closeFormBtn');
    const submitFeedbackBtn = document.getElementById('submitFeedbackBtn');
    const feedbackSuccess = document.getElementById('feedbackSuccess');
    const closeSuccessBtn = document.getElementById('closeSuccessBtn');
    const feedbackBackdrop = document.getElementById('feedbackBackdrop');
    
    // Feedback button click - show initial dialog
    feedbackBtn.addEventListener('click', function() {
        feedbackBackdrop.style.display = 'block';
        feedbackDialog.style.display = 'block';
    });
    
    // "Yes" button - open feedback form
    feedbackYesBtn.addEventListener('click', function() {
        feedbackDialog.style.display = 'none';
        feedbackForm.style.display = 'block';
    });
    
    // "No" button - close dialog
    feedbackNoBtn.addEventListener('click', function() {
        feedbackBackdrop.style.display = 'none';
        feedbackDialog.style.display = 'none';
    });
    
    // Close form button
    closeFormBtn.addEventListener('click', function() {
        feedbackBackdrop.style.display = 'none';
        feedbackForm.style.display = 'none';
        resetForm();
    });
    
    // Close success message
    closeSuccessBtn.addEventListener('click', function() {
        feedbackBackdrop.style.display = 'none';
        feedbackSuccess.style.display = 'none';
    });
    
    // Click on backdrop
    feedbackBackdrop.addEventListener('click', function() {
        feedbackBackdrop.style.display = 'none';
        feedbackDialog.style.display = 'none';
        feedbackForm.style.display = 'none';
        feedbackSuccess.style.display = 'none';
        resetForm();
    });
    
    // Submit feedback
    submitFeedbackBtn.addEventListener('click', function() {
        const name = document.getElementById('feedbackName').value;
        const email = document.getElementById('feedbackEmail').value;
        const type = document.getElementById('feedbackType').value;
        const text = document.getElementById('feedbackText').value;
        
        // Validate
        if (!text.trim()) {
            alert('Please enter your feedback');
            return;
        }
        
        // Disable button and show loading state
        submitFeedbackBtn.disabled = true;
        submitFeedbackBtn.textContent = 'Submitting...';
        
        // Submit via fetch API
        fetch('/submit-feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                email: email,
                type: type,
                feedback: text
            })
        })
        .then(response => response.json())
        .then(data => {
            // Show success message
            feedbackForm.style.display = 'none';
            feedbackSuccess.style.display = 'block';
            resetForm();
        })
        .catch(error => {
            alert('Error submitting feedback. Please try again.');
            console.error('Error:', error);
        })
        .finally(() => {
            // Reset button state
            submitFeedbackBtn.disabled = false;
            submitFeedbackBtn.textContent = 'Submit Feedback';
        });
    });
    
    // Reset form function
    function resetForm() {
        document.getElementById('feedbackName').value = '';
        document.getElementById('feedbackEmail').value = '';
        document.getElementById('feedbackType').selectedIndex = 0;
        document.getElementById('feedbackText').value = '';
    }
});


// Replace the problematic JavaScript section with this corrected version:

// No Match Alert and Enhanced Gemini Chatbot Logic
document.addEventListener('DOMContentLoaded', function() {
    const noMatchAlert = document.getElementById('noMatchAlert');
    const noMatchBackdrop = document.getElementById('noMatchBackdrop');
    const tryAgainBtn = document.getElementById('tryAgainBtn');
    const askGeminiBtn = document.getElementById('askGeminiBtn');
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    const countdownTimer = document.getElementById('countdownTimer');
    const countdownProgress = document.getElementById('countdownProgress');
    const chatbotTrigger = document.getElementById('chatbotTrigger');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const geminiForm = document.getElementById('geminiForm');
    const geminiInput = document.getElementById('geminiInput');
    const geminiChatArea = document.getElementById('geminiChatArea');
    
    let currentFailedQuestion = '';
    let currentHasFile = false;
    let countdownInterval = null;
    let autoSubmitTimeout = null;
    
    // Show no match alert with auto-submit option
    function showNoMatchAlert(question, hasFile) {
        currentFailedQuestion = question;
        currentHasFile = hasFile;
        noMatchBackdrop.style.display = 'block';
        noMatchAlert.style.display = 'block';
        startCountdown();

        
    }
    function startCountdown() {
        let timeLeft = 10; // 10 seconds countdown
        countdownTimer.textContent = timeLeft;
        countdownProgress.style.width = '100%';
        
        // Clear any existing intervals
        if (countdownInterval) clearInterval(countdownInterval);
        if (autoSubmitTimeout) clearTimeout(autoSubmitTimeout);
        
        countdownInterval = setInterval(() => {
            timeLeft--;
            countdownTimer.textContent = timeLeft;
            
            // Update progress bar
            const progressPercentage = (timeLeft / 10) * 100;
            countdownProgress.style.width = progressPercentage + '%';
            
            // Add warning animation when time is running out
            if (timeLeft <= 3) {
                countdownTimer.style.color = '#ff6b6b';
                countdownTimer.style.animation = 'pulse 0.5s ease-in-out infinite alternate';
            }
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                // Auto-submit to Gemini
                autoSubmitToGemini();
            }
        }, 1000);
        
        // Set timeout as backup
        autoSubmitTimeout = setTimeout(() => {
            if (noMatchAlert.style.display === 'block') {
                autoSubmitToGemini();
            }
        }, 10000); // 10 seconds
    }
    
    function autoSubmitToGemini() {
        // Clear intervals
        if (countdownInterval) clearInterval(countdownInterval);
        if (autoSubmitTimeout) clearTimeout(autoSubmitTimeout);
        
        // Hide alert and show chatbot
        hideNoMatchAlert();
        showChatbot();
        
        if (currentFailedQuestion) {
            geminiInput.value = currentFailedQuestion;
            // Auto-submit the form with a slight delay for better UX
            setTimeout(() => {
                geminiForm.dispatchEvent(new Event('submit'));
            }, 500);
        }
    }
    
    function stopCountdown() {
        if (countdownInterval) clearInterval(countdownInterval);
        if (autoSubmitTimeout) clearTimeout(autoSubmitTimeout);
    }
    
    
    // Make showNoMatchAlert available globally
    window.showNoMatchAlert = showNoMatchAlert;
    
    // Hide no match alert
    function hideNoMatchAlert() {
        noMatchBackdrop.style.display = 'none';
        noMatchAlert.style.display = 'none';
        // Reset countdown display
        countdownTimer.textContent = '10';
        countdownTimer.style.color = 'white';
        countdownTimer.style.animation = 'pulse 1s ease-in-out infinite alternate';
        countdownProgress.style.width = '100%';
    }
    
    // Try again button
    tryAgainBtn.addEventListener('click', function() {
        hideNoMatchAlert();
        document.getElementById('questionInput').focus();
    });
    
    // Ask Gemini button - immediate submit
    askGeminiBtn.addEventListener('click', function() {
        autoSubmitToGemini();
        showChatbot();
        if (currentFailedQuestion) {
            geminiInput.value = currentFailedQuestion;
            // Immediately submit the form
            geminiForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // Upload file button
    uploadFileBtn.addEventListener('click', function() {
        hideNoMatchAlert();
        document.getElementById('fileAttachment').click();
    });
    
    // Chatbot trigger
    chatbotTrigger.addEventListener('click', function() {
        showChatbot();
    });
    
    // Chatbot close
    chatbotClose.addEventListener('click', function() {
        hideChatbot();
    });
    
    // Show/hide chatbot
    function showChatbot() {
        chatbotWindow.style.display = 'flex';
        chatbotTrigger.style.display = 'none';
        geminiInput.focus();
    }
    
    function hideChatbot() {
        chatbotWindow.style.display = 'none';
        chatbotTrigger.style.display = 'flex';
    }
    
    // Enhanced Gemini form submission with better formatting
    geminiForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = geminiInput.value.trim();
        if (!message) return;
        
        // Add user message
        addGeminiMessage(message, 'user');
        geminiInput.value = '';
        
        // Add loading message with better animation
        const loadingId = 'loading-' + Date.now();
        addGeminiMessage('🤖 Analyzing your question...', 'ai', loadingId);
        
        // Send to Gemini
        fetch('/chat-gemini', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `message=${encodeURIComponent(message)}`
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            if (data.success) {
                // Format and add the response
                addFormattedGeminiMessage(data.response, 'ai');
            } else {
                addGeminiMessage('❌ Sorry, I encountered an error: ' + (data.error || 'Gemini API not available'), 'ai');
            }
        })
        .catch(error => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            addGeminiMessage('❌ Sorry, I encountered a connection error. Please try again.', 'ai');
        });
    });
    
    // Add message to Gemini chat with basic formatting
    function addGeminiMessage(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `gemini-message gemini-${type}-message`;
        if (id) messageElement.id = id;
        messageElement.textContent = text;
        
        geminiChatArea.appendChild(messageElement);
        geminiChatArea.scrollTop = geminiChatArea.scrollHeight;
    }
    
    // Add formatted message to Gemini chat with enhanced styling
    function addFormattedGeminiMessage(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `gemini-message gemini-${type}-message formatted`;
        if (id) messageElement.id = id;
        
        // Enhanced text formatting
        let formattedText = text;
        
        // Convert **bold** to HTML
        formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to HTML
        formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert code blocks ```code``` to HTML
        formattedText = formattedText.replace(/```([\\s\\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>');
        
        // Convert inline code `code` to HTML
        formattedText = formattedText.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
        
        // Convert numbered lists
        formattedText = formattedText.replace(/^\\d+\\.\\s+(.+)$/gm, '<div class="list-item numbered">$1</div>');
        
        // Convert bullet points
        formattedText = formattedText.replace(/^[-•]\\s+(.+)$/gm, '<div class="list-item bullet">• $1</div>');
        
        // Convert line breaks to proper HTML
        formattedText = formattedText.replace(/\\n\\n/g, '</p><p>');
        formattedText = '<p>' + formattedText + '</p>';
        
        // Clean up empty paragraphs
        formattedText = formattedText.replace(/<p><\\/p>/g, '');
        
        messageElement.innerHTML = formattedText;
        
        geminiChatArea.appendChild(messageElement);
        geminiChatArea.scrollTop = geminiChatArea.scrollHeight;
        
        // Add copy functionality to code blocks
        messageElement.querySelectorAll('.code-block').forEach(block => {
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-code-btn';
            copyBtn.textContent = 'Copy';
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(block.textContent).then(() => {
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
                });
            };
            block.style.position = 'relative';
            block.appendChild(copyBtn);
        });
    }
    
    // Close alert when clicking backdrop
    noMatchBackdrop.addEventListener('click', function() {
        hideNoMatchAlert();
    });
    // Prevent alert from closing when clicking inside the alert
    noMatchAlert.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});



// Advanced debug functionality
// Replace the debug functionality JavaScript with this:
document.addEventListener('DOMContentLoaded', function() {
    // Load questions from vickys.json for random selection
    let allQuestions = [];
    
    // Load questions directly from vickys.json and preloaded questions
    try {
        // Add preloaded GA questions
        preloadedQuestions.forEach(question => {
            allQuestions.push({
                text: question.text,
                category: question.category,
                source: 'GA Questions'
            });
        });
        
        // Load questions from vickys.json
        fetch('/static/vickys.json')
            .then(response => response.json())
            .then(data => {
                data.forEach(item => {
                    if (item.question && item.file) {
                        allQuestions.push({
                            text: item.question,
                            file: item.file,
                            source: 'File Questions'
                        });
                    }
                });
                console.log(`Loaded ${allQuestions.length} questions for debug tool`);
            })
            .catch(error => {
                console.log('Could not load vickys.json:', error);
            });
            
    } catch (e) {
        console.log('Could not load questions for debug tool:', e);
    }

    // Debug functionality
    const debugBtn = document.getElementById('debugFormBtn');
    const debugExpandable = document.getElementById('debugExpandable');
    const testFormBtn = document.getElementById('testFormBtn');
    // Add this to your debug section
const testQuestionsBtn = document.createElement('button');
testQuestionsBtn.className = 'debug-action-btn secondary';
testQuestionsBtn.innerHTML = '<i class="fas fa-list"></i> Check Questions';
testQuestionsBtn.addEventListener('click', function() {
    fetch('/api/question-stats')
        .then(response => response.json())
        .then(data => {
            const message = `📊 Question Statistics:\n\n` +
                          `Total Questions: ${data.total_questions}\n` +
                          `GA Questions: ${data.ga_questions}\n` +
                          `File Questions: ${data.file_questions}\n\n` +
                          `Categories:\n` +
                          `GA1: ${data.categories.GA1}\n` +
                          `GA2: ${data.categories.GA2}\n` +
                          `GA3: ${data.categories.GA3}\n` +
                          `GA4: ${data.categories.GA4}\n` +
                          `GA5: ${data.categories.GA5}`;
            addDebugMessage(message, 'info');
        })
        .catch(error => {
            addDebugMessage(`❌ Error checking questions: ${error.message}`, 'error');
        });
});

// Add the button to debug actions (insert after the existing buttons)
document.querySelector('.debug-actions').appendChild(testQuestionsBtn);
    const randomQuestionBtn = document.getElementById('randomQuestionBtn');
    const clearDebugBtn = document.getElementById('clearDebugBtn');
    const debugOutput = document.getElementById('debugOutput');

    let isExpanded = false;

    // Toggle debug expandable area
    debugBtn.addEventListener('click', function() {
        isExpanded = !isExpanded;
        
        if (isExpanded) {
            debugExpandable.style.display = 'block';
            this.innerHTML = '<i class="fas fa-chevron-up"></i> Hide Debug Tools';
        } else {
            debugExpandable.style.display = 'none';
            this.innerHTML = '<i class="fas fa-search"></i> Debug Form Data';
        }
    });

    // Test form functionality
    testFormBtn.addEventListener('click', function() {
        addDebugMessage('🔍 Testing form data...', 'info');
        
        const formData = new FormData();
        formData.append('question', 'Test question from debug tool');
        
        fetch('/debug-form', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            const formattedData = JSON.stringify(data, null, 2);
            const message = `✅ Form test successful!\n\n📋 Debug Results:`;
            addDebugMessage(message, 'success');
            addDebugMessage(`<pre>${formattedData}</pre>`, 'success');
        })
        .catch(error => {
            addDebugMessage(`❌ Form test failed!\n\n🚨 Error: ${error.message}`, 'error');
        });
    });

    // Random question functionality
    randomQuestionBtn.addEventListener('click', function() {
        if (allQuestions.length === 0) {
            addDebugMessage('📝 Loading questions... Please wait and try again in a moment.', 'info');
            return;
        }
        
        // Get random question
        const randomIndex = Math.floor(Math.random() * allQuestions.length);
        const randomQuestion = allQuestions[randomIndex];
        
        // Display the question
        let questionText = `🎲 Random Question from ${randomQuestion.source}:"${randomQuestion.text}"`;
        
        if (randomQuestion.category) {
            questionText += `\\n\\nCategory: ${randomQuestion.category}`;
        }
        
        if (randomQuestion.file) {
            questionText += `\\n\\nFile: ${randomQuestion.file}`;
        }
        
        addDebugMessage(questionText, 'question');
        
        // Auto-fill the main question input
        const questionInput = document.getElementById('questionInput');
        if (questionInput) {
            questionInput.value = randomQuestion.text;
            questionInput.focus();
        }
    });

    // Clear debug output
    clearDebugBtn.addEventListener('click', function() {
        debugOutput.innerHTML = `
            <div class="debug-message">
                Debug output cleared. Available questions: ${allQuestions.length}
            </div>
        `;
    });

    // Add message to debug output
    function addDebugMessage(text, type = 'info') {
        const messageElement = document.createElement('div');
        messageElement.className = `debug-message ${type}`;
        
        // Handle HTML content vs plain text
        if (text.includes('<pre>') || text.includes('<code>')) {
            messageElement.innerHTML = text;
        } else {
            messageElement.textContent = text;
        }
        
        debugOutput.appendChild(messageElement);
        debugOutput.scrollTop = debugOutput.scrollHeight;
    }
});
</script>
    
</div>
</body>
</html>
""")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
# Update the load_file_based_questions function to also return GA questions
def load_questions_from_vickys():
    """Load both GA questions and file-based questions from vickys.json"""
    try:
        json_path = Path("vickys.json")
        if not json_path.exists():
            json_path = Path("main/grok/vickys.json")
        if not json_path.exists():
            json_path = Path("e:/data science tool/main/grok/vickys.json")
            
        if not json_path.exists():
            logger.warning("vickys.json file not found")
            return {}, {}
            
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Separate GA questions and file-based questions
        ga_questions = {}
        file_questions = defaultdict(list)
        
        for i, item in enumerate(data):
            if "question" not in item:
                continue
                
            # Extract GA category from file path
            file_path = item.get("file", "")
            ga_match = re.search(r'GA(\d+)', file_path)
            
            if ga_match:
                # This is a GA question
                ga_number = ga_match.group(1)
                ga_category = f"GA{ga_number}"
                
                if ga_category not in ga_questions:
                    ga_questions[ga_category] = []
                
                ga_questions[ga_category].append({
                    "id": f"ga{ga_number}-{len(ga_questions[ga_category]) + 1}",
                    "text": item["question"],
                    "category": ga_category,
                    "file": item.get("file", "")
                })
            else:
                # This is a file-based question
                file_name = item.get("file", "General Questions")
                if "/" in file_name or "\\" in file_name:
                    file_name = file_name.replace("\\", "/").split("/")[-1]
                    
                file_questions[file_name].append({
                    "id": f"file-q-{i}",
                    "file": item.get("file", ""),
                    "question": item["question"]
                })
        
        logger.info(f"Loaded {sum(len(q) for q in ga_questions.values())} GA questions and {sum(len(q) for q in file_questions.values())} file questions")
        return ga_questions, file_questions
        
    except Exception as e:
        logger.error(f"Error loading questions from vickys.json: {e}")
        return {}, {}
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Track visitor IP and send Discord notification
    try:
        # Get client IP address
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host or "unknown"
        
        # Try to get real IP if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        real_ip = request.headers.get("X-Real-IP")
        
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif real_ip:
            client_ip = real_ip
        
        # Get user agent
        user_agent = request.headers.get("User-Agent") or "unknown"
        
        # Send Discord notification (non-blocking)
        import asyncio
        asyncio.create_task(send_discord_notification(client_ip, user_agent))
        
        logger.info(f"New visitor from IP: {client_ip}")
        
    except Exception as e:
        logger.error(f"Error tracking visitor: {e}")
    
    # Get list of uploaded files
    files = []
    if UPLOADS_DIR.exists():
        files = [f.name for f in UPLOADS_DIR.iterdir() if f.is_file()]
    
    # Load file-based questions
    file_based_questions = load_file_based_questions()
    ga_questions= load_questions_from_vickys()

    # Convert to a format suitable for JavaScript
    file_questions_list = []
    for file_name, questions in file_based_questions.items():
        file_questions_list.append({
            "file": file_name,
            "questions": questions
        })
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "files": files,
            "file_based_questions": file_questions_list,
            "ga_questions": ga_questions
        }
    )

@app.get("/health")
async def health_check():
    """Endpoint to check if the server is running correctly"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Update the ask_question function to handle file types more generically
@app.get("/api-status")
async def api_status():
    """Endpoint to get current API status"""
    return {
        "status": API_STATUS,
        "last_checked": API_LAST_CHECK.isoformat() if API_LAST_CHECK else None,
        "uptime": {
            "is_monitoring": API_MONITOR_RUNNING,
            "check_interval_seconds": API_CHECK_INTERVAL
        }
    }
@app.post("/ask")
async def ask_question(question: str = Form(...)):
    try:
        logger.info(f"Processing question: {question[:50]}...")
        
        # Check if the question references any uploaded files by ID
        file_ids = re.findall(r'\b([0-9a-f]{8})\b', question)
        
        # If we found file IDs, add their paths to the question
        if file_ids:
            for file_id in file_ids:
                if file_id in UPLOADED_FILES_REGISTRY:
                    # Add the actual file path to the question text
                    file_info = UPLOADED_FILES_REGISTRY[file_id]
                    file_ext = file_info["type"].lower()
                    
                    # Add appropriate context based on file type
                    if file_ext == ".zip":
                        question += f" The ZIP file is located at {file_info['path']}"
                    elif file_ext == ".md":
                        question += f" The README.md file is located at {file_info['path']}"
                    else:
                        # Generic handling for other file types
                        question += f" The file {file_info['original_name']} is located at {file_info['path']}"
        
        # Process the question with the augmented information
        answer = answer_question(question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing your question: {str(e)}")

# Create a global registry for uploaded files
UPLOADED_FILES_REGISTRY = {}  # Maps unique IDs to actual file paths

def register_uploaded_file(original_filename, file_path):
    """Register an uploaded file so solution functions can access it"""
    # Generate a unique ID for this file
    import uuid
    file_id = str(uuid.uuid4())[:8]
    
    # Add to registry with metadata
    UPLOADED_FILES_REGISTRY[file_id] = {
        "original_name": original_filename,
        "path": file_path,
        "uploaded_at": datetime.now().isoformat(),
        "type": os.path.splitext(original_filename)[1].lower()
    }
    
    # Return the ID that can be used in queries
    return file_id

# Update the upload file function to display file IDs better

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save uploaded file
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = UPLOADS_DIR / filename
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Register the file and get an ID
        file_id = register_uploaded_file(file.filename, str(file_path))
        
        logger.info(f"File uploaded: {filename} (ID: {file_id})")
        
        # Add a message to the chat interface about the uploaded file
        file_type = os.path.splitext(file.filename)[1].lower()
        usage_example = ""
        if file_type == ".zip":
            usage_example = f"Extract data from ZIP file with ID {file_id}"
        elif file_type == ".md":
            usage_example = f"Run npx prettier on README.md with ID {file_id}"
        
        return {
            "filename": filename,
            "file_id": file_id,
            "message": f"File uploaded successfully (ID: {file_id}). Example usage: '{usage_example}'"
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/use-file/{filename}")
async def use_file(filename: str, request: Request):
    # Redirect back to the chat interface with the filename in a query parameter
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return RedirectResponse(url=f"/?file={filename}")

# Add this function to make file IDs more accessible

@app.get("/files")
async def list_files(request: Request):
    """Show all uploaded files and their IDs"""
    files_info = []
    for file_id, info in UPLOADED_FILES_REGISTRY.items():
        files_info.append({
            "id": file_id,
            "name": info["original_name"],
            "type": info["type"],
            "uploaded_at": info["uploaded_at"]
        })
    
    return templates.TemplateResponse(
        "files.html",
        {"request": request, "files": files_info}
    )

# Create a template for the files page
with open(TEMPLATES_DIR / "files.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Uploaded Files - TDS</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #4c2882;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            margin: 0;
            font-size: 28px;
        }
        .files-table {
            width: 100%;
            background-color: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .files-table th, .files-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .files-table th {
            background-color: #4c2882;
            color: white;
        }
        .files-table tr:last-child td {
            border-bottom: none;
        }
        .files-table tr:hover {
            background-color: #f5f5f5;
        }
        .back-button {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background-color: #4c2882;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Uploaded Files</h1>
        </header>
        
        {% if files %}
        <table class="files-table">
            <thead>
                <tr>
                    <th>File ID</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Uploaded At</th>
                    <th>Usage Example</th>
                </tr>
            </thead>
            <tbody>
                {% for file in files %}
                <tr>
                    <td>{{ file.id }}</td>
                    <td>{{ file.name }}</td>
                    <td>{{ file.type }}</td>
                    <td>{{ file.uploaded_at }}</td>
                    <td>
                        {% if file.type == '.md' %}
                            Run npx prettier on README.md with ID {{ file.id }}
                        {% elif file.type == '.zip' %}
                            Extract data from ZIP file with ID {{ file.id }}
                        {% else %}
                            Process file with ID {{ file.id }}
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No files have been uploaded yet.</p>
        {% endif %}
        
        <a href="/" class="back-button">Back to Chat</a>
    </div>
</body>
</html>
""")

@app.post("/ask_with_file")
async def ask_with_file(question: str = Form(...), file: UploadFile = File(None)):
    try:
        logger.info(f"Processing question with file: {question[:50]}...")
        
        # If a file was provided, save and process it
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            logger.info(f"File uploaded with question: {filename} (ID: {file_id})")
            
            # Add file context directly to the question
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            elif file_ext == ".md":
                question += f" The README.md file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        answer = answer_question(question)
         # Check if no match was found
        if answer == "NO_MATCH_FOUND":
            return {
                "success": False,
                "no_match": True,
                "question": question,
                "has_file": bool(file and file.filename),
                "message": "We couldn't find a matching question in our database."
            }
        return {"success": True, "answer": answer}
    except Exception as e:
        logger.error(f"Error processing question with file: {e}")
        return {
            "success": False, 
            "error": str(e),
            "error_type": e.__class__.__name__
        }
# Add this new endpoint for Gemini chat
# @app.post("/chat-gemini")
# async def chat_gemini(request: Request, message: str = Form(...)):
#     """Chat with Gemini AI"""
#     try:
#         import google.generativeai as genai
        
#         # Get API key from environment
#         api_key = os.environ.get("GEMINI_API_KEY")
#         if not api_key:
#             return {"success": False, "error": "Gemini API key not configured"}
        
#         # Configure Gemini
#         genai.configure(api_key=api_key)
#         model = genai.GenerativeModel('gemini-2.0-flash')
#         # model.set_temperature(0.7)
#         # Generate response
#         response = model.generate_content(message)
        
#         return {
#             "success": True,
#             "response": response.text,
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         logger.error(f"Error with Gemini chat: {e}")
#         return {"success": False, "error": str(e)}
# Add these imports at the top
import google.generativeai as genai
import os
from typing import Optional

# Configure Gemini API (add this after your other configurations)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
else:
    gemini_model = None
# Add this after your imports and before the preloadedQuestions usage

# Define preloaded questions in Python (same as in JavaScript)
preloadedQuestions = [
    # GA1 Questions
    {"id": "ga1-1", "text": "Install and run Visual Studio Code. In your Terminal (or Command Prompt), type code -s and press Enter. Copy and paste the entire output below. What is the output of code -s?", "category": "GA1"},
    {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
    {"id": "ga1-3", "text": "How to use npx and prettier with README.md?", "category": "GA1"},
    {"id": "ga1-4", "text": "Google Sheets formula with SEQUENCE and ARRAY_CONSTRAIN", "category": "GA1"},
    {"id": "ga1-5", "text": "Excel formula with SORTBY and TAKE", "category": "GA1"},
    {"id": "ga1-6", "text": "Find hidden input value on a webpage", "category": "GA1"},
    {"id": "ga1-7", "text": "How many Wednesdays are in a date range?", "category": "GA1"},
    {"id": "ga1-8", "text": "Extract data from CSV in a ZIP file", "category": "GA1"},
    
    # GA2 Questions
    {"id": "ga2-1", "text": "Write Python code to count pixels by brightness in an image", "category": "GA2"},
    {"id": "ga2-2", "text": "How to set up a git hook to enforce commit message format?", "category": "GA2"},
    {"id": "ga2-3", "text": "Join datasets using SQLModel in Python", "category": "GA2"},
    {"id": "ga2-4", "text": "Display a world map using Matplotlib", "category": "GA2"},
    {"id": "ga2-5", "text": "Create a MIDI file with a simple melody", "category": "GA2"},
    {"id": "ga2-6", "text": "Generate a fake dataset with scikit-learn", "category": "GA2"},
    {"id": "ga2-7", "text": "Download and visualize weather data", "category": "GA2"},
    {"id": "ga2-8", "text": "Create a simple interactive dashboard with Plotly", "category": "GA2"},
    {"id": "ga2-9", "text": "Create a FastAPI server for student data", "category": "GA2"},
    {"id": "ga2-10", "text": "Set up a Llama model with ngrok tunnel", "category": "GA2"},

    # GA3 Questions
    {"id": "ga3-1", "text": "Calculate step count statistics from JSON data", "category": "GA3"},
    {"id": "ga3-2", "text": "Track view transitions in web animations", "category": "GA3"},
    {"id": "ga3-3", "text": "Clean Excel sales data for margin calculation", "category": "GA3"},
    {"id": "ga3-4", "text": "Compare commits in two Git branches", "category": "GA3"},
    {"id": "ga3-5", "text": "Parse JSON array with nested objects", "category": "GA3"},

    # GA4 Questions
    {"id": "ga4-1", "text": "Analyze GitHub users by location", "category": "GA4"},
    {"id": "ga4-2", "text": "Retrieve follower counts from GitHub API", "category": "GA4"},
    {"id": "ga4-3", "text": "Compare language preferences across regions", "category": "GA4"},
    {"id": "ga4-4", "text": "Find GitHub users who joined in 2022", "category": "GA4"},

    # GA5 Questions
    {"id": "ga5-1", "text": "Clean Excel sales data for margin calculation", "category": "GA5"},
    {"id": "ga5-2", "text": "Generate a histogram of values from data", "category": "GA5"},
    {"id": "ga5-3", "text": "Analyze log entries for error patterns", "category": "GA5"},
    {"id": "ga5-4", "text": "Prepare dataset for sentiment analysis", "category": "GA5"}
]
# Add this endpoint for Gemini chat
# Replace your existing Gemini configuration section with this enhanced version

import google.generativeai as genai
import os
from typing import Optional

# Configure Gemini API - Add this after your other configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDcXoOAk8fUUXD21f55S99s21WysAYa4Sw")
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None
    logger.warning("Gemini API key not configured")

# Enhanced Gemini chat endpoint
@app.post("/chat-gemini")
async def chat_gemini(message: str = Form(...)):
    """Chat with Gemini AI about IIT Madras data science topics"""
    if not gemini_model:
        return {"success": False, "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."}
    
    try:
        # Create a context-aware prompt for IIT Madras data science
        context_prompt = f"""
        You are a helpful AI assistant specialized in data science tools and techniques, 
        particularly for IIT Madras coursework and graded assignments. You can help with:
        
        **Programming & Tools:**
        - Python programming for data science (pandas, numpy, matplotlib, seaborn, plotly)
        - Statistical analysis and machine learning (scikit-learn, scipy)
        - Web development (FastAPI, Flask, HTML/CSS)
        - Version control with Git and GitHub
        - Database operations with SQL
        - Command line tools and terminal usage
        
        **IIT Madras Specific:**
        - Graded Assignment questions (GA1 through GA5)
        - Data visualization and analysis projects
        - Web scraping and API usage
        - File processing (ZIP, CSV, JSON, README.md)
        - Interactive dashboards and data presentation
        
        **Instructions for Response:**
        - Provide clear, step-by-step explanations
        - Include practical code examples when relevant
        - Use proper formatting with headers and bullet points
        - Keep explanations concise but comprehensive
        - Focus on practical applications for students
        
        **Current Request:** {message}

        Please provide a helpful well formatted, practical response focused on data science applications. 
        Include code examples when relevant, and explain concepts clearly for students.
        If this relates to a specific assignment, provide step-by-step guidance.
        """
        
        response = gemini_model.generate_content(context_prompt)
        
        return {
            "success": True, 
            "response": response.text,
            "model": "Gemini 1.5 Flash",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return {
            "success": False, 
            "error": f"Gemini API error: {str(e)}"
        }

# Enhanced API endpoint to get question statistics
@app.get("/api/question-stats")
async def get_question_stats():
    """Get comprehensive statistics about available questions"""
    try:
        # Load from vickys.json
        vickys_path = STATIC_DIR / "vickys.json"
        file_questions = 0
        if vickys_path.exists():
            with open(vickys_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                file_questions = len(data)
        
        # Count GA questions from our preloaded list
        ga_questions_count = len(preloadedQuestions)
        
        # Count by category
        category_counts = {}
        for question in preloadedQuestions:
            category = question.get("category", "Unknown")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "total_questions": ga_questions_count + file_questions,
            "ga_questions": ga_questions_count,
            "file_questions": file_questions,
            "categories": category_counts,
            "gemini_api_status": "configured" if gemini_model else "not_configured",
            "data_sources": {
                "preloaded_ga_questions": ga_questions_count,
                "vickys_json_questions": file_questions
            }
        }
    except Exception as e:
        logger.error(f"Error getting question stats: {e}")
        return {"error": str(e)}

# Enhanced random question endpoint
@app.get("/api/random-question")
async def get_random_question():
    """Get a random question from both preloaded and vickys.json"""
    try:
        ga_questions, file_questions = load_questions_from_vickys()
        
        all_questions = []
        
        # Add preloaded GA questions
        for question in preloadedQuestions:
            all_questions.append({
                "text": question["text"],
                "category": question["category"],
                "source": "Preloaded GA Questions",
                "id": question["id"]
            })
        
        # Add GA questions from vickys.json
        for category, questions in ga_questions.items():
            for question in questions:
                all_questions.append({
                    "text": question["text"],
                    "category": question["category"],
                    "source": "Vickys.json GA Questions",
                    "file": question.get("file", "")
                })
        
        # Add file-based questions
        for file_name, questions in file_questions.items():
            for question in questions:
                all_questions.append({
                    "text": question["question"],
                    "file": question.get("file", ""),
                    "source": "File Questions"
                })
        
        if not all_questions:
            return {"error": "No questions available", "total_sources_checked": 3}
        
        # Select random question
        import random
        random_question = random.choice(all_questions)
        
        return {
            "success": True,
            "question": random_question,
            "total_available": len(all_questions),
            "sources": {
                "preloaded": len([q for q in all_questions if q["source"] == "Preloaded GA Questions"]),
                "vickys_ga": len([q for q in all_questions if q["source"] == "Vickys.json GA Questions"]),
                "file_based": len([q for q in all_questions if q["source"] == "File Questions"])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting random question: {e}")
        return {"error": str(e)}
@app.get("/api/docs", response_class=HTMLResponse)
async def api_docs(request: Request):
    return templates.TemplateResponse(
        "api_docs.html",
        {"request": request}
    )

# Create a template for the API documentation page
with open(TEMPLATES_DIR / "api_docs.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDS API Documentation</title>
    <!-- CSS styles here -->
</head>
<body>
    <div class="container">
        <header>
            <h1>TDS API Documentation</h1>
        </header>
        
        <section>
            <h2>Asking Questions</h2>
            
            <h3>POST /api/ask_with_file</h3>
            <p>Ask a question with an optional file attachment</p>
            
            <h4>Parameters</h4>
            <ul>
                <li><strong>question</strong> (required) - The question text</li>
                <li><strong>file</strong> (optional) - A file to use with the question</li>
            </ul>
            
            <h4>Example</h4>
            <pre>
curl -X POST "http://yourdomain.com/api/ask_with_file" \
  -F "question=Extract data from this ZIP file" \
  -F "file=@/path/to/file.zip"
            </pre>
            
            <h4>Response</h4>
            <pre>
{
  "success": true,
  "answer": "The answer from extract.csv is 42",
  "question": "Extract data from this ZIP file"
}
            </pre>
        </section>
        <section>
    <h2>Assignment Submission API</h2>
    
    <h3>POST /api/</h3>
    <p>Main API endpoint for assignment submissions that returns a minimal JSON response format</p>
    
    <h4>Parameters</h4>
    <ul>
        <li><strong>question</strong> (required) - The question text</li>
        <li><strong>file</strong> (optional) - A file to use with the question</li>
    </ul>
    
    <h4>Example</h4>
    <pre>
curl -X POST "https://your-app.vercel.app/api/" \
  -H "Content-Type: multipart/form-data" \
  -F "question=Download and unzip file abcd.zip which has a single extract.csv file inside. What is the value in the \"answer\" column of the CSV file?" \
  -F "file=@abcd.zip"
    </pre>
    
    <h4>Response</h4>
    <pre>
{
  "answer": "1234567890"
}
    </pre>
    
    <p>The response contains a single "answer" field with the exact text that can be submitted for the assignment.</p>
</section>
        
        <section>
    <h2>File Processing API</h2>
    
    <h3>POST /api/process</h3>
    <p>Process a question that requires a file (like README.md for Question 3 or ZIP for Question 8)</p>
    
    <h4>Parameters</h4>
    <ul>
        <li><strong>question</strong> (required) - The question text</li>
        <li><strong>file</strong> (required) - The file to process</li>
        <li><strong>question_type</strong> (optional) - Hint about question type:
            <ul>
                <li><code>npx_readme</code> - For GA1 third question (README.md with npx)</li>
                <li><code>extract_zip</code> - For GA1 eighth question (Extract from ZIP)</li>
            </ul>
        </li>
    </ul>
    
    <h4>cURL Example</h4>
    <pre>
# For README.md (Question 3)
curl -X POST "http://localhost:8000/api/process" \
  -F "question=What is the output of npx prettier on this README file?" \
  -F "file=@/path/to/README.md" \
  -F "question_type=npx_readme"

# For ZIP file (Question 8)
curl -X POST "http://localhost:8000/api/process" \
  -F "question=What is the value in the answer column?" \
  -F "file=@/path/to/q-extract-csv-zip.zip" \
  -F "question_type=extract_zip"
    </pre>
</section>
    </div>
</body>
</html>
""")
# Create a template for the Vicky API documentation page
with open(TEMPLATES_DIR / "vicky_api_docs.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vicky API - Comprehensive Documentation</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #4c2882;
            --primary-light: #6b3eb6;
            --secondary-color: #37bb9c;
            --dark-color: #2c2c2c;
            --light-color: #f8f9fa;
            --gray-color: #e9ecef;
            --text-color: #343a40;
            --code-bg: #2d2d2d;
            --code-color: #f8f8f2;
            --border-radius: 8px;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
            --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--light-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
            color: white;
            padding: 40px 0;
            margin-bottom: 40px;
            position: relative;
            overflow: hidden;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
        }
        
        header::after {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            background: radial-gradient(circle at bottom right, rgba(255,255,255,0.2), transparent);
            pointer-events: none;
        }
        
        .header-content {
            padding: 0 40px;
            position: relative;
            z-index: 2;
        }
        
        h1 {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        h2 {
            font-size: 28px;
            font-weight: 600;
            margin: 40px 0 20px;
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 10px;
        }
        
        h3 {
            font-size: 22px;
            font-weight: 600;
            margin: 30px 0 15px;
            color: var(--secondary-color);
        }
        
        p {
            margin-bottom: 15px;
        }
        
        .subtitle {
            font-size: 18px;
            opacity: 0.9;
            max-width: 700px;
        }
        
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin: 30px 0 20px;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 10px;
        }
        
        .nav-tab {
            padding: 8px 16px;
            cursor: pointer;
            border-radius: var(--border-radius);
            font-weight: 500;
            transition: var(--transition);
            background-color: transparent;
        }
        
        .nav-tab.active {
            background-color: var(--primary-color);
            color: white;
        }
        
        .nav-tab:hover:not(.active) {
            background-color: var(--gray-color);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .endpoint {
            background-color: white;
            border-radius: var(--border-radius);
            margin-bottom: 30px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        
        .endpoint-header {
            display: flex;
            align-items: center;
            padding: 15px 20px;
            background-color: var(--primary-color);
            color: white;
        }
        
        .method {
            font-weight: 600;
            padding: 5px 10px;
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.2);
            margin-right: 15px;
            font-family: var(--font-mono);
        }
        
        .path {
            font-family: var(--font-mono);
            font-size: 18px;
        }
        
        .endpoint-body {
            padding: 20px;
        }
        
        .parameters {
            margin-top: 20px;
        }
        
        .parameter {
            border-bottom: 1px solid var(--gray-color);
            padding: 12px 0;
            display: grid;
            grid-template-columns: 1fr 1fr 2fr;
            gap: 15px;
        }
        
        .parameter:last-child {
            border-bottom: none;
        }
        
        .param-name {
            font-family: var(--font-mono);
            font-weight: 600;
        }
        
        .param-type {
            color: var(--primary-color);
        }
        
        .required {
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 10px;
            background-color: #e74c3c;
            color: white;
            margin-left: 8px;
            font-weight: bold;
        }
        
        .optional {
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 10px;
            background-color: #3498db;
            color: white;
            margin-left: 8px;
            font-weight: bold;
        }
        
        .param-desc {
            grid-column: span 3;
            padding-top: 5px;
            color: #555;
        }
        
        .code-section {
            margin: 20px 0;
        }
        
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background-color: #343a40;
            color: white;
            border-top-left-radius: var(--border-radius);
            border-top-right-radius: var(--border-radius);
            font-family: var(--font-mono);
            font-size: 14px;
        }
        
        .copy-btn {
            background-color: transparent;
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            border-radius: 3px;
            transition: var(--transition);
        }
        
        .copy-btn:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        pre {
            background-color: var(--code-bg);
            color: var(--code-color);
            padding: 15px;
            border-bottom-left-radius: var(--border-radius);
            border-bottom-right-radius: var(--border-radius);
            overflow-x: auto;
            font-family: var(--font-mono);
            font-size: 14px;
            line-height: 1.5;
        }
        
        pre.language-json .key {
            color: #f92672;
        }
        
        pre.language-json .string {
            color: #a6e22e;
        }
        
        pre.language-json .number {
            color: #ae81ff;
        }
        
        pre.language-json .boolean {
            color: #66d9ef;
        }
        
        pre.language-json .null {
            color: #fd971f;
        }
        
        .example {
            margin-top: 30px;
        }
        
        .sub-section {
            margin: 30px 0;
        }
        
        .response-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: var(--shadow);
            border-radius: var(--border-radius);
            overflow: hidden;
        }
        
        .response-table th, .response-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--gray-color);
        }
        
        .response-table th {
            background-color: var(--primary-color);
            color: white;
            font-weight: 500;
        }
        
        .response-table tr:last-child td {
            border-bottom: none;
        }
        
        .response-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .try-it {
            margin-top: 30px;
            background-color: white;
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: var(--shadow);
        }
        
        .try-it-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .toggle-btn {
            background-color: var(--secondary-color);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: var(--transition);
        }
        
        .toggle-btn:hover {
            background-color: #2ea58a;
        }
        
        .try-it-form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .form-label {
            font-weight: 500;
        }
        
        .form-input, .form-textarea {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
        }
        
        .form-textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .submit-btn {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: var(--transition);
            margin-top: 10px;
            font-weight: 500;
        }
        
        .submit-btn:hover {
            background-color: var(--primary-light);
        }
        
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: var(--gray-color);
            border-radius: var(--border-radius);
            display: none;
        }
        
        .result pre {
            max-height: 300px;
            overflow-y: auto;
            margin: 0;
            border-radius: 4px;
        }
        
        footer {
            margin-top: 60px;
            padding: 30px 0;
            background-color: var(--primary-color);
            color: white;
            text-align: center;
            border-radius: var(--border-radius);
        }
        
        footer a {
            color: var(--secondary-color);
            text-decoration: none;
        }
        
        footer a:hover {
            text-decoration: underline;
        }
        
        .curl-example {
            background-color: var(--code-bg);
            padding: 15px;
            border-radius: var(--border-radius);
            overflow-x: auto;
            margin: 20px 0;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 5px;
            color: white;
        }
        
        .badge-get {
            background-color: #61affe;
        }
        
        .badge-post {
            background-color: #49cc90;
        }
        
        @media (max-width: 768px) {
            .parameter {
                grid-template-columns: 1fr;
                gap: 8px;
            }
            
            .param-desc {
                grid-column: 1;
            }
            
            .container {
                padding: 15px;
            }
            
            h1 {
                font-size: 28px;
            }
            
            h2 {
                font-size: 24px;
            }
            
            .nav-tabs {
                flex-wrap: wrap;
            }
            
            .endpoint-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .method {
                margin-bottom: 5px;
                margin-right: 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>Vicky API Documentation</h1>
                <p class="subtitle">A comprehensive API for data science tools, graded assignments, and file processing</p>
            </div>
        </header>
        
        <div class="nav-tabs">
            <div class="nav-tab active" data-tab="overview">Overview</div>
            <div class="nav-tab" data-tab="endpoints">Endpoints</div>
            <div class="nav-tab" data-tab="examples">Examples</div>
            <div class="nav-tab" data-tab="try-it">Try It</div>
        </div>
        
        <div class="tab-content active" id="overview">
            <h2>Introduction</h2>
            <p>
                The Vicky API provides access to powerful data science tools and automated solutions for various tasks.
                It allows you to send questions, process files, and get detailed answers to help with data science assignments.
            </p>
            
            <h3>Base URL</h3>
            <p>All API requests should be made to:</p>
            <pre>https://app.algsoch.tech/api</pre>
            
            <h3>Authentication</h3>
            <p>
                Currently, the API is available for public use without authentication. However, IP addresses are logged for security purposes,
                and rate limiting may be applied to prevent abuse.
            </p>
            
            <h3>Response Formats</h3>
            <p>
                The API can return responses in multiple formats:
            </p>
            <ul>
                <li><strong>JSON</strong> (default): Structured data that's easy to parse programmatically</li>
                <li><strong>HTML</strong>: Formatted responses that can be displayed directly in a browser</li>
            </ul>
        </div>
        
        <div class="tab-content" id="endpoints">
            <h2>API Endpoints</h2>
            
            <div class="endpoint">
                <div class="endpoint-header">
                    <span class="method">POST</span>
                    <span class="path">/api/vicky</span>
                </div>
                <div class="endpoint-body">
                    <p>
                        Process a question with optional file attachment and get a detailed answer.
                        This endpoint combines the capabilities of all other endpoints with additional features.
                    </p>
                    
                    <h3>Parameters</h3>
                    <div class="parameters">
                        <div class="parameter">
                            <div class="param-name">question<span class="required">Required</span></div>
                            <div class="param-type">string</div>
                            <div class="param-desc">
                                The question or task description to process. This can include references to files, data science concepts, or specific assignments.
                            </div>
                        </div>
                        
                        <div class="parameter">
                            <div class="param-name">file<span class="optional">Optional</span></div>
                            <div class="param-type">file</div>
                            <div class="param-desc">
                                File to process alongside the question. Can be a ZIP archive, README.md, or any other file needed to answer the question.
                            </div>
                        </div>
                        
                        <div class="parameter">
                            <div class="param-name">format<span class="optional">Optional</span></div>
                            <div class="param-type">string</div>
                            <div class="param-desc">
                                Response format. Either "json" (default) or "html".
                            </div>
                        </div>
                        
                        <div class="parameter">
                            <div class="param-name">notify<span class="optional">Optional</span></div>
                            <div class="param-type">boolean</div>
                            <div class="param-desc">
                                Whether to send notifications about this API call. Default is false.
                            </div>
                        </div>
                    </div>
                    
                    <h3>Response</h3>
                    <p>For JSON responses (default):</p>
                    <div class="code-section">
                        <div class="code-header">
                            <span>Response (JSON)</span>
                            <button class="copy-btn">Copy</button>
                        </div>
                        <pre class="language-json">{
  "answer": "The detailed answer to the question",
  "metadata": {
    "processing_time_seconds": 1.25,
    "timestamp": "2023-04-15T14:32:10.123456",
    "api_version": "1.0"
  },
  "file": {
    "id": "abc123de",
    "name": "example.zip",
    "path": "uploads/20230415_143200_example.zip",
    "size": 12345
  }
}</pre>
                    </div>
                    
                    <p>For HTML responses (when format=html):</p>
                    <p>Returns HTML content that can be directly displayed in a browser with proper formatting of code blocks and other elements.</p>
                </div>
            </div>
            
            <div class="endpoint">
                <div class="endpoint-header">
                    <span class="method">POST</span>
                    <span class="path">/api/</span>
                </div>
                <div class="endpoint-body">
                    <p>
                        Simplified endpoint that returns minimal JSON responses. Ideal for automated grading systems that need just the answer.
                    </p>
                    
                    <h3>Parameters</h3>
                    <div class="parameters">
                        <div class="parameter">
                            <div class="param-name">question<span class="required">Required</span></div>
                            <div class="param-type">string</div>
                            <div class="param-desc">
                                The question or task description to process.
                            </div>
                        </div>
                        
                        <div class="parameter">
                            <div class="param-name">file<span class="optional">Optional</span></div>
                            <div class="param-type">file</div>
                            <div class="param-desc">
                                File to process alongside the question.
                            </div>
                        </div>
                    </div>
                    
                    <h3>Response</h3>
                    <div class="code-section">
                        <div class="code-header">
                            <span>Response (JSON)</span>
                            <button class="copy-btn">Copy</button>
                        </div>
                        <pre class="language-json">{
  "answer": "The answer to the question"
}</pre>
                    </div>
                </div>
            </div>
            
            <div class="endpoint">
                <div class="endpoint-header">
                    <span class="method">POST</span>
                    <span class="path">/api/process</span>
                </div>
                <div class="endpoint-body">
                    <p>
                        Process a question with an optional hint about the question type. Useful for specific assignment questions.
                    </p>
                    
                    <h3>Parameters</h3>
                    <div class="parameters">
                        <div class="parameter">
                            <div class="param-name">question<span class="required">Required</span></div>
                            <div class="param-type">string</div>
                            <div class="param-desc">
                                The question or task description to process.
                            </div>
                        </div>
                        
                        <div class="parameter">
                            <div class="param-name">file<span class="required">Required</span></div>
                            <div class="param-type">file</div>
                            <div class="param-desc">
                                File to process with the question.
                            </div>
                        </div>
                        
                        <div class="parameter">
                            <div class="param-name">question_type<span class="optional">Optional</span></div>
                            <div class="param-type">string</div>
                            <div class="param-desc">
                                Hint about the question type. Values: "npx_readme", "extract_zip"
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="tab-content" id="examples">
            <h2>Example API Usage</h2>
            
            <div class="sub-section">
                <h3>Example 1: Simple Question</h3>
                <p>Asking a data science question without any file:</p>
                
                <div class="code-section">
                    <div class="code-header">
                        <span>cURL Example</span>
                        <button class="copy-btn">Copy</button>
                    </div>
                    <pre class="curl-example">curl -X POST "https://app.algsoch.tech/api/vicky" \
  -F "question=What is the difference between precision and recall in machine learning?"</pre>
                </div>
                
                <div class="code-section">
                    <div class="code-header">
                        <span>Response</span>
                        <button class="copy-btn">Copy</button>
                    </div>
                    <pre class="language-json">{
  "answer": "Precision and recall are metrics used to evaluate classification models in machine learning:\n\n- **Precision** measures the accuracy of positive predictions. It's calculated as TP/(TP+FP), where TP is true positives and FP is false positives. High precision means that when the model predicts the positive class, it's likely correct.\n\n- **Recall** (also called sensitivity) measures the ability to find all positive instances. It's calculated as TP/(TP+FN), where FN is false negatives. High recall means the model captures most of the actual positive cases.\n\nThere's typically a trade-off between precision and recall - increasing one often decreases the other. Which metric to prioritize depends on your application. For example, in medical testing, high recall may be more important to catch all potential cases, while in spam filtering, high precision might be preferred to avoid flagging legitimate emails.",
  "metadata": {
    "processing_time_seconds": 0.85,
    "timestamp": "2023-04-15T14:32:10.123456",
    "api_version": "1.0"
  }
}</pre>
                </div>
            </div>
            
            <div class="sub-section">
                <h3>Example 2: Processing a ZIP File</h3>
                <p>Extracting data from a ZIP file containing a CSV:</p>
                
                <div class="code-section">
                    <div class="code-header">
                        <span>cURL Example</span>
                        <button class="copy-btn">Copy</button>
                    </div>
                    <pre class="curl-example">curl -X POST "https://app.algsoch.tech/api/vicky" \
  -F "question=Extract data from this ZIP file which has a single extract.csv file inside. What is the value in the \"answer\" column of the CSV file?" \
  -F "file=@/path/to/data.zip"</pre>
                </div>
                
                <div class="code-section">
                    <div class="code-header">
                        <span>Response</span>
                        <button class="copy-btn">Copy</button>
                    </div>
                    <pre class="language-json">{
  "answer": "1234567890",
  "metadata": {
    "processing_time_seconds": 2.34,
    "timestamp": "2023-04-15T14:35:22.654321",
    "api_version": "1.0"
  },
  "file": {
    "id": "9a8b7c6d",
    "name": "data.zip",
    "path": "uploads/20230415_143520_data.zip",
    "size": 5678
  }
}</pre>
                </div>
            </div>
            
            <div class="sub-section">
                <h3>Example 3: Formatting README.md with npx prettier</h3>
                <p>Get the output of npx prettier on a README.md file:</p>
                
                <div class="code-section">
                    <div class="code-header">
                        <span>cURL Example</span>
                        <button class="copy-btn">Copy</button>
                    </div>
                    <pre class="curl-example">curl -X POST "https://app.algsoch.tech/api/vicky" \
  -F "question=What is the output of running npx prettier on this README.md file?" \
  -F "file=@/path/to/README.md" \
  -F "format=html"</pre>
                </div>
                
                <p>The response will be HTML content with proper formatting of the prettier output.</p>
            </div>
        </div>
        
        <div class="tab-content" id="try-it">
            <h2>Try the API</h2>
            
            <div class="try-it">
                <div class="try-it-header">
                    <h3>API Tester</h3>
                    <button class="toggle-btn" id="showForm">Show Form</button>
                </div>
                
                <form class="try-it-form" id="apiForm" style="display: none;">
                    <div class="form-group">
                        <label class="form-label" for="apiUrl">API Endpoint</label>
                        <input class="form-input" type="text" id="apiUrl" value="https://app.algsoch.tech/api/vicky" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label" for="question">Question</label>
                        <textarea class="form-textarea" id="question" placeholder="Enter your question here..." required></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label" for="file">File (optional)</label>
                        <input class="form-input" type="file" id="file">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label" for="format">Response Format</label>
                        <select class="form-input" id="format">
                            <option value="json">JSON</option>
                            <option value="html">HTML</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="submit-btn">Send Request</button>
                </form>
                
                <div class="result" id="result">
                    <h4>Response:</h4>
                    <pre id="response"></pre>
                </div>
            </div>
        </div>
    </div>
    
    <footer>
        <p>TDS - Tools for Data Science API | <a href="https://app.algsoch.tech">app.algsoch.tech</a></p>
        <p>&copy; 2023 All rights reserved.</p>
    </footer>
    
    <script>
    // Video Transcription Logic
    document.addEventListener('DOMContentLoaded', function() {
    const videoUrlInput = document.getElementById('videoUrl');
    const videoFileInput = document.getElementById('videoFile');
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    const correctTextCheckbox = document.getElementById('correctText');
    const translateToHindiCheckbox = document.getElementById('translateToHindi');
    const transcribeBtn = document.getElementById('transcribeBtn');
    
    const transcriptionResults = document.querySelector('.transcription-results');
    const englishTranscript = document.getElementById('englishTranscript');
    const hindiTranscript = document.getElementById('hindiTranscript');
    const englishAudio = document.getElementById('englishAudio');
    const hindiAudio = document.getElementById('hindiAudio');
    
    const copyTranscriptBtn = document.getElementById('copyTranscriptBtn');
    const downloadTranscriptBtn = document.getElementById('downloadTranscriptBtn');
    const clearTranscriptionBtn = document.getElementById('clearTranscriptionBtn');
    
    const hindiResultTab = document.querySelector('.result-tab[data-result="hindi"]');
    const transcriptionUsageCount = document.getElementById('transcriptionUsageCount');
    
    // Initialize usage counter from localStorage
    let usageCount = parseInt(localStorage.getItem('transcriptionUsageCount') || '0');
    updateUsageCount(usageCount);
    
    // Function to update and display usage count
    function updateUsageCount(count) {
        usageCount = count;
        localStorage.setItem('transcriptionUsageCount', count.toString());
        transcriptionUsageCount.textContent = `Used: ${count} times`;
    }
    
    // Tab switching for URL/Upload
    document.querySelectorAll('.transcription-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // Update active tab
            document.querySelectorAll('.transcription-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding tab content
            const tabId = this.getAttribute('data-tab') + 'Tab';
            document.querySelectorAll('.transcription-tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Tab switching for results (English/Hindi)
    document.querySelectorAll('.result-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // Update active tab
            document.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding result
            const resultId = this.getAttribute('data-result') + 'Result';
            document.querySelectorAll('.result-container').forEach(container => {
                container.classList.remove('active');
            });
            document.getElementById(resultId).classList.add('active');
        });
    });
    
    // Transcribe button click
    transcribeBtn.addEventListener('click', function() {
        // Get input values
        const videoUrl = videoUrlInput.value.trim();
        const videoFile = videoFileInput.files[0];
        const startTime = startTimeInput.value ? parseInt(startTimeInput.value) : 0;
        const endTime = endTimeInput.value ? parseInt(endTimeInput.value) : null;
        const correctText = correctTextCheckbox.checked;
        const translateToHindi = translateToHindiCheckbox.checked;
        
        // Validate input
        if (!videoUrl && !videoFile) {
            alert('Please enter a video URL or upload a video file');
            return;
        }
        
        // Create form data
        const formData = new FormData();
        
        if (videoUrl) {
            formData.append('video_url', videoUrl);
        }
        
        if (videoFile) {
            formData.append('file', videoFile);
        }
        
        formData.append('start_time', startTime);
        if (endTime) formData.append('end_time', endTime);
        formData.append('correct_text', correctText);
        formData.append('translate_to_hindi', translateToHindi);
        
        // Show loading indicator
        transcribeBtn.disabled = true;
        transcribeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Transcribing...';
        
        // Hide results while processing
        transcriptionResults.style.display = 'none';
        
        // Send request to server
        fetch('/transcribe-video', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            transcribeBtn.disabled = false;
            transcribeBtn.innerHTML = 'Transcribe Video';
            
            if (data.success) {
                // Update usage count
                updateUsageCount(usageCount + 1);
                
                // Display English transcript
                englishTranscript.textContent = data.corrected_transcript || data.transcript;
                
                // Set English audio if available
                if (data.audio_english_id) {
                    englishAudio.src = `/audio/${data.audio_english_id}`;
                    englishAudio.parentElement.style.display = 'block';
                } else {
                    englishAudio.parentElement.style.display = 'none';
                }
                
                // Display Hindi transcript and tab if available
                if (data.hindi_transcript) {
                    hindiTranscript.textContent = data.hindi_transcript;
                    hindiResultTab.style.display = 'block';
                    
                    // Set Hindi audio if available
                    if (data.audio_hindi_id) {
                        hindiAudio.src = `/audio/${data.audio_hindi_id}`;
                        hindiAudio.parentElement.style.display = 'block';
                    } else {
                        hindiAudio.parentElement.style.display = 'none';
                    }
                } else {
                    hindiResultTab.style.display = 'none';
                }
                
                // Show results
                transcriptionResults.style.display = 'block';
                
                // Reset result tabs to English
                document.querySelector('.result-tab[data-result="english"]').click();
            } else {
                alert('Error: ' + (data.error || 'Failed to transcribe video'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            transcribeBtn.disabled = false;
            transcribeBtn.innerHTML = 'Transcribe Video';
            alert('Error transcribing video. Please try again.');
        });
    });
    
    // Copy transcript button
    copyTranscriptBtn.addEventListener('click', function() {
        // Get active result container
        const activeContainer = document.querySelector('.result-container.active');
        const textElement = activeContainer.querySelector('.transcript-text');
        
        // Copy text to clipboard
        navigator.clipboard.writeText(textElement.textContent).then(() => {
            this.textContent = 'Copied!';
            setTimeout(() => { this.textContent = 'Copy Text'; }, 2000);
        });
    });
    
    // Download transcript button
    downloadTranscriptBtn.addEventListener('click', function() {
        // Get active result container
        const activeContainer = document.querySelector('.result-container.active');
        const textElement = activeContainer.querySelector('.transcript-text');
        const isHindi = activeContainer.id === 'hindiResult';
        
        // Create file
        const filename = `transcript_${isHindi ? 'hindi' : 'english'}_${new Date().toISOString().slice(0,10)}.txt`;
        const blob = new Blob([textElement.textContent], {type: 'text/plain'});
        
        // Create download link and click it
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    });
    
    // Clear button
    clearTranscriptionBtn.addEventListener('click', function() {
        // Clear inputs
        videoUrlInput.value = '';
        videoFileInput.value = '';
        startTimeInput.value = '';
        endTimeInput.value = '';
        correctTextCheckbox.checked = false;
        translateToHindiCheckbox.checked = false;
        
        // Clear results
        englishTranscript.textContent = '';
        hindiTranscript.textContent = '';
        englishAudio.src = '';
        hindiAudio.src = '';
        
        // Hide results section
        transcriptionResults.style.display = 'none';
    });
});
        // Tab switching
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Update active tab
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Show corresponding content
                const tabId = tab.getAttribute('data-tab');
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(tabId).classList.add('active');
            });
        });
        
        // Copy buttons
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const pre = btn.parentElement.nextElementSibling;
                const text = pre.textContent;
                
                navigator.clipboard.writeText(text).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
                });
            });
        });
        
        // Toggle API form
        document.getElementById('showForm').addEventListener('click', () => {
            const form = document.getElementById('apiForm');
            const isVisible = form.style.display !== 'none';
            form.style.display = isVisible ? 'none' : 'block';
            document.getElementById('showForm').textContent = isVisible ? 'Show Form' : 'Hide Form';
        });
        
        // API form submission
        document.getElementById('apiForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const apiUrl = document.getElementById('apiUrl').value;
            const question = document.getElementById('question').value;
            const file = document.getElementById('file').files[0];
            const format = document.getElementById('format').value;
            
            const formData = new FormData();
            formData.append('question', question);
            formData.append('format', format);
            
            if (file) {
                formData.append('file', file);
            }
            
            document.getElementById('response').textContent = 'Loading...';
            document.getElementById('result').style.display = 'block';
            
            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    body: formData
                });
                
                if (format === 'html') {
                    const html = await response.text();
                    document.getElementById('response').innerHTML = html;
                } else {
                    const data = await response.json();
                    document.getElementById('response').textContent = JSON.stringify(data, null, 2);
                }
            } catch (error) {
                document.getElementById('response').textContent = `Error: ${error.message}`;
            }
        });
    </script>
</body>
</html>
""")



# ===== PYDANTIC MODELS =====

class SimilarityRequest(BaseModel):
    docs: List[str]
    query: str

class SimilarityResponse(BaseModel):
    matches: List[str]

# ===== UTILITY FUNCTIONS =====

def get_mock_embedding(text: str) -> np.ndarray:
    """Generate a mock embedding for text (simple hash-based approach)"""
    import hashlib
    
    # Simple hash-based embedding
    hash_obj = hashlib.md5(text.encode())
    hash_digest = hash_obj.hexdigest()
    
    # Convert hex to numbers and normalize
    embedding = []
    for i in range(0, len(hash_digest), 2):
        val = int(hash_digest[i:i+2], 16) / 255.0
        embedding.append(val)
    
    # Pad or truncate to fixed size (16 dimensions)
    while len(embedding) < 16:
        embedding.append(0.0)
    
    return np.array(embedding[:16])

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)

# Define model for feedback data
class FeedbackModel(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    type: str
    feedback: str

@app.post("/submit-feedback")
async def submit_feedback(request: Request, feedback: FeedbackModel):
    """Handle feedback submission and send to communication channels"""
    try:
        # Log the feedback
        logger.info(f"Received feedback: Type={feedback.type}, Name={feedback.name or 'Anonymous'}")
        
        # Get notification URLs from environment
        discord_webhook = os.environ.get("DISCORD_WEBHOOK")
        slack_webhook = os.environ.get("SLACK_WEBHOOK")
        
        # Create feedback message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get user information
        ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(',')[0].strip()
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        # Format message for notifications
        message_title = f"📝 New {feedback.type.capitalize()} Submitted"
        
        # Send to Discord if configured
        if discord_webhook:
            payload = {
                "embeds": [{
                    "title": message_title,
                    "color": 5814783,  # Purple color
                    "fields": [
                        {
                            "name": "Feedback",
                            "value": feedback.feedback
                        },
                        {
                            "name": "Type",
                            "value": feedback.type,
                            "inline": True
                        },
                        {
                            "name": "From",
                            "value": feedback.name or "Anonymous",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": f"Submitted at {timestamp}"
                    }
                }]
            }
            
            # Add email if provided
            if feedback.email:
                payload["embeds"][0]["fields"].append({
                    "name": "Email",
                    "value": feedback.email,
                    "inline": True
                })
            
            # Add source info
            payload["embeds"][0]["fields"].append({
                "name": "Source Info",
                "value": f"IP: {ip}\nUser Agent: {user_agent[:100]}..."
            })
            
            requests.post(discord_webhook, json=payload, timeout=5)
            logger.info("Feedback sent to Discord")
        
        # Send to Slack if configured
        if slack_webhook:
            slack_fields = [
                {
                    "title": "Feedback",
                    "value": feedback.feedback,
                    "short": False
                },
                {
                    "title": "Type",
                    "value": feedback.type,
                    "short": True
                },
                {
                    "title": "From",
                    "value": feedback.name or "Anonymous",
                    "short": True
                }
            ]
            
            # Add email if provided
            if feedback.email:
                slack_fields.append({
                    "title": "Email",
                    "value": feedback.email,
                    "short": True
                })
            
            # Add source info
            slack_fields.append({
                "title": "Source Info",
                "value": f"IP: {ip}\nUser Agent: {user_agent[:100]}..."
            })
            
            slack_payload = {
                "text": message_title,
                "attachments": [
                    {
                        "color": "#4c2882",
                        "fields": slack_fields,
                        "footer": f"Submitted at {timestamp}"
                    }
                ]
            }
            
            requests.post(slack_webhook, json=slack_payload, timeout=5)
            logger.info("Feedback sent to Slack")
        
        # Store feedback in a log file
        feedback_log_file = Path("feedback_logs.json")
        
        # Load existing feedback
        feedback_logs = []
        if feedback_log_file.exists():
            try:
                with open(feedback_log_file, "r") as f:
                    feedback_logs = json.load(f)
            except json.JSONDecodeError:
                feedback_logs = []
        
        # Add new feedback
        feedback_logs.append({
            "timestamp": timestamp,
            "type": feedback.type,
            "name": feedback.name,
            "email": feedback.email,
            "feedback": feedback.feedback,
            "ip_address": ip,
            "user_agent": user_agent
        })
        
        # Save feedback logs
        with open(feedback_log_file, "w") as f:
            json.dump(feedback_logs, f, indent=2)
        
        return {"success": True, "message": "Feedback submitted successfully"}
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return {"success": False, "message": f"Error submitting feedback: {str(e)}"}
@app.get("/admin/feedback-logs")
async def view_feedback_logs(request: Request, key: str = None):
    """View submitted feedback (protected by admin key)"""
    # Security check
    admin_key = os.environ.get("ADMIN_KEY")
    if not key or key.strip() != admin_key:
        logger.warning(f"Invalid admin key for feedback logs")
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Read logs
    feedback_log_file = Path("feedback_logs.json")
    if not feedback_log_file.exists():
        return {"feedback": [], "count": 0}
    
    try:
        with open(feedback_log_file, "r") as f:
            feedback_logs = json.load(f)
        
        # Count by type
        type_counts = {}
        for log in feedback_logs:
            feedback_type = log.get("type", "unknown")
            if feedback_type not in type_counts:
                type_counts[feedback_type] = 0
            type_counts[feedback_type] += 1
        
        return {
            "feedback": feedback_logs,
            "count": len(feedback_logs),
            "by_type": type_counts,
            "recent": feedback_logs[-5:]  # Last 5 feedback items
        }
    except Exception as e:
        logger.error(f"Error getting feedback logs: {e}")
        return {"error": str(e)}
@app.post("/api/process")
async def api_process(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...),
    question_type: str = Form(None)  # Optional hint about which question it is
):
    """Process a question with an optional file through API"""
    try:
        if file and file.filename:
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Auto-detect the question type from file extension if not specified
            if not question_type:
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext == ".md":
                    question_type = "npx_readme"  # GA1 third question
                elif file_ext == ".zip":
                    question_type = "extract_zip"  # GA1 eighth question
            
            # Add appropriate context based on detected question type
            if question_type == "npx_readme" or (file.filename.lower() == "readme.md"):
                question += f" The README.md file is located at {file_path}"
            elif question_type == "extract_zip" or file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the enhanced question
        answer = answer_question(question)
        
        # Return a structured response for API clients
        return {
            "success": True,
            "answer": answer,
            "file_processed": bool(file and file.filename),
            "question": question
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_details": str(e.__class__.__name__)
        }
@app.post("/api/")
async def api_direct(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...)
):
    """Process questions with files using the standard API endpoint format"""
    # Log the IP address
    log_ip_address(request, "/api/", question)
    """Process questions with files using the standard API endpoint format"""
    # Send notification about API access
    threading.Thread(target=send_api_notification, args=(request, question)).start()
    try:
        file_path = None
        # If file is uploaded, always use it and don't try to extract from query
        if file and file.filename:
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            try:
                contents = await file.read()
                temp_file.write(contents)
            finally:
                temp_file.close()
            file_path = temp_file.name
            question += f" [Using uploaded file: {file.filename}]"
        
        # Process the question (with explicit file path if available)
        raw_answer = answer_question(question, explicit_file_path=file_path)
        
        # Clean up execution time info
        clean_answer = re.sub(r'Execution time: \d+\.\d+s', '', raw_answer).strip()
        
        return {"answer": clean_answer}
    except Exception as e:
        logger.error(f"API error: {e}")
        return {"answer": f"Error: {str(e)}"}
@app.get("/api/vicky", response_class=HTMLResponse)
async def vicky_api_docs(request: Request):
    """Comprehensive documentation for the Vicky API"""
    # Log access to this documentation page
    log_ip_address(request, "/api/vicky", "API documentation access")
    
    return templates.TemplateResponse(
        "vicky_api_docs.html",
        {"request": request}
    )

@app.post("/api/vicky")
async def vicky_api(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...),
    format: str = Form("json"),
    notify: bool = Form(False)
):
    """Advanced API endpoint with enhanced features"""
    # Log the IP address
    log_ip_address(request, "/api/vicky", question)
    
    # Send notification if requested
    if notify:
        threading.Thread(target=send_api_notification, args=(request, question)).start()
    
    try:
        file_path = None
        file_info = {}
        
        # Process uploaded file if present
        if file and file.filename:
            # Save the file with a timestamp prefix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            file_info = {
                "id": file_id,
                "name": file.filename,
                "path": str(file_path),
                "size": os.path.getsize(file_path)
            }
            
            # Add file context to the question
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            elif file_ext == ".md":
                question += f" The README.md file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        start_time = time.time()
        raw_answer = answer_question(question, explicit_file_path=file_path)
        processing_time = time.time() - start_time
        
        # Clean up execution time info from the answer if present
        clean_answer = re.sub(r'Execution time: \d+\.\d+s', '', raw_answer).strip()
        
        # Format the response based on request
        if format.lower() == "html":
            # Convert markdown-like formatting to HTML
            import html
            html_answer = html.escape(clean_answer)
            # Convert code blocks
            html_answer = re.sub(
                r'```(.*?)```', 
                r'<pre><code>\1</code></pre>', 
                html_answer, 
                flags=re.DOTALL
            )
            # Convert inline code
            html_answer = re.sub(r'`([^`]+)`', r'<code>\1</code>', html_answer)
            
            return HTMLResponse(
                f"<html><body><div class='answer'>{html_answer}</div></body></html>",
                media_type="text/html"
            )
        else:  # Default to JSON
            response = {
                "answer": clean_answer,
                "metadata": {
                    "processing_time_seconds": round(processing_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "api_version": "1.0"
                }
            }
            
            if file_info:
                response["file"] = file_info
                
            return response
            
    except Exception as e:
        logger.error(f"Vicky API error: {e}")
        if format.lower() == "html":
            error_html = f"<html><body><div class='error'>Error: {html.escape(str(e))}</div></body></html>"
            return HTMLResponse(error_html, media_type="text/html", status_code=500)
        else:
            return {
                "error": str(e),
                "error_type": e.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
@app.get("/api/vicky", response_class=HTMLResponse)
async def vicky_api_docs(request: Request):
    """Comprehensive documentation for the Vicky API"""
    # Log access to this documentation page
    log_ip_address(request, "/api/vicky", "API documentation access")
    
    return templates.TemplateResponse(
        "vicky_api_docs.html",
        {"request": request}
    )

@app.post("/api/vicky")
async def vicky_api(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...),
    format: str = Form("json"),
    notify: bool = Form(False)
):
    """Advanced API endpoint with enhanced features"""
    # Log the IP address
    log_ip_address(request, "/api/vicky", question)
    
    # Send notification if requested
    if notify:
        threading.Thread(target=send_api_notification, args=(request, question)).start()
    
    try:
        file_path = None
        file_info = {}
        
        # Process uploaded file if present
        if file and file.filename:
            # Save the file with a timestamp prefix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            file_info = {
                "id": file_id,
                "name": file.filename,
                "path": str(file_path),
                "size": os.path.getsize(file_path)
            }
            
            # Add file context to the question
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            elif file_ext == ".md":
                question += f" The README.md file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        start_time = time.time()
        raw_answer = answer_question(question, explicit_file_path=file_path)
        processing_time = time.time() - start_time
        
        # Clean up execution time info from the answer if present
        clean_answer = re.sub(r'Execution time: \d+\.\d+s', '', raw_answer).strip()
        
        # Format the response based on request
        if format.lower() == "html":
            # Convert markdown-like formatting to HTML
            import html
            html_answer = html.escape(clean_answer)
            # Convert code blocks
            html_answer = re.sub(
                r'```(.*?)```', 
                r'<pre><code>\1</code></pre>', 
                html_answer, 
                flags=re.DOTALL
            )
            # Convert inline code
            html_answer = re.sub(r'`([^`]+)`', r'<code>\1</code>', html_answer)
            
            return HTMLResponse(
                f"<html><body><div class='answer'>{html_answer}</div></body></html>",
                media_type="text/html"
            )
        else:  # Default to JSON
            response = {
                "answer": clean_answer,
                "metadata": {
                    "processing_time_seconds": round(processing_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "api_version": "1.0"
                }
            }
            
            if file_info:
                response["file"] = file_info
                
            return response
            
    except Exception as e:
        logger.error(f"Vicky API error: {e}")
        if format.lower() == "html":
            error_html = f"<html><body><div class='error'>Error: {html.escape(str(e))}</div></body></html>"
            return HTMLResponse(error_html, media_type="text/html", status_code=500)
        else:
            return {
                "error": str(e),
                "error_type": e.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
@app.get("/api/vicky", response_class=HTMLResponse)
async def vicky_api_docs(request: Request):
    """Comprehensive documentation for the Vicky API"""
    # Log access to this documentation page
    log_ip_address(request, "/api/vicky", "API documentation access")
    
    return templates.TemplateResponse(
        "vicky_api_docs.html",
        {"request": request}
    )

@app.post("/api/vicky")
async def vicky_api(
    request: Request,
    file: UploadFile = File(None),
    question: str = Form(...),
    format: str = Form("json"),
    notify: bool = Form(False)
):
    """Advanced API endpoint with enhanced features"""
    # Log the IP address
    log_ip_address(request, "/api/vicky", question)
    
    # Send notification if requested
    if notify:
        threading.Thread(target=send_api_notification, args=(request, question)).start()
    
    try:
        file_path = None
        file_info = {}
        
        # Process uploaded file if present
        if file and file.filename:
            # Save the file with a timestamp prefix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = UPLOADS_DIR / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Register the file and get an ID
            file_id = register_uploaded_file(file.filename, str(file_path))
            file_info = {
                "id": file_id,
                "name": file.filename,
                "path": str(file_path),
                "size": os.path.getsize(file_path)
            }
            
            # Add file context to the question
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext == ".zip":
                question += f" The ZIP file is located at {file_path}"
            elif file_ext == ".md":
                question += f" The README.md file is located at {file_path}"
            else:
                question += f" The file {file.filename} is located at {file_path}"
        
        # Process the question
        start_time = time.time()
        raw_answer = answer_question(question, explicit_file_path=file_path)
        processing_time = time.time() - start_time
        
        # Clean up execution time info from the answer if present
        clean_answer = re.sub(r'Execution time: \d+\.\d+s', '', raw_answer).strip()
        
        # Format the response based on request
        if format.lower() == "html":
            # Convert markdown-like formatting to HTML
            import html
            html_answer = html.escape(clean_answer)
            # Convert code blocks
            html_answer = re.sub(
                r'```(.*?)```', 
                r'<pre><code>\1</code></pre>', 
                html_answer, 
                flags=re.DOTALL
            )
            # Convert inline code
            html_answer = re.sub(r'`([^`]+)`', r'<code>\1</code>', html_answer)
            
            return HTMLResponse(
                f"<html><body><div class='answer'>{html_answer}</div></body></html>",
                media_type="text/html"
            )
        else:  # Default to JSON
            response = {
                "answer": clean_answer,
                "metadata": {
                    "processing_time_seconds": round(processing_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "api_version": "1.0"
                }
            }
            
            if file_info:
                response["file"] = file_info
                
            return response
            
    except Exception as e:
        logger.error(f"Vicky API error: {e}")
        if format.lower() == "html":
            error_html = f"<html><body><div class='error'>Error: {html.escape(str(e))}</div></body></html>"
            return HTMLResponse(error_html, media_type="text/html", status_code=500)
        else:
            return {
                "error": str(e),
                "error_type": e.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }

@app.get("/connection-info")
async def connection_info():
    """Get server connection details - useful for debugging remote connections"""
    import platform
    import socket
    
    # Get hostname and IP
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except:
        ip = "Unable to determine IP"
    
    # Return connection info
    return {
        "server": {
            "hostname": hostname,
            "operating_system": platform.system(),
            "ip_address": ip,
            "python_version": platform.python_version(),
        },
        "request_handling": {
            "file_upload_directory": str(UPLOADS_DIR.absolute()),
            "ngrok_support": "Supported (use 'ngrok http 8000' to expose)"
        }
    }

# Add this to the startup code of your application
@app.on_event("startup")
async def startup_event():
    """Run when the application starts"""
    # Create uploads directory if it doesn't exist
    UPLOADS_DIR.mkdir(exist_ok=True)
    logger.info(f"Uploads directory ready: {UPLOADS_DIR.absolute()}")
    
    # Load existing files into registry
    load_existing_files()

def load_existing_files():
    """Load any existing files in the uploads directory into the registry"""
    if UPLOADS_DIR.exists():
        for file_path in UPLOADS_DIR.iterdir():
            if file_path.is_file():
                # Register existing file with its original timestamp if possible
                try:
                    # Try to extract timestamp from filename (assumes format: YYYYMMDD_HHMMSS_originalname)
                    filename = file_path.name
                    parts = filename.split('_', 2)
                    if len(parts) >= 3:
                        original_name = parts[2]  # Get original filename
                        file_id = register_uploaded_file(original_name, str(file_path))
                        logger.info(f"Loaded existing file: {filename} (ID: {file_id})")
                except Exception as e:
                    logger.warning(f"Couldn't register existing file {file_path}: {e}")

@app.post("/debug-form")
async def debug_form(request: Request):
    """Debug endpoint to see what's being received in a form submission"""
    form_data = await request.form()
    return {
        "received_fields": list(form_data.keys()),
        "form_data": {k: str(v) for k, v in form_data.items()},
        "content_type": request.headers.get("content-type", "none")
    }
@app.get("/admin/ip-logs")
async def view_ip_logs(request: Request, key: str = None):
    """View collected IP logs (protected by admin key)"""
    # Create logs directory and file if it doesn't exist
    IP_LOGS_FILE = Path("ip_logs.json")
    if not IP_LOGS_FILE.exists():
        with open(IP_LOGS_FILE, "w") as f:
            json.dump([], f)
    
    # Get admin key with more robust handling
    admin_key = os.environ.get("ADMIN_KEY")
    logger.info(f"Admin key from env: '{admin_key}' (length: {len(admin_key) if admin_key else 0})")
    
    # Debug info to help diagnose issues
    logger.info(f"Received key: '{key}' (length: {len(key) if key else 0})")
    
    # More flexible key matching
    if not key or key.strip() != admin_key:
        # Show what key we're expecting for debugging purposes
        logger.warning(f"Invalid admin key: received '{key}', expected '{admin_key}'")
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    try:
        # Load existing logs or return empty list if no logs or invalid format
        try:
            with open(IP_LOGS_FILE, "r") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []
            
        # Get unique IP count
        unique_ips = set(entry["ip_address"] for entry in logs if "ip_address" in entry)
            
        return {
            "logs": logs,
            "count": len(logs),
            "unique_ips": len(unique_ips),
            "unique_ip_list": list(unique_ips)
        }
    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}")
        return {"error": f"Could not read logs: {str(e)}"}
@app.get("/admin/api-stats")
async def api_stats(request: Request, key: str = None):
    """View API usage statistics"""
    # Security check
    admin_key = os.environ.get("ADMIN_KEY")
    if not key or key.strip() != admin_key:
        logger.warning(f"Invalid admin key for API stats: received '{key}'")
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Read logs
    try:
        if not IP_LOGS_FILE.exists():
            return {"api_requests": 0, "unique_ips": 0}
            
        with open(IP_LOGS_FILE, "r") as f:
            logs = json.load(f)
        
        # Filter to only API requests
        api_logs = [log for log in logs if log.get("endpoint") == "/api/"]
        
        # Get unique IPs
        unique_ips = set(log["ip_address"] for log in api_logs if "ip_address" in log)
        
        # Group by day
        daily_counts = {}
        for log in api_logs:
            if "timestamp" in log:
                day = log["timestamp"].split("T")[0]
                if day not in daily_counts:
                    daily_counts[day] = 0
                daily_counts[day] += 1
        
        return {
            "api_requests": len(api_logs),
            "unique_ips": len(unique_ips),
            "daily_counts": daily_counts,
            "recent_requests": api_logs[-10:]  # Last 10 requests
        }
    except Exception as e:
        logger.error(f"Error getting API stats: {e}")
        return {"error": str(e)}
@app.post("/log-base64-usage")
async def log_base64_usage(request: Request):
    """Log Base64 decoder usage"""
    try:
        # Get IP address
        ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(',')[0].strip()
            
        # Get usage data from the request
        data = await request.json()
        count = data.get("count", 0)
        
        # Log to a separate file
        usage_log_file = Path("base64_usage_logs.json")
        
        # Load existing logs
        logs = []
        if usage_log_file.exists():
            try:
                with open(usage_log_file, "r") as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        
        # Add new entry
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "ip_address": ip,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "usage_count": count
        })
        
        # Save logs
        with open(usage_log_file, "w") as f:
            json.dump(logs, f, indent=2)
            
        logger.info(f"Logged Base64 decoder usage: IP {ip}, Count {count}")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error logging Base64 usage: {e}")
        return {"success": False, "error": str(e)}
@app.get("/admin/base64-stats")
async def base64_stats(request: Request, key: str = None):
    """View Base64 decoder usage statistics"""
    # Security check
    admin_key = os.environ.get("ADMIN_KEY")
    if not key or key.strip() != admin_key:
        logger.warning(f"Invalid admin key for Base64 stats")
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Read logs
    try:
        usage_log_file = Path("base64_usage_logs.json")
        if not usage_log_file.exists():
            return {"total_uses": 0, "unique_ips": 0}
            
        with open(usage_log_file, "r") as f:
            logs = json.load(f)
        
        # Get unique IPs
        unique_ips = set(log["ip_address"] for log in logs if "ip_address" in log)
        
        # Calculate highest usage count
        highest_count = 0
        for log in logs:
            count = log.get("usage_count", 0)
            if count > highest_count:
                highest_count = count
        
        # Group by day
        daily_counts = {}
        for log in logs:
            if "timestamp" in log:
                day = log["timestamp"].split("T")[0]
                if day not in daily_counts:
                    daily_counts[day] = 0
                daily_counts[day] += 1
        
        return {
            "total_logs": len(logs),
            "unique_ips": len(unique_ips),
            "highest_usage_count": highest_count,
            "daily_counts": daily_counts,
            "recent_logs": logs[-10:]  # Last 10 logs
        }
    except Exception as e:
        logger.error(f"Error getting Base64 stats: {e}")
        return {"error": str(e)}
@app.post("/log-html-viewer-usage")
async def log_html_viewer_usage(request: Request):
    """Log HTML viewer usage"""
    try:
        # Get IP address
        ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(',')[0].strip()
            
        # Get usage data from the request
        data = await request.json()
        count = data.get("count", 0)
        
        # Log to a separate file
        usage_log_file = Path("html_viewer_logs.json")
        
        # Load existing logs
        logs = []
        if usage_log_file.exists():
            try:
                with open(usage_log_file, "r") as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        
        # Add new entry
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "ip_address": ip,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "usage_count": count
        })
        
        # Save logs
        with open(usage_log_file, "w") as f:
            json.dump(logs, f, indent=2)
            
        logger.info(f"Logged HTML viewer usage: IP {ip}, Count {count}")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error logging HTML viewer usage: {e}")
        return {"success": False, "error": str(e)}
@app.get("/admin/html-viewer-stats")
async def html_viewer_stats(request: Request, key: str = None):
    """View HTML viewer usage statistics"""
    # Security check
    admin_key = os.environ.get("ADMIN_KEY")
    if not key or key.strip() != admin_key:
        logger.warning(f"Invalid admin key for HTML viewer stats")
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Read logs
    try:
        usage_log_file = Path("html_viewer_logs.json")
        if not usage_log_file.exists():
            return {"total_uses": 0, "unique_ips": 0}
            
        with open(usage_log_file, "r") as f:
            logs = json.load(f)
        
        # Get unique IPs
        unique_ips = set(log["ip_address"] for log in logs if "ip_address" in log)
        
        # Group by domain
        domains = {}
        for log in logs:
            if "url" in log:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(log["url"]).netloc
                    if domain not in domains:
                        domains[domain] = 0
                    domains[domain] += 1
                except:
                    pass
        
        return {
            "total_uses": len(logs),
            "unique_ips": len(unique_ips),
            "top_domains": dict(sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_logs": logs[-10:]  # Last 10 logs
        }
    except Exception as e:
        logger.error(f"Error getting HTML viewer stats: {e}")
        return {"error": str(e)}

# ===== INTEGRATED API ROUTES (Azure Compatible) =====

@app.post("/api/similarity", response_model=SimilarityResponse)
async def find_similar_documents(request: SimilarityRequest = Body(...)):
    """
    Semantic search through documents using text embeddings
    Replaces the separate server from ga3_seventh_solution
    """
    try:
        documents = request.docs
        query = request.query
        
        # Generate embeddings for query and documents
        query_embedding = get_mock_embedding(query)
        doc_embeddings = [get_mock_embedding(doc) for doc in documents]
        
        # Calculate similarity scores
        similarity_scores = [
            cosine_similarity(query_embedding, doc_emb) 
            for doc_emb in doc_embeddings
        ]
        
        # Get indices of top 3 most similar documents
        top_k = min(3, len(documents))
        top_indices = np.argsort(similarity_scores)[-top_k:][::-1]
        
        # Get the documents corresponding to these indices
        top_matches = [documents[i] for i in top_indices]
        
        return {"matches": top_matches}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing similarity request: {str(e)}")

@app.get("/api/similarity")
async def similarity_info():
    """Information about the similarity endpoint"""
    return {
        "message": "This endpoint requires a POST request with JSON data",
        "required_format": {
            "docs": ["Document 1", "Document 2", "Document 3"],
            "query": "Your search query"
        },
        "example_curl": 'curl -X POST "http://localhost:8000/api/similarity" -H "Content-Type: application/json" -d \'{"docs": ["Document 1", "Document 2"], "query": "search term"}\''
    }

@app.get("/api/student-marks")
async def get_student_marks(name: Optional[List[str]] = Query(None)):
    """
    Get student marks data from JSON file
    Replaces the separate server from ga2_sixth_solution
    """
    try:
        # Try to load student data - handle file paths gracefully
        default_file_paths = [
            "E://data science tool//GA2//q-vercel-python.json",
            "q-vercel-python.json",
            "student_data.json",
            "uploads/q-vercel-python.json"
        ]
        
        students = []
        for file_path in default_file_paths:
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read().strip()
                        if content:
                            students = json.loads(content)
                            break
            except:
                continue
        
        if not students:
            # Return sample data if no file found
            students = [
                {"name": "John", "marks": 85},
                {"name": "Jane", "marks": 92},
                {"name": "Bob", "marks": 78}
            ]
        
        student_dict = {student["name"]: student["marks"] for student in students}
        
        if not name:
            return {"students": students}
        
        marks = [student_dict.get(name_item, 0) for name_item in name]
        return {"marks": marks}
        
    except Exception as e:
        return {"error": f"Failed to load student data: {str(e)}"}

@app.get("/api/student-data")
async def get_student_data(class_filter: Optional[List[str]] = Query(None, alias="class")):
    """
    Get student data from CSV file with class filtering
    Replaces the separate server from ga2_ninth_solution
    """
    try:
        import pandas as pd
        
        # Try multiple file paths
        default_file_paths = [
            "E://data science tool//GA2//q-fastapi.csv",
            "q-fastapi.csv",
            "student_data.csv",
            "uploads/q-fastapi.csv"
        ]
        
        df = None
        for file_path in default_file_paths:
            try:
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    break
            except:
                continue
        
        if df is None:
            # Return sample data if no file found
            students = [
                {"name": "John", "class": "1A", "marks": 85},
                {"name": "Jane", "class": "1B", "marks": 92},
                {"name": "Bob", "class": "1A", "marks": 78}
            ]
        else:
            students = df.to_dict('records')
        
        if not class_filter:
            return {"students": students}
        
        # Filter by class
        filtered_students = [
            student for student in students 
            if student.get("class") in class_filter
        ]
        
        return {"students": filtered_students}
        
    except Exception as e:
        return {"error": f"Failed to load CSV data: {str(e)}"}

@app.get("/api/execute")
async def execute_function(q: str = Query(..., description="Natural language query")):
    """
    Function identification from natural language queries
    Replaces the separate server from ga3_eighth_solution
    """
    try:
        function_templates = [
            {
                "name": "get_ticket_status",
                "pattern": r"(?i)what is the status of ticket (\d+)\??",
                "parameters": ["ticket_id"],
                "parameter_types": [int]
            },
            {
                "name": "create_user", 
                "pattern": r"(?i)create a new user with username \"([^\"]+)\" and email \"([^\"]+)\"\??",
                "parameters": ["username", "email"],
                "parameter_types": [str, str]
            },
            {
                "name": "schedule_meeting",
                "pattern": r"(?i)schedule a meeting on ([\w\s,]+) at (\d{1,2}:\d{2} [APap][Mm]) with ([^?]+)\??",
                "parameters": ["date", "time", "attendees"], 
                "parameter_types": [str, str, str]
            }
        ]
        
        # Try to match the query against function templates
        for template in function_templates:
            pattern = template["pattern"]
            match = re.search(pattern, q)
            
            if match:
                # Extract parameters
                parameters = {}
                for i, param_name in enumerate(template["parameters"]):
                    param_value = match.group(i + 1)
                    param_type = template["parameter_types"][i]
                    
                    # Convert to appropriate type
                    if param_type == int:
                        param_value = int(param_value)
                    elif param_type == float:
                        param_value = float(param_value)
                    # str remains as is
                    
                    parameters[param_name] = param_value
                
                return {
                    "function": template["name"],
                    "parameters": parameters
                }
        
        # No match found
        return {
            "function": None,
            "parameters": None,
            "error": "No matching function found for the given query"
        }
        
    except Exception as e:
        return {"error": f"Error processing query: {str(e)}"}

@app.get("/api/outline")
async def wikipedia_outline(country: Optional[str] = Query(None, description="Country name for Wikipedia outline")):
    """
    Generate a Markdown outline from Wikipedia country page headings
    Replaces the separate server from ga4_third_solution
    """
    try:
        if not country:
            return {
                "error": "Country parameter is required",
                "example": "/api/outline?country=France"
            }
        
        import requests
        from bs4 import BeautifulSoup
        
        # Construct Wikipedia URL
        country_formatted = country.replace(' ', '_')
        url = f"https://en.wikipedia.org/wiki/{country_formatted}"
        
        # Fetch Wikipedia page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            return {
                "error": f"Wikipedia page not found for '{country}'",
                "suggestion": "Please check the country name spelling"
            }
        
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the main content area
        content = soup.find('div', {'class': 'mw-parser-output'})
        if not content:
            return {"error": "Could not find main content on Wikipedia page"}
        
        # Extract headings (h1, h2, h3, h4, h5, h6)
        headings = content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        # Generate Markdown outline
        outline_lines = [f"# {country} - Wikipedia Outline\n"]
        
        for heading in headings:
            # Get heading level
            level = int(heading.name[1])
            
            # Get heading text and clean it
            text = heading.get_text().strip()
            
            # Skip empty headings or edit links
            if not text or '[edit]' in text:
                continue
            
            # Remove [edit] text if present
            text = re.sub(r'\[edit\]', '', text).strip()
            
            # Skip if still empty
            if not text:
                continue
            
            # Generate markdown heading with appropriate level
            markdown_prefix = '#' * (level + 1)  # Add 1 since we start with h1 for the title
            outline_lines.append(f"{markdown_prefix} {text}")
        
        # Join all lines
        outline = '\n'.join(outline_lines)
        
        return {
            "country": country,
            "wikipedia_url": url,
            "outline": outline,
            "heading_count": len(outline_lines) - 1  # Subtract 1 for title
        }
        
    except requests.exceptions.Timeout:
        return {"error": "Wikipedia request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching Wikipedia page: {str(e)}"}
    except Exception as e:
        return {"error": f"Error generating outline: {str(e)}"}

@app.get("/api/info")
async def comprehensive_api_info():
    """
    Information about all integrated API endpoints
    """
    return {
        "message": "Vicky App Integrated APIs - All running on port 8000",
        "endpoints": {
            "/api/similarity": "POST - Semantic document search using embeddings",
            "/api/student-marks": "GET - Student marks data with name filtering",
            "/api/student-data": "GET - Student CSV data with class filtering", 
            "/api/execute": "GET - Function identification from natural language",
            "/api/outline": "GET - Wikipedia country outline generator",
            "/api/info": "GET - This endpoint - comprehensive API information"
        },
        "examples": {
            "similarity": {
                "method": "POST",
                "url": "/api/similarity",
                "body": {
                    "docs": ["Document 1", "Document 2", "Document 3"],
                    "query": "search term"
                }
            },
            "student_marks": "/api/student-marks?name=John&name=Jane",
            "student_data": "/api/student-data?class=1A&class=1B",
            "execute": "/api/execute?q=What is the status of ticket 12345?",
            "outline": "/api/outline?country=France"
        },
        "integration_note": "All APIs integrated into main FastAPI app - no separate ports needed!",
        "azure_compatible": True,
        "main_port": 8000,
        "documentation": "/docs",
        "features": [
            "✅ Single port (8000) - no conflicts",
            "✅ Azure App Service compatible",
            "✅ Automatic API documentation",
            "✅ CORS enabled for cross-origin requests",
            "✅ Error handling and validation",
            "✅ JSON responses with consistent format"
        ]
    }

def start():
    """Function to start the server with proper error handling"""
    try:
        import os
        port = int(os.environ.get("PORT", 8000))
        print("\n" + "=" * 50)
        print("Starting TDS - Tools for Data Science Server")
        print("=" * 50)
        print(f"* Access the web interface at: http://0.0.0.0:{port}")
        print(f"* Access the web interface at: http://localhost:{port}")
        print("* Press Ctrl+C to stop the server\n")
        
        # Use os.system to run uvicorn with workers
        os.system(f"uvicorn vicky_app:app --host 0.0.0.0 --port {port} --workers 4")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\nError starting the server: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure port 8000 is not already in use")
        print("2. Check that you have permissions to create files/directories")
        print("3. Ensure vicky_server.py is in the same directory")
        sys.exit(1)

if __name__ == "__main__":
    start()