"""
Plugin management system for VantablackGame
Handles loading and managing optional relationship system plugins
"""

import os
import sys
from config.settings import RELATIONSHIP_SYSTEM_ENABLED

class PluginManager:
    """Manages plugin loading and execution"""
    
    def __init__(self):
        self.plugins = {}
        self.session_trackers = {}  # session_id -> SessionTracker
        self.load_plugins()
    
    def load_plugins(self):
        """Load enabled plugins"""
        if RELATIONSHIP_SYSTEM_ENABLED:
            try:
                from plugins.relationship import RelationshipPlugin
                self.plugins['relationship'] = RelationshipPlugin()
                print("DEBUG: Relationship plugin loaded successfully")
            except ImportError as e:
                print(f"DEBUG: Relationship plugin not available: {e}")
            except Exception as e:
                print(f"DEBUG: Error loading relationship plugin: {e}")
        else:
            print("DEBUG: Relationship system disabled")
    
    def get_plugin(self, name):
        """Get a specific plugin by name"""
        return self.plugins.get(name)
    
    def has_plugin(self, name):
        """Check if a plugin is loaded"""
        return name in self.plugins
    
    def on_action(self, action, target, result, session_id=None):
        """Call plugin hooks for action processing"""
        if self.has_plugin('relationship'):
            try:
                # Get or create session tracker for this session
                if session_id and session_id not in self.session_trackers:
                    from plugins.relationship.session_tracker import SessionTracker
                    self.session_trackers[session_id] = SessionTracker()
                
                # Track action if we have a session tracker
                if session_id and session_id in self.session_trackers:
                    self.session_trackers[session_id].track_action(action, target, result)
                
                self.plugins['relationship'].on_action(action, target, result)
            except Exception as e:
                print(f"DEBUG: Plugin error in on_action: {e}")
    
    def enhance_response(self, response, context):
        """Call plugin hooks for response enhancement"""
        if self.has_plugin('relationship'):
            try:
                return self.plugins['relationship'].enhance_response(response, context)
            except Exception as e:
                print(f"DEBUG: Plugin error in enhance_response: {e}")
                return response
        return response
    
    def on_session_start(self, player_name, session_id=None):
        """Call plugin hooks for session start"""
        if self.has_plugin('relationship'):
            try:
                # Start session tracking for this specific session
                if session_id:
                    if session_id not in self.session_trackers:
                        from plugins.relationship.session_tracker import SessionTracker
                        self.session_trackers[session_id] = SessionTracker()
                    self.session_trackers[session_id].start_session(player_name)
                
                self.plugins['relationship'].on_session_start(player_name)
            except Exception as e:
                print(f"DEBUG: Plugin error in on_session_start: {e}")
    
    def on_session_end(self, player_name, session_id=None):
        """Call plugin hooks for session end"""
        if self.has_plugin('relationship'):
            try:
                # End session tracking for this specific session
                if session_id and session_id in self.session_trackers:
                    self.session_trackers[session_id].end_session(player_name)
                    # Clean up the session tracker
                    del self.session_trackers[session_id]
                
                self.plugins['relationship'].on_session_end(player_name)
            except Exception as e:
                print(f"DEBUG: Plugin error in on_session_end: {e}")
