"""
Session tracking component
Tracks player actions and behavior patterns
"""

import json
import time
import os
from config.settings import SESSION_DATA_DIR, MAX_ACTIONS_PER_SESSION

class SessionTracker:
    """Tracks player session data"""
    
    def __init__(self):
        self.session_data = {}
        self.current_player = None
        
        # Ensure data directory exists
        os.makedirs(SESSION_DATA_DIR, exist_ok=True)
    
    def start_session(self, player_name):
        """Start tracking a new session"""
        self.current_player = player_name
        self.session_data = {
            'player_name': player_name,
            'session_start': time.time(),
            'actions': [],
            'total_actions': 0,
            'session_id': f"{player_name}_{int(time.time())}"
        }
        print(f"DEBUG: Started session tracking for {player_name}")
    
    def track_action(self, action, target, result):
        """Track a player action"""
        if not self.current_player:
            return
        
        # Prevent memory bloat
        if len(self.session_data.get('actions', [])) >= MAX_ACTIONS_PER_SESSION:
            return
        
        action_data = {
            'action': action,
            'target': target,
            'timestamp': time.time(),
            'success': result.get('success', False),
            'response_length': len(str(result.get('response', ''))),
            'patch_involved': 'patch' in str(result.get('response', '')).lower()
        }
        
        self.session_data['actions'].append(action_data)
        self.session_data['total_actions'] = len(self.session_data['actions'])
    
    def end_session(self, player_name):
        """End current session and save data"""
        if not self.current_player or self.current_player != player_name:
            return
        
        self.session_data['session_end'] = time.time()
        self.session_data['duration'] = self.session_data['session_end'] - self.session_data['session_start']
        
        # Save session data
        session_file = os.path.join(SESSION_DATA_DIR, f"{player_name}_{int(time.time())}.json")
        try:
            with open(session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
            print(f"DEBUG: Saved session data for {player_name}")
        except Exception as e:
            print(f"DEBUG: Error saving session data: {e}")
        
        # Reset for next session
        self.current_player = None
        self.session_data = {}
