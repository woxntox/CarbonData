"""
Memory system component
Handles cross-session memory persistence
"""

import json
import os
from config.settings import PROFILE_DATA_DIR

class MemorySystem:
    """Manages player memory and personality data"""
    
    def __init__(self):
        self.player_memories = {}
        
        # Ensure data directory exists
        os.makedirs(PROFILE_DATA_DIR, exist_ok=True)
    
    def load_player_memory(self, player_name):
        """Load player memory from file"""
        memory_file = os.path.join(PROFILE_DATA_DIR, f"{player_name}.json")
        
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r') as f:
                    self.player_memories[player_name] = json.load(f)
                print(f"DEBUG: Loaded memory for {player_name}")
            except Exception as e:
                print(f"DEBUG: Error loading memory for {player_name}: {e}")
                self.player_memories[player_name] = {}
        else:
            self.player_memories[player_name] = {
                'facts': {},
                'preferences': {},
                'interaction_style': 'unknown',
                'total_sessions': 0,
                'last_seen': None
            }
    
    def save_player_memory(self, player_name):
        """Save player memory to file"""
        if player_name not in self.player_memories:
            return
        
        memory_file = os.path.join(PROFILE_DATA_DIR, f"{player_name}.json")
        
        try:
            with open(memory_file, 'w') as f:
                json.dump(self.player_memories[player_name], f, indent=2)
            print(f"DEBUG: Saved memory for {player_name}")
        except Exception as e:
            print(f"DEBUG: Error saving memory for {player_name}: {e}")
    
    def remember_fact(self, player_name, fact_type, fact_value):
        """Remember a fact about the player"""
        if player_name not in self.player_memories:
            self.load_player_memory(player_name)
        
        self.player_memories[player_name]['facts'][fact_type] = fact_value
        print(f"DEBUG: Remembered {fact_type}: {fact_value} for {player_name}")
    
    def get_fact(self, player_name, fact_type):
        """Get a remembered fact about the player"""
        if player_name not in self.player_memories:
            return None
        
        return self.player_memories[player_name]['facts'].get(fact_type)
    
    def get_player_memory(self, player_name):
        """Get full player memory"""
        if player_name not in self.player_memories:
            self.load_player_memory(player_name)
        
        return self.player_memories.get(player_name, {})
