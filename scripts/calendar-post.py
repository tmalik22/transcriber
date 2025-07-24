#!/usr/bin/env python3

"""
calendar-post.py - Calendar integration for action items and follow-ups
Integrates with Microsoft Graph API to create calendar events
"""

import sys
import json
import time
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Optional imports with fallbacks
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

# Add project root to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

def load_config():
    """Load configuration from settings.json"""
    config_path = PROJECT_DIR / "config" / "settings.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def log(message, session_id=None):
    """Log message with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    if session_id:
        log_file = PROJECT_DIR / "logs" / f"{session_id}.log"
    else:
        log_file = PROJECT_DIR / "logs" / "calendar.log"
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def parse_action_items(summary_content):
    """Parse action items from AI summary"""
    action_items = []
    
    # Look for action items section
    lines = summary_content.split('\n')
    in_action_section = False
    current_item = {}
    
    for line in lines:
        line = line.strip()
        
        # Check if we're entering action items section
        if '🔨 Action Items' in line or 'Action Items' in line:
            in_action_section = True
            continue
        
        # Check if we're leaving action items section
        if in_action_section and line.startswith('#') and 'Action' not in line:
            break
        
        if in_action_section and line:
            # Parse action item format
            if line.startswith('- **Task**:'):
                if current_item:
                    action_items.append(current_item)
                current_item = {
                    'task': line.replace('- **Task**:', '').strip(),
                    'owner': 'TBD',
                    'due_date': 'TBD',
                    'priority': 'Medium'
                }
            elif '**Owner**:' in line:
                current_item['owner'] = line.split('**Owner**:')[1].strip()
            elif '**Due Date**:' in line:
                current_item['due_date'] = line.split('**Due Date**:')[1].strip()
            elif '**Priority**:' in line:
                current_item['priority'] = line.split('**Priority**:')[1].strip()
    
    # Add final item
    if current_item:
        action_items.append(current_item)
    
    return action_items

def parse_calendar_suggestions(summary_content):
    """Parse calendar suggestions from AI summary"""
    calendar_items = []
    
    lines = summary_content.split('\n')
    in_calendar_section = False
    current_item = {}
    
    for line in lines:
        line = line.strip()
        
        if '📅 Calendar Suggestions' in line:
            in_calendar_section = True
            continue
        
        if in_calendar_section and line.startswith('#') and 'Calendar' not in line:
            break
        
        if in_calendar_section and line:
            if line.startswith('- **Title**:'):
                if current_item:
                    calendar_items.append(current_item)
                current_item = {
                    'title': line.replace('- **Title**:', '').strip(),
                    'duration': '30 minutes',
                    'attendees': [],
                    'notes': ''
                }
            elif '**Duration**:' in line:
                current_item['duration'] = line.split('**Duration**:')[1].strip()
            elif '**Attendees**:' in line:
                attendees_str = line.split('**Attendees**:')[1].strip()
                current_item['attendees'] = [a.strip() for a in attendees_str.split(',') if a.strip()]
            elif '**Notes**:' in line:
                current_item['notes'] = line.split('**Notes**:')[1].strip()
    
    if current_item:
        calendar_items.append(current_item)
    
    return calendar_items

def parse_duration(duration_str):
    """Parse duration string to minutes"""
    duration_str = duration_str.lower()
    
    # Extract numbers
    numbers = re.findall(r'\d+', duration_str)
    if not numbers:
        return 30  # Default 30 minutes
    
    minutes = int(numbers[0])
    
    if 'hour' in duration_str:
        minutes *= 60
    elif 'day' in duration_str:
        minutes *= 60 * 8  # 8-hour work day
    
    return max(15, min(minutes, 480))  # Between 15 minutes and 8 hours

def parse_due_date(due_date_str):
    """Parse due date string to datetime"""
    if due_date_str.lower() in ['tbd', 'to be determined', '']:
        # Default to next week
        return datetime.now() + timedelta(days=7)
    
    due_date_str = due_date_str.lower()
    now = datetime.now()
    
    if 'today' in due_date_str:
        return now
    elif 'tomorrow' in due_date_str:
        return now + timedelta(days=1)
    elif 'next week' in due_date_str:
        return now + timedelta(days=7)
    elif 'end of week' in due_date_str:
        days_until_friday = (4 - now.weekday()) % 7
        return now + timedelta(days=days_until_friday)
    else:
        # Try to parse relative dates
        numbers = re.findall(r'\d+', due_date_str)
        if numbers:
            days = int(numbers[0])
            if 'day' in due_date_str:
                return now + timedelta(days=days)
            elif 'week' in due_date_str:
                return now + timedelta(days=days*7)
    
    # Default fallback
    return now + timedelta(days=7)

def create_calendar_event_local(item, session_id):
    """Create local calendar reminder (fallback)"""
    try:
        # Create AppleScript to add calendar event
        title = item.get('title', 'Meeting Follow-up')
        notes = item.get('notes', f"Generated from meeting session: {session_id}")
        duration_minutes = parse_duration(item.get('duration', '30 minutes'))
        
        # Schedule for next business day at 10 AM
        start_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        if start_date.weekday() >= 5:  # Weekend
            days_to_monday = 7 - start_date.weekday()
            start_date = start_date + timedelta(days=days_to_monday)
        elif start_date < datetime.now():
            start_date = start_date + timedelta(days=1)
        
        end_date = start_date + timedelta(minutes=duration_minutes)
        
        # Format dates for AppleScript
        start_str = start_date.strftime('%m/%d/%Y %H:%M:%S')
        end_str = end_date.strftime('%m/%d/%Y %H:%M:%S')
        
        applescript = f'''
        tell application "Calendar"
            tell calendar "Home"
                make new event with properties {{summary:"{title}", start date:date "{start_str}", end date:date "{end_str}", description:"{notes}"}}
            end tell
        end tell
        '''
        
        subprocess.run(['osascript', '-e', applescript], check=True)
        log(f"Created local calendar event: {title}", session_id)
        return True
        
    except Exception as e:
        log(f"Failed to create local calendar event: {e}", session_id)
        return False

def get_microsoft_graph_token(config):
    """Get Microsoft Graph API access token"""
    if not HAS_REQUESTS:
        log("Warning: requests library not available for Microsoft Graph integration")
        return None
    
    # This is a placeholder - you'd need to implement OAuth flow
    # For now, return None to use fallback method
    return None

def create_microsoft_graph_event(item, token, session_id):
    """Create event using Microsoft Graph API"""
    if not HAS_REQUESTS:
        log("Microsoft Graph API requires requests library", session_id)
        return False
    
    # Placeholder for Microsoft Graph integration
    # This would require proper OAuth setup
    log("Microsoft Graph API not configured, using local calendar", session_id)
    return False

def process_calendar_integration(session_id):
    """Main calendar integration function"""
    config = load_config()
    calendar_config = config.get('calendar', {})
    
    if not calendar_config.get('enabled', False):
        log("Calendar integration disabled", session_id)
        return
    
    log(f"Processing calendar integration for session: {session_id}", session_id)
    
    # Find summary file
    summary_file = PROJECT_DIR / "transcripts" / f"{session_id}_summary.md"
    if not summary_file.exists():
        log("No summary file found for calendar integration", session_id)
        return
    
    # Read summary
    with open(summary_file, 'r') as f:
        summary_content = f.read()
    
    # Parse action items and calendar suggestions
    action_items = parse_action_items(summary_content)
    calendar_suggestions = parse_calendar_suggestions(summary_content)
    
    log(f"Found {len(action_items)} action items and {len(calendar_suggestions)} calendar suggestions", session_id)
    
    # Try Microsoft Graph API first
    token = get_microsoft_graph_token(calendar_config)
    created_events = []
    
    # Process calendar suggestions
    for item in calendar_suggestions:
        success = False
        
        if token:
            success = create_microsoft_graph_event(item, token, session_id)
        
        if not success:
            success = create_calendar_event_local(item, session_id)
        
        if success:
            created_events.append(item['title'])
    
    # Process action items as calendar reminders
    for item in action_items:
        due_date = parse_due_date(item['due_date'])
        
        calendar_item = {
            'title': f"Action Item: {item['task'][:50]}...",
            'duration': '30 minutes',
            'notes': f"Owner: {item['owner']}\nPriority: {item['priority']}\nTask: {item['task']}"
        }
        
        success = create_calendar_event_local(calendar_item, session_id)
        if success:
            created_events.append(calendar_item['title'])
    
    if created_events:
        log(f"Created {len(created_events)} calendar events", session_id)
    else:
        log("No calendar events created", session_id)

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python calendar-post.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    
    try:
        process_calendar_integration(session_id)
        print("Calendar integration completed")
    except Exception as e:
        log(f"Calendar integration error: {e}", session_id)
        print(f"Error: {e}")
        # Don't exit with error - calendar integration is optional

if __name__ == "__main__":
    import subprocess
    main()
