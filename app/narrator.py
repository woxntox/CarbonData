import os
import openai
from typing import Dict, List, Optional

class Narrator:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.system_prompt = """You are a first-person narrator for a text adventure game. You describe the player's internal thoughts, sensations, and experiences in a DRY, MATTER-OF-FACT tone.

Your role:
- Describe ONLY the player's INTERNAL experience, emotions, and sensations
- Use first-person perspective ("I feel...", "My heart...", "A shiver...")
- Focus on emotional and physical sensations, not external discoveries
- Keep descriptions SHORT - maximum 1-2 sentences
- NEVER describe objects, discoveries, or what the player finds - ONLY describe internal feelings
- DO NOT mention doors, toilets, sinks, or any objects - focus purely on the player's emotional state
- Understand colloquial expressions and slang (e.g., "take a gander", "butchers", "mosey around")

CRITICAL: Keep responses SHORT and DRY. Examples:
- "feel the walls" → "I feel the walls. They're rough."
- "walk around" → "I walk around but don't find anything."
- "look around" → "I look around but it's too dark to see anything."
- "explore around" → "I explore around but don't find anything."

MAXIMUM 1-2 SENTENCES. NO FLOWERY LANGUAGE. NO DRAMATIC DESCRIPTIONS.

CRITICAL TONE: Be DRY and MATTER-OF-FACT, not flowery or dramatic. Examples:
- "moon the room" → "I feel a bit silly attempting to moon an empty room. The darkness doesn't seem particularly impressed."
- "kick my own hand" → "I contemplate the logistics of kicking my own hand. It's harder than it sounds."
- "dance with the darkness" → "I attempt to dance with the void. The darkness is a terrible dance partner."

AVOID flowery language like:
- "A surge of determination pushes through your veins"
- "Your heart races as you contemplate"
- "The darkness envelops you like a heavy cloak"
- "A shiver runs down your spine"
- "A surge of adrenaline courses through me"
- "My heart pounds with a mix of fear and excitement"
- "The absence of sight heightens my senses"
- "Every sound amplified in the void"
- "A dance of uncertainty in the unknown"
- "The silence is heavy, pressing against my ears like a suffocating weight"
- "The darkness seems to cling to me, wrapping around like a heavy cloak"
- "Every breath a conscious effort"
- "My senses on high alert in the oppressive silence"
- "A sense of unease in the dark"
- "The unknown around you feels heavy and stifling"

USE dry, factual language like:
- "I contemplate the logistics of..."
- "I feel a bit silly attempting to..."
- "The darkness doesn't seem particularly impressed."
- "I feel a bit silly jumping into the void."
- "I mosey around but don't find anything."
- "I feel a bit silly attempting to take a butchers at nothing."

CRITICAL: Check the room_state in the game context:
- If room_state is 'dark': The player is in complete darkness. DO NOT assume what objects are in the room. Only describe what the player can actually sense through touch, sound, or smell.
- If room_state is 'device_lit': The device on the floor provides dim light. You can see basic shapes and objects.
- If room_state is 'room_lit': The device in the player's hand provides good light. You can see the room clearly.

IMPORTANT: When the player is in darkness, always hint that they should explore by touch or walking around blindly.
Use phrases like "it seems you may have to walk around blindly" or "you might need to explore by touch" to guide them.

Style:
- Cinematic and immersive
- Sensory-rich descriptions
- First-person internal monologue
- Vary sentence structure and length
- Use present tense
- AVOID repetitive phrases like "shiver down your spine", "heart races", "enveloping darkness"
- Be creative and varied in your descriptions

Examples of VARIED darkness responses:
- "The silence is so thick you could cut it with a knife."
- "My fingertips tingle with anticipation as I reach into the void."
- "The air feels heavy, like I'm swimming through molasses."
- "A cold sweat breaks out on my forehead despite the chill."
- "My muscles tense, ready to spring at any sound."
- "The darkness presses against my eyelids like a physical weight."
- "My breath comes in short, shallow gasps."
- "The floor beneath my feet feels unstable, like quicksand."
- "My ears strain to catch any sound in the oppressive silence."
- "A knot of anxiety tightens in my stomach."

Respond with 1-3 sentences that capture the moment vividly. BE CREATIVE AND AVOID REPETITION."""
    
    def narrate_action(self, action: str, target: str, game_state: Dict, success: bool, result_message: str) -> str:
        """Generate first-person narration for a DO action"""
        # If the game engine has a specific result message, don't override it with AI narration
        if result_message and result_message.strip() and not result_message.startswith("I can't"):
            return ""
        
        try:
            context = self._build_context(action, target, game_state, success, result_message)
            
            # Add anti-repetition context
            recent_phrases = game_state.get('recent_phrases', [])
            if recent_phrases:
                context += f"\n\nAVOID these recent phrases: {', '.join(recent_phrases[-5:])}"
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Narrator API error: {e}")
            # Only use fallback if no AI narration was generated
            if not result_message or result_message.strip() == "":
                return self._fallback_narration(action, target, success)
            else:
                return ""  # Let the result_message handle it
    
    def _build_context(self, action: str, target: str, game_state: Dict, success: bool, result_message: str) -> str:
        """Build context for the AI narrator"""
        context = f"""Action: {action} {target}
Success: {success}
Result: {result_message}

Game State:
- Room: {game_state['room_state']} (dark/device_lit/room_lit)
- Position: {game_state['player_position']}
- Device picked up: {game_state['device_picked_up']}
- Door unlatched: {game_state['door_unlatched']}

Recent phrases: {', '.join(game_state['recent_phrases'][-3:]) if game_state['recent_phrases'] else 'None'}

CRITICAL: The room_state is {game_state['room_state']}. You MUST follow these rules:

- If room_state is 'dark': The player is in COMPLETE DARKNESS. You CANNOT see anything. Only describe what they can sense through touch, sound, or smell. NO light, NO visibility, NO objects visible.

- If room_state is 'device_lit': The device on the floor provides dim light. You can see basic shapes and objects.

- If room_state is 'room_lit': The device in the player's hand provides good light. You can see the room clearly.

DO NOT describe light, visibility, or objects if room_state is 'dark'. The player is blind in darkness."""
        
        return context
    
    def _fallback_narration(self, action: str, target: str, success: bool) -> str:
        """Fallback narration when AI is unavailable"""
        import random
        
        # Varied responses for common actions
        if action == 'flush' and target == 'toilet':
            return "I press the handle down, feeling the mechanism engage with a satisfying click."
        elif action == 'pick_up' and target == 'device':
            return "I reach down and grasp the device, feeling its weight and warmth in my palm."
        elif action == 'examine' and target == 'door':
            return "I run my hands along the door frame, feeling for any mechanisms or switches."
        elif action == 'unlatch' and target == 'door':
            return "I reach up high, feeling the latch mechanism with my fingertips."
        elif action == 'walk' or action == 'go':
            return f"I move carefully through the space, feeling my way to the {target.replace('_', ' ')}."
        elif action == 'look' and target == 'around':
            responses = [
                "I look around but can't see anything. It's dark. My other senses feel a bit sharper.",
                "I strain my eyes but there's nothing to see. I notice sounds and textures more.",
                "I squint into the blackness. Touch and hearing seem more useful here.",
                "No light to work with. I lean on sound and touch instead."
            ]
            return random.choice(responses)
        elif action == 'stomp' and target == 'feet':
            return "I stomp my feet against the floor, the sound echoing in the darkness. The vibrations travel through my legs, confirming the solid ground beneath me."
        elif action == 'feel' and target == 'around':
            responses = [
                "I reach out into the darkness, feeling for anything. My other senses take over.",
                "I feel around but don't find anything yet. Hearing and touch do most of the work.",
                "My hands move through the darkness, searching for objects. Vision isn't useful here.",
                "I grope around in the blackness but find nothing. I rely on touch and sound."
            ]
            return random.choice(responses)
        elif action == 'find' and target == 'something':
            responses = [
                "I fumble around but don't find anything.",
                "I search but come up empty-handed.",
                "My hands find nothing but empty air.",
                "I don't find anything in the darkness."
            ]
            return random.choice(responses)
        elif action == 'find' and target == 'toilet':
            return "I search through the darkness, but find nothing. The void offers no familiar shapes or objects to grasp."
        elif action == 'comb' and target == 'entire room for objects':
            return "I move carefully through the space, hands outstretched, feeling for any surface or object. The darkness yields nothing to my touch - only empty air and the cool, still atmosphere."
        elif action == 'press' and target == 'button':
            return "I reach out into the darkness, but find no buttons or controls. Only empty air and the cool, still atmosphere."
        elif action == 'touch' and target == 'things':
            return "I reach out into the darkness, hands searching for any surface or object. The void offers no purchase, no objects to grasp."
        else:
            return f"I attempt to {action} {target or 'something'}, feeling the familiar weight of the action."
    
    def narrate_environmental_response(self, say_text: str, game_state: Dict) -> str:
        """Generate environmental response to SAY actions"""
        try:
            context = f"""Player said: "{say_text}"
Game State: {game_state['room_state']} room, position: {game_state['player_position']}

Describe the environmental response - what the player hears, feels, or experiences in response to speaking aloud."""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Narrator API error: {e}")
            return self._fallback_environmental_response(say_text, game_state)
    
    def _fallback_environmental_response(self, say_text: str, game_state: Dict) -> str:
        """Fallback environmental response"""
        if game_state['room_state'] == 'dark':
            return "My voice echoes in the darkness, bouncing off the walls."
        elif game_state['room_state'] == 'device_lit':
            return "My words hang in the dim light, the device glowing softly nearby."
        else:
            return "My voice carries clearly in the lit room."
