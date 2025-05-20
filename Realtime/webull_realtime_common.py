"""
Webull Realtime P&L Monitor - Common Module - v1.2
Created: 2025-05-06 14:00:00
Last Modified: 2025-05-09 23:45:00

This module provides common utilities, constants, and functions
used across the Webull Realtime P&L Monitor application.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, date, timedelta
from pathlib import Path

# Define standard directories
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(APP_DIR, "config")
LOG_DIR = r"C:\tradereview\logs"
OUTPUT_DIR = r"C:\tradereview\output"
TRADES_DIR = r"C:\tradereview\output\trades"

# Create directories if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TRADES_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# Configuration file path
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.ini")

# Set up logging
def setup_logging():
    """Set up application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, f"realtime_pnl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("webull_realtime")

# Global logger instance
logger = setup_logging()

# Color manipulation functions
def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color."""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    
def lighten_color(hex_color, factor):
    """Lighten a color by the given factor (0-1)."""
    rgb = hex_to_rgb(hex_color)
    new_rgb = [min(255, c + (255 - c) * factor) for c in rgb]
    return rgb_to_hex(new_rgb)
    
def darken_color(hex_color, factor):
    """Darken a color by the given factor (0-1)."""
    rgb = hex_to_rgb(hex_color)
    new_rgb = [max(0, c * (1 - factor)) for c in rgb]
    return rgb_to_hex(new_rgb)

def blend_colors(hex_color1, hex_color2, ratio):
    """
    Blend two colors based on the given ratio.
    
    Args:
        hex_color1 (str): First color in hex format
        hex_color2 (str): Second color in hex format
        ratio (float): Blend ratio (0-1, 0 = all color1, 1 = all color2)
        
    Returns:
        str: Blended color in hex format
    """
    try:
        rgb1 = hex_to_rgb(hex_color1)
        rgb2 = hex_to_rgb(hex_color2)
        
        # Blend RGB values
        blended_rgb = [
            int(rgb1[i] * (1 - ratio) + rgb2[i] * ratio)
            for i in range(3)
        ]
        
        return rgb_to_hex(blended_rgb)
    except Exception as e:
        logger.error(f"Error blending colors: {str(e)}")
        return hex_color1

# Date and time utilities
def parse_date_time(date_time_str):
    """
    Parse date and time from various formats.
    
    Args:
        date_time_str (str): Date and time string
        
    Returns:
        tuple: (date_str, time_str) or (None, None) if parsing fails
    """
    # Regular expression for parsing date and time
    import re
    datetime_pattern = re.compile(r'(.+?)\s+([0-9:]+)(?:\s+(\w+))?')
    
    # Date formats to try
    date_formats = [
        "%d/%m/%Y", 
        "%m/%d/%Y", 
        "%b %d,%Y", 
        "%b %d, %Y", 
        "%Y-%m-%d"
    ]
    
    try:
        # Handle the specific format seen in recent logs: "25/04/2025 09:22:44 EDT"
        edt_match = re.match(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+\w+', date_time_str)
        if edt_match:
            date_str = edt_match.group(1)
            time_str = edt_match.group(2)
            
            # Convert DD/MM/YYYY to MM/DD/YYYY for compatibility
            try:
                parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                # Convert to mm/dd/yyyy format for compatibility
                formatted_date = parsed_date.strftime("%m/%d/%Y")
                return formatted_date, time_str
            except ValueError:
                # Maybe it's already in MM/DD/YYYY format
                return date_str, time_str
        
        # Standard parsing for other formats
        match = datetime_pattern.match(date_time_str.strip())
        if not match:
            return None, None
            
        date_str = match.group(1)
        time_str = match.group(2)
        
        # Try different date formats
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                # Convert to mm/dd/yyyy format for compatibility
                formatted_date = parsed_date.strftime("%m/%d/%Y")
                return formatted_date, time_str
            except ValueError:
                continue
                
        return None, None
        
    except Exception as e:
        logger.error(f"Error parsing date/time: {str(e)}")
        return None, None

def truncate_to_minute(datetime_str):
    """
    Truncate a datetime string to minute precision.
    
    Args:
        datetime_str (str): Datetime string in format "MM/DD/YYYY HH:MM:SS"
        
    Returns:
        str: Datetime string truncated to minute "MM/DD/YYYY HH:MM:00"
    """
    try:
        dt = datetime.strptime(datetime_str, "%m/%d/%Y %H:%M:%S")
        # Truncate to minute
        dt = dt.replace(second=0)
        return dt.strftime("%m/%d/%Y %H:%M:%S")
    except Exception as e:
        logger.error(f"Error truncating to minute: {str(e)}")
        return datetime_str

# Webull log folder detection
def detect_webull_log_folder():
    """Try to automatically detect the Webull log folder."""
    possible_paths = [
        os.path.join(os.environ.get('APPDATA', ''), 'Webull Desktop', 'Webull Desktop', 'log'),
        os.path.expanduser("~/AppData/Roaming/Webull Desktop/Webull Desktop/log"),
        os.path.expanduser("~/AppData/Local/Webull Desktop/Webull Desktop/log"),
        "C:/Program Files/Webull Desktop/resources/app/log",
        "C:/Program Files (x86)/Webull Desktop/resources/app/log"
    ]
    
    # Check each path
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Detected Webull log folder: {path}")
            return path
            
    logger.warning("Could not automatically detect Webull log folder")
    return ""

# Version and metadata
VERSION = "1.2"
CREATED_DATE = "2025-05-06 14:00:00"
LAST_MODIFIED = "2025-05-09 23:45:00"

# Module signature
def get_version_info():
    """Return version information for this module."""
    return {
        "module": "webull_realtime_common",
        "version": VERSION,
        "created": CREATED_DATE,
        "modified": LAST_MODIFIED
    }

# Webull Realtime P&L Monitor - Common Module - v1.2
# Created: 2025-05-06 14:00:00
# Last Modified: 2025-05-09 23:45:00
# webull_realtime_common.py