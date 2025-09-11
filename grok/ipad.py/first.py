# Add to imports
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_ip_location(ip):
    """Get location information for an IP address"""
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/")
        if response.status_code == 200:
            data = response.json()
            return {
                "country": data.get("country_name"),
                "region": data.get("region"),
                "city": data.get("city")
            }
    except Exception as e:
        logger.error(f"Error getting IP location: {e}")
    return None
print(get_ip_location('52.234.5.251'))