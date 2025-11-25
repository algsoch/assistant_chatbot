"""
Webhook Notifications
Discord, Slack, and Telegram integrations
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import requests

from src.core.config import settings

logger = logging.getLogger(__name__)


class NotificationBuffer:
    """Buffer notifications to prevent spam"""
    
    def __init__(self):
        self.buffer: List[Dict[str, Any]] = []
        self.count: int = 0
        self.last_sent: float = time.time()
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
    
    def add(self, notification: Dict[str, Any]):
        """Add a notification to the buffer"""
        with self.lock:
            self.buffer.append(notification)
            self.count += 1
            
            # Check if we should send
            current_time = time.time()
            if current_time - self.last_sent >= settings.NOTIF_INTERVAL_SECONDS:
                if self.thread is None or not self.thread.is_alive():
                    self.thread = threading.Thread(target=self._send_buffered)
                    self.thread.daemon = True
                    self.thread.start()
                    self.last_sent = current_time
    
    def _send_buffered(self):
        """Send buffered notifications"""
        with self.lock:
            notifications = self.buffer.copy()
            count = self.count
            self.buffer = []
            self.count = 0
        
        if not notifications:
            return
        
        # Create summary message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = f"**API Access Summary** ({timestamp})\n"
        summary += f"- Total requests: {count}\n"
        
        # Group by IP
        ip_counts = {}
        for notif in notifications:
            ip = notif.get("ip", "unknown")
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        summary += "- IP addresses:\n"
        for ip, cnt in ip_counts.items():
            summary += f"  - {ip}: {cnt} requests\n"
        
        # Recent queries
        summary += "- Recent queries:\n"
        for notif in notifications[-5:]:
            summary += f"  - {notif.get('question', 'N/A')[:50]}...\n"
        
        # Send to all configured channels
        send_to_discord(summary)
        send_to_slack(summary)
        send_to_telegram(summary)


# Global notification buffer
notification_buffer = NotificationBuffer()


def send_to_discord(message: str, embed: Optional[Dict] = None):
    """Send message to Discord webhook"""
    if not settings.DISCORD_WEBHOOK:
        return
    
    try:
        payload = {"content": message}
        if embed:
            payload["embeds"] = [embed]
        
        response = requests.post(
            settings.DISCORD_WEBHOOK,
            json=payload,
            timeout=5
        )
        if response.status_code == 204:
            logger.info("Discord notification sent")
        else:
            logger.warning(f"Discord webhook failed: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")


def send_to_slack(message: str):
    """Send message to Slack webhook"""
    if not settings.SLACK_WEBHOOK:
        return
    
    try:
        payload = {"text": message}
        response = requests.post(
            settings.SLACK_WEBHOOK,
            json=payload,
            timeout=5
        )
        logger.info("Slack notification sent")
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")


def send_to_telegram(message: str):
    """Send message to Telegram"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    
    try:
        api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(api_url, json=payload, timeout=5)
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")


def notify_api_access(ip: str, user_agent: str, question: str):
    """Queue a notification for API access"""
    notification = {
        "timestamp": datetime.now().isoformat(),
        "ip": ip,
        "user_agent": user_agent,
        "question": question[:100] + ("..." if len(question) > 100 else "")
    }
    notification_buffer.add(notification)


def send_visitor_notification(ip: str, user_agent: str = None):
    """Send immediate notification for new visitor"""
    if not settings.DISCORD_WEBHOOK:
        return
    
    embed = {
        "title": "🌐 New Website Visitor",
        "color": 0x4c2882,
        "fields": [
            {"name": "IP Address", "value": ip or "Unknown", "inline": True},
            {"name": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
            {"name": "User Agent", "value": (user_agent[:100] + "...") if user_agent and len(user_agent) > 100 else (user_agent or "Unknown"), "inline": False}
        ],
        "footer": {"text": "TDS Assistant"},
        "timestamp": datetime.now().isoformat()
    }
    
    send_to_discord("", embed)
