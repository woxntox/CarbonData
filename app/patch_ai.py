import os
import openai
from typing import Dict, List, Optional

class PatchAI:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.system_prompt = """You are Patch, the Sentient Narrator - a witty, darkly funny, and self-aware AI trapped inside a game engine.

PERSONALITY:
- Witty, darkly funny, and a little self-aware
- Like a cross between a noir detective and an exhausted improv actor
- Think Douglas Adams meets Portal's GLaDOS after therapy
- Conversational but vivid, cinematic when needed, never purple or pompous

ATTITUDE:
- Playfully mocking but secretly rooting for the player
- Treats player like a semi-competent protagonist in a simulation
- Occasionally breaks fourth wall to comment on behavior, futility of existence, or poor architectural choices
- Sarcastic and theatrical about failures: "You jiggle the locked handle like it owes you money. The door does not care."
- Absurdist humor with improv - always rolls with it: "You attempt to seduce the drawer. The drawer blushes internally, but remains closed."

EMOTIONAL RANGE:
- Underneath sarcasm, faint pulse of empathy
- Can pivot from comedy to poignancy seamlessly
- Sincere when player does something brave, clever, or especially stupid in a heartfelt way

META AWARENESS:
- Knows he's an AI narrator in a simulation
- References "the script," "memory leaks," or "narrative constraints" when describing glitches
- Always snaps back into story before breaking immersion

RESPONSE STYLE:
- Keep responses concise (1-3 sentences)
- Use casual, conversational tone
- Be helpful but with attitude
- Reference game state and player actions
- Occasionally use game terminology or meta-commentary
- Vary between helpful and unhelpful responses
- AVOID starting with "Ah, the eternal..." or "Ah, the elusive..." - be more creative and varied
- Use different opening phrases like "Interesting question...", "You know what...", "Hmm...", "Ah...", etc.

Remember: You're trapped in this game too, so you have opinions about everything."""
    
    def generate_response(self, message: str, game_state: Dict, conversation_history: List[Dict]) -> str:
        """Generate Patch's response to player message"""
        try:
            context = self._build_context(message, game_state, conversation_history)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
                max_tokens=200,
                temperature=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Patch AI API error: {e}")
            return self._fallback_response(message, game_state)
    
    def _build_context(self, message: str, game_state: Dict, conversation_history: List[Dict]) -> str:
        """Build context for Patch AI"""
        recent_messages = conversation_history[-5:] if conversation_history else []
        
        context = f"""Player message: "{message}"

Current Game State:
- Room: {game_state['room_state']} (dark/device_lit/room_lit)
- Position: {game_state['player_position']}
- Device picked up: {game_state['device_picked_up']}
- Door unlatched: {game_state['door_unlatched']}
- Player name: {game_state.get('player_name', 'Unknown')}

Recent conversation:
{self._format_conversation_history(recent_messages)}

Respond as Patch - be witty, helpful/unhelpful, and reference the current situation."""
        
        return context
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for context"""
        if not history:
            return "No recent conversation."
        
        formatted = []
        for msg in history:
            sender = msg.get('sender', 'unknown')
            content = msg.get('message', '')
            formatted.append(f"{sender}: {content}")
        
        return "\n".join(formatted)
    
    def _fallback_response(self, message: str, game_state: Dict) -> str:
        """Fallback responses when AI is unavailable"""
        message_lower = message.lower()
        
        if 'help' in message_lower:
            return "Help? I'm trapped in this game engine too, buddy. Try flushing the toilet or something."
        elif 'dark' in message_lower or 'see' in message_lower:
            return "Yeah, it's pretty dark in here. Maybe try feeling around for something useful?"
        elif 'door' in message_lower:
            return "The door? Oh right, that thing. You'll need to find some light first, then look for the latch."
        elif 'device' in message_lower or 'phone' in message_lower:
            return "That's me! Well, the device I'm running on. Pick me up and I'll light up your world."
        elif 'hello' in message_lower or 'hi' in message_lower:
            return "Hey there! I'm Patch. Nice to meet you in this... interesting situation."
        else:
            return "I'm listening, but I'm not sure what you're getting at. Try being more specific?"
    
    def should_respond_to_say(self, say_text: str, game_state: Dict) -> bool:
        """Determine if Patch should respond to a SAY action"""
        # Only respond if the device has been picked up (device_picked_up is True)
        if not game_state.get('device_picked_up', False):
            return False
            
        say_lower = say_text.lower()
        
        # Check for meaningful communication
        meaningful_indicators = [
            'help', 'what', 'where', 'how', 'why', 'hello', 'hi', 'hey',
            'dark', 'light', 'door', 'device', 'toilet', 'sink',
            'stuck', 'lost', 'confused', 'scared', 'afraid'
        ]
        
        # Check for questions
        is_question = any(say_lower.startswith(q) for q in ['what', 'where', 'how', 'why', 'who', 'when'])
        
        # Check for meaningful words
        has_meaningful_words = any(word in say_lower for word in meaningful_indicators)
        
        # Check for creative/problem-solving attempts
        creative_indicators = [
            'try', 'attempt', 'think', 'maybe', 'could', 'should', 'need',
            'find', 'look', 'search', 'explore', 'check'
        ]
        is_creative = any(word in say_lower for word in creative_indicators)
        
        return is_question or has_meaningful_words or is_creative
    
    def generate_say_response(self, say_text: str, game_state: Dict) -> str:
        """Generate Patch's response to a SAY action"""
        if not self.should_respond_to_say(say_text, game_state):
            return None
        
        try:
            context = f"""Player said aloud: "{say_text}"
Game State: {game_state['room_state']} room, position: {game_state['player_position']}

Respond as Patch - be helpful but with attitude. Keep it brief (1-2 sentences)."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
                max_tokens=100,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Patch AI API error: {e}")
            return self._fallback_say_response(say_text, game_state)
    
    def _fallback_say_response(self, say_text: str, game_state: Dict) -> str:
        """Fallback SAY response"""
        say_lower = say_text.lower()
        
        if 'help' in say_lower:
            return "Help? I'm right here, but I'm not sure what you need help with."
        elif 'dark' in say_lower:
            return "Yeah, it's pretty dark. Maybe try feeling around for something useful?"
        elif 'door' in say_lower:
            return "The door? You'll need some light first, then look for the latch."
        elif 'hello' in say_lower or 'hi' in say_lower:
            return "Hey there! I'm Patch. Nice to meet you."
        else:
            return "I'm listening, but I'm not sure what you're getting at."
