"""
Main relationship plugin class
Coordinates all relationship system components
"""

from config.settings import (
    SESSION_TRACKING_ENABLED,
    PERSONALITY_ANALYSIS_ENABLED,
    MEMORY_SYSTEM_ENABLED,
    ENHANCED_RESPONSES_ENABLED
)

class RelationshipPlugin:
    """Main relationship system plugin"""
    
    def __init__(self):
        self.session_tracker = None
        self.memory_system = None
        self.personality_analyzer = None
        self.conversation_ai = None
        
        # Initialize enabled components
        if SESSION_TRACKING_ENABLED:
            from .session_tracker import SessionTracker
            self.session_tracker = SessionTracker()
            print("DEBUG: Session tracking enabled")
        
        if MEMORY_SYSTEM_ENABLED:
            from .memory_system import MemorySystem
            self.memory_system = MemorySystem()
            print("DEBUG: Memory system enabled")
        
        if PERSONALITY_ANALYSIS_ENABLED:
            from .personality_analyzer import PersonalityAnalyzer
            self.personality_analyzer = PersonalityAnalyzer()
            print("DEBUG: Personality analysis enabled")
        
        if ENHANCED_RESPONSES_ENABLED:
            from .conversation_ai import ConversationAI
            self.conversation_ai = ConversationAI(self.memory_system)
            print("DEBUG: Enhanced responses enabled")
    
    def on_action(self, action, target, result):
        """Handle player action"""
        if self.session_tracker:
            self.session_tracker.track_action(action, target, result)
        
        if self.personality_analyzer:
            self.personality_analyzer.analyze_action(action, target, result)
    
    def enhance_response(self, response, context):
        """Enhance Patch response with relationship data"""
        if self.conversation_ai:
            return self.conversation_ai.enhance_response(response, context)
        return response
    
    def on_session_start(self, player_name):
        """Handle session start"""
        if self.session_tracker:
            self.session_tracker.start_session(player_name)
        
        if self.memory_system:
            self.memory_system.load_player_memory(player_name)
    
    def on_session_end(self, player_name):
        """Handle session end"""
        if self.session_tracker:
            self.session_tracker.end_session(player_name)
        
        if self.memory_system:
            self.memory_system.save_player_memory(player_name)
