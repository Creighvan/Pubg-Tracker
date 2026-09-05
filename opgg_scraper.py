"""
OP.GG Scraper Module
Provides historical inactivity data beyond the 14-day PUBG API limitation.

Data Source: op.gg (with proper attribution as per their terms)
Rate Limiting: 2 requests per second to respect service operation
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import re

# Rate limiting to respect OP.GG service (2 requests per second)
OPGG_RATE_LIMIT = 2
LAST_REQUEST_TIME = 0

def _rate_limit():
    """Enforce rate limiting between requests"""
    global LAST_REQUEST_TIME
    elapsed = time.time() - LAST_REQUEST_TIME
    if elapsed < (1.0 / OPGG_RATE_LIMIT):
        time.sleep((1.0 / OPGG_RATE_LIMIT) - elapsed)
    LAST_REQUEST_TIME = time.time()

def get_opgg_last_active(player_name: str) -> Optional[Dict[str, Any]]:
    """
    Get last active date from OP.GG for a player.
    
    Args:
        player_name: PUBG player name
        
    Returns:
        Dict with 'days_inactive' and 'last_match_date' or None if not found
    """
    try:
        _rate_limit()
        
        # OP.GG player page URL
        url = f"https://op.gg/pubg/player/{player_name}"
        headers = {
            'User-Agent': 'PUBG-Tracker-Bot/1.0 (Data Source: op.gg)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return None  # Player not found on OP.GG
            
        if response.status_code != 200:
            print(f"OP.GG error for {player_name}: HTTP {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find last match date in various possible locations
        # OP.GG structure may change, so we try multiple approaches
        
        # Method 1: Look for recent match list with dates
        match_items = soup.find_all(class_=re.compile(r'match|recent|history', re.I))
        
        if not match_items:
            # Method 2: Look for any text containing "days ago" or similar
            page_text = soup.get_text()
            # Look for patterns like "16 days ago", "2 weeks ago", etc.
            days_match = re.search(r'(\d+)\s*days?\s*ago', page_text, re.I)
            if days_match:
                days = int(days_match.group(1))
                return {
                    'days_inactive': days,
                    'last_match_date': (datetime.now() - timedelta(days=days)).isoformat(),
                    'source': 'op.gg'
                }
            
            weeks_match = re.search(r'(\d+)\s*weeks?\s*ago', page_text, re.I)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                days = weeks * 7
                return {
                    'days_inactive': days,
                    'last_match_date': (datetime.now() - timedelta(days=days)).isoformat(),
                    'source': 'op.gg'
                }
        
        # Method 3: Try to parse specific OP.GG match cards
        # This is more fragile but more accurate if it works
        for item in match_items[:5]:  # Check first 5 match items
            item_text = item.get_text()
            # Look for date patterns
            date_match = re.search(r'(\d+)\s*days?\s*ago', item_text, re.I)
            if date_match:
                days = int(date_match.group(1))
                return {
                    'days_inactive': days,
                    'last_match_date': (datetime.now() - timedelta(days=days)).isoformat(),
                    'source': 'op.gg'
                }
        
        # If we couldn't find specific date data, player might be very inactive
        # or OP.GG structure changed
        return None
        
    except requests.RequestException as e:
        print(f"OP.GG request error for {player_name}: {e}")
        return None
    except Exception as e:
        print(f"OP.GG parsing error for {player_name}: {e}")
        return None

def get_opgg_last_active_batch(player_names: list) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Get last active dates for multiple players from OP.GG.
    
    Args:
        player_names: List of PUBG player names
        
    Returns:
        Dict mapping player names to their inactivity data
    """
    results = {}
    for player_name in player_names:
        results[player_name] = get_opgg_last_active(player_name)
        # Small additional delay between batch requests
        time.sleep(0.1)
    return results