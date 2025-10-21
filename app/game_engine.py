import json
import os
import time
from typing import Dict, List, Optional, Tuple
from .state import RoomLight, Tutorial, advance_tutorial, room_light_to_string, string_to_room_light

class GameEngine:
    def __init__(self):
        self.room_config = self._load_room_config()
        self.game_state = {
            'room_id': 'room0',
            'room_state': 'dark',  # dark, device_lit, room_lit (backward compatibility)
            'room_light': RoomLight.DARK,  # new enum-based state
            'player_position': 'center',
            'player_name': None,
            'device_picked_up': False,
            'door_unlatched': False,
            'patch_messages': [],
            'patch_unread_count': 0,
            'conversation_history': [],
            'recent_phrases': [],
            'tutorial': Tutorial.NOT_STARTED,  # new enum-based tutorial state
            # Legacy flags for backward compatibility
            'tutorial_step': 0,
            'tutorial_photo_needed': False,
            'photo_request_active': False,
            # New state tracking
            'mirror_exam_count': 0,
            'photo_script': None
        }
        
    def _load_room_config(self) -> Dict:
        """Load room configuration from JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'room0.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def start_photo_script(self, item_key: str, examine_text: str) -> Tuple[bool, str, Dict]:
        """Standardized photo script template for all photo items"""
        # Block photo scripts only while the tutorial camera is still pending
        if self.game_state.get('tutorial_photo_needed', False):
            return True, f"I examine the {examine_text}.", {}
        
        # Set photo script state
        self.game_state['photo_script'] = item_key
        self.game_state['photo_request_active'] = True
        
        # Clear old tutorial messages to prevent conflicts
        self.game_state['patch_messages'] = []
        self.game_state['patch_unread_count'] = 0
        
        # Standardized response
        response = f"Take a picture of this {examine_text}."
        
        return True, response, {
            'patch_message': True,
            'show_patch_button': True,
            'patch_button_blink': True  # New: makes button blink red
        }

    def normalize_command(self, action: str, target: str) -> Tuple[str, str]:
        """Normalize command using verb aliases"""
        # Verb alias maps
        verb_aliases = {
            'look': ['look', 'look around', 'examine room', 'scan', 'peek'],
            'feel': ['feel', 'touch', 'finger', 'use hands', 'tinker with'],
            'listen': ['listen', 'keep my ears peeled', 'hear', 'quiet down'],
            'smell': ['smell', 'sniff', 'breathe in']
        }
        
        # Find canonical verb
        canonical_action = action
        for canonical, aliases in verb_aliases.items():
            if action.lower() in aliases:
                canonical_action = canonical
                break
        
        return canonical_action, target

    def _handle_listen(self) -> Tuple[bool, str, Dict]:
        """Handle listen command - provides contextual audio hints"""
        if self.game_state['room_light'] == RoomLight.DARK:
            return True, "I calm my breathing until I can hear my own heartbeat, oh what's that? I can hear dripping water.", {}
        elif self.game_state['room_light'] == RoomLight.PHONE_GLOW:
            return True, "I listen carefully. The dripping sound is clearer now - it's coming from the sink.", {}
        else:
            return True, "I listen to the room. The dripping from the sink is clear and steady.", {}

    def _sync_legacy_state(self):
        """Sync legacy boolean flags with enum state for backward compatibility"""
        # Sync room_state with room_light enum
        self.game_state['room_state'] = room_light_to_string(self.game_state['room_light'])
        
        # Sync tutorial flags with tutorial enum
        tutorial = self.game_state['tutorial']
        self.game_state['tutorial_step'] = tutorial.value if hasattr(tutorial, 'value') else 0
        
        # Only set tutorial_photo_needed if it hasn't been manually set to False
        if self.game_state.get('tutorial_photo_needed') is not False:
            self.game_state['tutorial_photo_needed'] = tutorial in [Tutorial.DEVICE_PICKED, Tutorial.NAME_SET, Tutorial.PATCH_INTRO_DONE]
        
        # photo_request_active can be set manually for article scripts
        # Only override if it's not already set to True
        if self.game_state.get('photo_request_active') != True:
            self.game_state['photo_request_active'] = tutorial in [Tutorial.PATCH_INTRO_DONE, Tutorial.MIRROR_PROMPTED, Tutorial.ARTICLE_PROMPTED]
        self.game_state['device_picked_up'] = tutorial != Tutorial.NOT_STARTED

    def get_game_state(self) -> Dict:
        """Get current game state"""
        # Preserve manually set photo_request_active before syncing
        manual_photo_active = self.game_state.get('photo_request_active')
        self._sync_legacy_state()  # Ensure legacy fields are synced
        # Restore manual setting if it was True
        if manual_photo_active == True:
            self.game_state['photo_request_active'] = True
        state = self.game_state.copy()
        # Convert set to list for JSON serialization
        if 'discovered_items' in state:
            state['discovered_items'] = list(state['discovered_items'])
        # Convert enum to string for JSON serialization
        if 'room_light' in state and hasattr(state['room_light'], 'name'):
            state['room_light'] = state['room_light'].name
        if 'tutorial' in state and hasattr(state['tutorial'], 'name'):
            state['tutorial'] = state['tutorial'].name
        return state
    
    def get_room_description(self) -> str:
        """Get current room description based on state"""
        if self.game_state['room_state'] == 'dark':
            return "You're in complete darkness. You can't see anything."
        elif self.game_state['room_state'] == 'device_lit':
            return "The device on the floor glows softly, casting dim light around the room."
        else:  # room_lit
            return "The device in your hand provides enough light to see the room clearly."
    
    def get_room_map(self) -> str:
        """Generate ASCII art map of current room"""
        if self.game_state['room_state'] == 'dark':
            return "I can't see the map in the darkness."
        
        discovered_items = self.game_state.get('discovered_items', set())
        
        # ASCII art for the bathroom
        map_art = """
    ┌─────────────────┐
    │                 │
    │   DOOR          │
    │                 │
    │  TOILET         │
    │                 │
    │  SINK           │
    │                 │
    └─────────────────┘
        """
        
        # Add discovered items to the map
        if 'door' in discovered_items:
            map_art = map_art.replace("DOOR", "DOOR ✓")
        if 'toilet' in discovered_items:
            map_art = map_art.replace("TOILET", "TOILET ✓")
        if 'sink' in discovered_items:
            map_art = map_art.replace("SINK", "SINK ✓")
        
        return f"Room Map:\n{map_art}\n✓ = Discovered"
    
    def get_visible_items(self) -> List[Dict]:
        """Get items visible to player based on current state"""
        visible_items = []
        for item_id, item in self.room_config['items'].items():
            if item.get('visible_in_dark', False) or self.game_state['room_state'] != 'dark':
                visible_items.append({
                    'id': item_id,
                    'name': item['name'],
                    'description': item['description'],
                    'position': item['position']
                })
        return visible_items
    
    def can_reach_item(self, item_name: str) -> bool:
        """Check if player can reach an item from current position"""
        for item_id, item in self.room_config['items'].items():
            if item['name'] == item_name or (item_name == 'door' and item['name'] == 'red door'):
                return item['position'] == self.game_state['player_position']
        return False
    
    def _parse_colloquial_expressions(self, action: str, target: str) -> Tuple[str, str]:
        """Parse colloquial expressions and slang into standard commands"""
        # Look around / examine room expressions
        look_expressions = [
            'take a gander', 'take a look', 'have a look', 'check out', 'scope out',
            'take a butchers', 'butchers', 'butcher\'s', 'butchers hook',
            'peek', 'peep', 'glance', 'survey', 'scan', 'inspect',
            'get a load of', 'check', 'see what\'s here', 'what\'s around',
            'suss out', 'suss', 'case the joint', 'case', 'recon', 'reconnaissance'
        ]
        
        # Movement expressions
        move_expressions = [
            'mosey', 'saunter', 'stroll', 'wander', 'amble', 'perambulate',
            'shuffle', 'creep', 'sneak', 'tip-toe', 'tread', 'step',
            'head over', 'make my way', 'get to', 'reach', 'approach'
        ]
        
        # Touch/feel expressions
        touch_expressions = [
            'feel around', 'grope', 'fumble', 'touch', 'handle', 'fiddle',
            'poke around', 'root around', 'rummage', 'search', 'explore',
            'investigate', 'probe', 'palpate', 'manipulate'
        ]
        
        # Examine expressions
        examine_expressions = [
            'examine', 'inspect', 'check out', 'have a look at', 'take a look at',
            'have a butchers at', 'butchers', 'butcher\'s', 'butchers hook',
            'suss out', 'suss', 'case', 'recon', 'reconnaissance'
        ]
        
        # Check if action matches any colloquial expressions
        if any(expr in action for expr in look_expressions):
            return 'look', target or 'around'
        elif any(expr in action for expr in move_expressions):
            return 'go', target or 'around'
        elif any(expr in action for expr in touch_expressions):
            return 'feel', target or 'around'
        elif any(expr in action for expr in examine_expressions):
            return 'examine', target or 'around'
        
        # Handle specific phrases
        if 'take a gander' in action or 'take a butchers' in action:
            return 'look', target or 'around'
        if 'mosey' in action or 'saunter' in action:
            return 'go', target or 'around'
        if 'poke around' in action or 'root around' in action:
            return 'feel', target or 'around'
        
        # Special easter egg responses
        if 'fuck around' in action:
            return 'fuck_around', target or ''
        
        return action, target
    
    def process_action(self, action: str, target: str = None) -> Tuple[bool, str, Dict]:
        """Process a DO action and return (success, message, state_changes)"""
        action = action.lower().strip()
        target = target.lower().strip() if target else None
        
        # Normalize target prepositions (e.g., "look at mirror" → target "mirror")
        if target and target.startswith('at '):
            target = target[3:]
        if target and target.startswith('the '):
            target = target[4:]

        # Parse colloquial expressions and slang
        action, target = self._parse_colloquial_expressions(action, target)
        
        # Apply verb alias normalization
        action, target = self.normalize_command(action, target)
        
        # Track recent phrases for anti-repetition
        if 'recent_phrases' not in self.game_state:
            self.game_state['recent_phrases'] = []
        
        # Add current action to recent phrases (keep last 10)
        current_phrase = f"{action} {target or ''}".strip()
        if current_phrase not in self.game_state['recent_phrases']:
            self.game_state['recent_phrases'].append(current_phrase)
            if len(self.game_state['recent_phrases']) > 10:
                self.game_state['recent_phrases'].pop(0)
        
        # Handle position changes
        if action in ['walk', 'go', 'move'] and target:
            # Check if it's a general direction (forward, backward, left, right)
            if target in ['forward', 'backward', 'left', 'right', 'ahead', 'back']:
                return True, "", {'ai_narration': True}
            elif target in ['around', 'room', 'area', 'space', 'blindly', 'around blindly'] or 'around' in target or 'blindly' in target or 'through' in target:
                # Handle general exploration
                return self._handle_general_exploration()
            else:
                return self._handle_position_change(target)
        elif action in ['move', 'walk', 'go'] and not target:
            # Handle general movement commands - chance to discover something
            return self._handle_general_exploration()
        
        # Handle help
        if action == 'help' or action == 'what' or action == 'commands':
            return self._handle_help()
        
        # Handle special easter egg actions
        if action == 'fuck_around':
            return self._handle_fuck_around()
        
        # Handle silly/absurd actions
        if action in ['moon', 'dance', 'sing', 'yell', 'scream', 'whisper', 'kick', 'jump']:
            return self._handle_silly_action(action, target)
        
        # Handle colloquial movement actions
        if action in ['mosey', 'saunter', 'stroll', 'wander', 'amble']:
            return self._handle_silly_action('mosey', target)
        
        # Handle specific feel actions
        if action == 'feel' and target in ['walls', 'wall', 'the walls', 'the wall']:
            return True, "I feel the walls. They're rough.", {}
        
        # Handle explore around
        if action == 'explore' and target in ['around', 'the room', 'room']:
            return True, "I explore around but don't find anything.", {}
        
        # Handle common exploration commands without targets
        if action == 'explore' and not target:
            return True, "I explore but don't find anything.", {}
        
        if action == 'feel' and target == 'around':
            return True, "I feel around but don't find anything.", {}
        
        if action == 'navigate' and target == 'blindly':
            return True, "I navigate blindly but don't find anything.", {}
        
        if action == 'move' and target == 'around':
            return True, "I move around but don't find anything.", {}
        
        # Handle taste-related actions (teleport to toilet with hint)
        if action in ['lick', 'taste'] or ('tongue' in (action or '')) or ('tongue' in (target or '')) or ('lick' in (target or '')) or ('taste' in (target or '')):
            # Ensure toilet is discovered and move player to it
            discovered_items = self.game_state.get('discovered_items', set())
            if 'toilet' not in discovered_items:
                discovered_items.add('toilet')
                self.game_state['discovered_items'] = discovered_items
            self.game_state['player_position'] = 'at_toilet'
            # Force the player's name later to ToungeRaider when name modal appears
            self.game_state['forced_name'] = 'ToungeRaider'
            return True, (
                'You explore the room tongue first and find smooth porcelain on your tongue. '
                'It tastes like human waste. You hear a disembodied voice say, "Wow, did you just lick a toilet? '
                'How very Crowdis of you. Interesting strategy. Well urine luck, I come with hints. '
                'Try flushing the toilet, I\'ve been waiting to say something funny when you do".'
            ), {}

        # Handle discovery actions
        if action in ['feel', 'touch', 'search', 'find', 'explore'] and target:
            return self._handle_discovery(target)
        elif action in ['feel', 'touch', 'search', 'find', 'explore'] and not target:
            return self._handle_general_exploration()
        
        # Handle smell command - always returns mildew/stale-piss note
        if action == 'smell':
            return True, "I take a deep breath. The place smells of mildew and stale piss.", {}
        
        # Handle listen command - provides contextual audio hints
        if action == 'listen':
            return self._handle_listen()
        
        # Handle item interactions
        if action == 'flush' and target == 'toilet':
            return self._handle_flush_toilet()
        elif action == 'pick_up' and target == 'device':
            return self._handle_pick_up_device()
        elif action == 'pick_up' and target == 'glowing device':
            return self._handle_pick_up_device()
        elif action == 'examine' and target:
            return self._handle_examine(target)
        elif action == 'look' and target in ['room', 'around room', 'around']:
            return self._handle_examine('room')
        elif action == 'look' and target:
            return self._handle_examine(target)
        elif action == 'map' or (action == 'show' and target == 'map'):
            return self._handle_map()
        elif action == 'unlatch' and target == 'door':
            return self._handle_unlatch_door()
        elif action == 'open' and target == 'door':
            return self._handle_open_door()
        elif action in ['go', 'walk', 'move'] and 'through' in target and 'door' in target:
            # Handle going through door (room transition)
            if self.game_state['door_unlatched']:
                return True, "I step through the door into Room 1... (Coming soon!)", {'room_transition': True}
            else:
                return False, "The door is latched. You need to unlatch it first.", {}
        else:
            # Let AI handle unknown commands instead of rejecting them
            return True, "", {'ai_narration': True}
    
    def move_to(self, x: float, y: float) -> Tuple[bool, str, Dict]:
        """Move player to normalized coordinates in room (0..100). Clamps to bounds."""
        try:
            xn = max(0.0, min(100.0, float(x)))
            yn = max(0.0, min(100.0, float(y)))
        except Exception:
            return False, "Invalid coordinates.", {}

        self.game_state['player_xy'] = {'x': xn, 'y': yn}
        return True, "", {}

    def move_direction(self, distance: float, unit: str, direction: str) -> Tuple[bool, str, Dict]:
        """Move player by distance in a cardinal/diagonal direction."""
        try:
            dist = float(distance)
        except Exception:
            return False, "Invalid distance.", {}

        # Unit scale: meters ≈ 5, steps ≈ 2 (tunable)
        scale = 5.0 if (unit or '').lower().startswith('meter') else 2.0

        dx, dy = 0.0, 0.0
        d = (direction or '').lower().strip()
        if d in ['n', 'north', 'up']:
            dy = -1
        elif d in ['s', 'south', 'down']:
            dy = 1
        elif d in ['e', 'east', 'right']:
            dx = 1
        elif d in ['w', 'west', 'left']:
            dx = -1
        elif d in ['ne', 'northeast', 'north-east']:
            dx, dy = 0.7071, -0.7071
        elif d in ['nw', 'northwest', 'north-west']:
            dx, dy = -0.7071, -0.7071
        elif d in ['se', 'southeast', 'south-east']:
            dx, dy = 0.7071, 0.7071
        elif d in ['sw', 'southwest', 'south-west']:
            dx, dy = -0.7071, 0.7071
        else:
            return False, "Unknown direction.", {}

        move = dist * scale
        cur = self.game_state.get('player_xy', {'x': 50.0, 'y': 50.0})
        xn = cur['x'] + dx * move
        yn = cur['y'] + dy * move
        return self.move_to(xn, yn)

    def _handle_position_change(self, target: str) -> Tuple[bool, str, Dict]:
        """Handle player position changes"""
        # Map user-friendly names to position keys
        position_map = {
            'toilet': 'at_toilet',
            'sink': 'at_sink', 
            'door': 'at_door',
            'center': 'center',
            'at_toilet': 'at_toilet',
            'at_sink': 'at_sink',
            'at_door': 'at_door'
        }
        
        target_key = position_map.get(target.lower(), target)
        valid_positions = list(self.room_config['positions'].keys())
        
        if target_key in valid_positions:
            # Check if player has discovered this location (only in darkness)
            if self.game_state['room_light'] == RoomLight.DARK:
                discovered_items = self.game_state.get('discovered_items', set())
                if target_key == 'at_toilet' and 'toilet' not in discovered_items:
                    return False, "I can't go to the toilet — I haven't discovered it yet. Maybe I should explore by touch first.", {}
                elif target_key == 'at_sink' and 'sink' not in discovered_items:
                    return False, "I can't go to the sink — I haven't discovered it yet. Maybe I should explore by touch first.", {}
                elif target_key == 'at_door' and 'door' not in discovered_items:
                    return False, "I can't go to the door — I haven't discovered it yet. Maybe I should explore by touch first.", {}
            
            # If room is lit, player can see and go to any valid position
            self.game_state['player_position'] = target_key
            return True, f"I walk to the {target.replace('_', ' ')}.", {'position': target_key}
        else:
            if self.game_state['room_light'] == RoomLight.DARK:
                return False, f"I can't go to {target}. Maybe I should explore by touch first.", {}
            else:
                return False, f"I can't go to {target}. Maybe I should look around first.", {}
    
    def _handle_flush_toilet(self) -> Tuple[bool, str, Dict]:
        """Handle toilet flush - triggers device lighting"""
        if not self.can_reach_item('toilet'):
            if self.game_state['room_light'] == RoomLight.DARK:
                return False, "I can't reach that from here. Maybe I should explore by touch first.", {}
            else:
                return False, "I can't reach that from here. Maybe I should look around first.", {}
        
        if self.game_state['room_light'] == RoomLight.DARK:
            self.game_state['room_light'] = RoomLight.PHONE_GLOW
            self.game_state['patch_unread_count'] += 1
            self.game_state['patch_messages'].append({
                'sender': 'patch',
                'message': "Everything come out alright? ...Sorry, couldn't resist. I'm Patch.",
                'timestamp': self._get_timestamp()
            })
            return True, "I flush the toilet. The sound echoes in the darkness. Suddenly, a **glowing device** on the floor lights up with a message.", {
                'room_state': 'device_lit',
                'patch_message': True,
                'show_patch_button': True,
                'show_pickup_button': True
            }
        else:
            return True, "I flush the toilet.", {}
    
    def _handle_pick_up_device(self) -> Tuple[bool, str, Dict]:
        """Handle picking up the Patch device"""
        if not self.can_reach_item('device'):
            return False, "I can't reach the device from here. Maybe I should walk to the toilet first.", {}
        
        if self.game_state['tutorial'] != Tutorial.NOT_STARTED:
            return False, "I already have the device.", {}
        
        if self.game_state['room_light'] == RoomLight.DARK:
            return False, "I can't see the device in the darkness.", {}
        
        # Device is only visible when room is PHONE_GLOW or LIT
        if self.game_state['room_light'] not in [RoomLight.PHONE_GLOW, RoomLight.LIT]:
            return False, "I can't see the device.", {}
        
        # Advance tutorial state
        self.game_state['tutorial'] = advance_tutorial(self.game_state['tutorial'], 'device_picked')
        self.game_state['room_light'] = RoomLight.LIT
        
        # Set tutorial photo needed flag
        self.game_state['tutorial_photo_needed'] = True
        
        # Initially disable camera until IMPORTANT message
        self.game_state['photo_request_active'] = False
        
        return True, "I pick up the device. It glows softly in my hand, providing enough light to see the room clearly.", {
            'device_picked_up': True,
            'room_state': 'room_lit',
            'name_modal': True,
            'show_patch_button': True,
            'patch_message': True
        }
    
    def _get_examine_table_response(self, target: str, room_light: RoomLight) -> Optional[str]:
        """Get table-driven examine response for specific item+light combinations"""
        player_position = self.game_state.get('player_position', 'center')
        
        # Position-aware examine responses
        examine_table = {
            # Dark state responses - only when at the object
            ('toilet', RoomLight.DARK, 'toilet'): "I can tell I'm standing in pee. I can't see the toilet but I can feel the flusher and some reading material on the top of the tank. It's too dark to see what it says, though.",
            ('toilet', RoomLight.DARK, 'not_toilet'): "I examine the toilet from here, but it's too dark to see anything.",
            ('sink', RoomLight.DARK, 'sink'): "I examine the sink. Above it hangs a mirror.",
            ('sink', RoomLight.DARK, 'not_sink'): "I examine the sink from here, but it's too dark to see anything.",
            ('mirror', RoomLight.DARK, 'sink'): "I sense glass. My reflection refuses to load.",
            ('mirror', RoomLight.DARK, 'not_sink'): "I examine the mirror from here, but it's too dark to see anything.",
            ('door', RoomLight.DARK, 'door'): "I feel along the wall and encounter a solid surface. I've found what feels like a door.",
            ('door', RoomLight.DARK, 'not_door'): "I examine the door from here, but it's too dark to see anything.",
            
            # Device-lit state responses - only when at the object
            ('toilet', RoomLight.PHONE_GLOW, 'toilet'): "I can tell I'm standing in pee. I can't see the toilet but I can feel the flusher and some reading material on the top of the tank. It's too dark to see what it says, though.",
            ('toilet', RoomLight.PHONE_GLOW, 'not_toilet'): "I examine the toilet from here. In the dim light, I can make out its shape but can't see details.",
            ('sink', RoomLight.PHONE_GLOW, 'sink'): "I examine the sink. Above it hangs a mirror.",
            ('sink', RoomLight.PHONE_GLOW, 'not_sink'): "I examine the sink from here. In the dim light, I can see it has a mirror above it.",
            ('mirror', RoomLight.PHONE_GLOW, 'sink'): "I sense glass. My reflection refuses to load.",
            ('mirror', RoomLight.PHONE_GLOW, 'not_sink'): "I examine the mirror from here. In the dim light, I can see it's there but can't make out my reflection.",
            ('door', RoomLight.PHONE_GLOW, 'door'): "Red paint drinks the blue glow; still locked.",
            ('door', RoomLight.PHONE_GLOW, 'not_door'): "I examine the door from here. In the dim light, I can see it's there but can't make out details.",
            
            # Room-lit state responses - only when at the object
            ('toilet', RoomLight.LIT, 'toilet'): "There appears to be a magazine article on the back of the toilet.",
            ('toilet', RoomLight.LIT, 'not_toilet'): "I examine the toilet from here. In the light, I can see there's a magazine article on the back of it.",
            ('sink', RoomLight.LIT, 'sink'): "I examine the sink. Above it hangs a mirror.",
            ('sink', RoomLight.LIT, 'not_sink'): "I examine the sink from here. In the light, I can see it has a mirror above it.",
            ('mirror', RoomLight.LIT, 'sink'): "I examine the mirror. I can see my reflection clearly in the light.",
            ('mirror', RoomLight.LIT, 'not_sink'): "I examine the mirror from here. In the light, I can see it clearly.",
            ('door', RoomLight.LIT, 'door'): "I examine the door. In the light, I can see there's a latch high up on the door frame. It seems the door was always just latched from the inside.",
            ('door', RoomLight.LIT, 'not_door'): "I examine the door from here. In the light, I can see there's a latch high up on the door frame.",
        }
        
        # Determine position key
        if target == 'toilet':
            position_key = 'toilet' if player_position == 'toilet' else 'not_toilet'
        elif target == 'sink':
            position_key = 'sink' if player_position == 'sink' else 'not_sink'
        elif target == 'mirror':
            position_key = 'sink' if player_position == 'sink' else 'not_sink'  # Mirror is at sink
        elif target == 'door':
            position_key = 'door' if player_position == 'door' else 'not_door'
        else:
            return None
            
        return examine_table.get((target, room_light, position_key))

    def _handle_examine(self, target: str) -> Tuple[bool, str, Dict]:
        """Handle examining objects"""
        if target == 'room':
            if self.game_state['room_light'] == RoomLight.LIT:
                return True, "I examine the room. In the light from my device, I can clearly see: a toilet, a sink with a mirror above it, and a door.", {}
            elif self.game_state['room_light'] == RoomLight.PHONE_GLOW:
                return True, "I examine the room. In the dim light from the device on the floor, I can make out: a toilet, a sink with a mirror above it, and a door.", {}
            else:  # dark
                return True, "I examine the room, but it's too dark to see anything. My other senses feel a bit sharper.", {}
        elif target == 'door' and self.game_state['room_light'] == RoomLight.LIT:
            if not self.game_state['door_unlatched']:
                return True, "I examine the door. In the light, I can see there's a latch high up on the door frame. It seems the door was always just latched from the inside.", {}
            else:
                return True, "The door is unlatched and ready to open.", {}
        elif target == 'device' and self.game_state['device_picked_up']:
            return True, "The device is warm in your hand, glowing softly. It looks like a cross between a modern smartphone and an old Nokia brick.", {}
        elif target == 'article':
            # Handle examine article - trigger photo script using template
            try:
                from .state import advance_tutorial, Tutorial
                self.game_state['tutorial'] = advance_tutorial(
                    self.game_state.get('tutorial', Tutorial.NOT_STARTED),
                    'article_prompted'
                )
            except Exception:
                pass
            return self.start_photo_script('toilet_article', 'article')
        else:
            # Check table-driven responses first
            table_response = self._get_examine_table_response(target, self.game_state['room_light'])
            if table_response:
                # Handle special mirror logic
                if target == 'mirror':
                    return self._handle_mirror_examine()
                # Handle special door logic  
                elif target == 'door':
                    return self._handle_door_examine()
                # Handle toilet article photo script - only after tutorial photo is taken
                elif target == 'toilet' and 'article' in table_response:
                    # Only trigger photo script if tutorial photo is complete
                    if not self.game_state.get('tutorial_photo_needed', False):
                        try:
                            from .state import advance_tutorial, Tutorial
                            self.game_state['tutorial'] = advance_tutorial(
                                self.game_state.get('tutorial', Tutorial.NOT_STARTED),
                                'article_prompted'
                            )
                        except Exception:
                            pass
                        return self.start_photo_script('toilet_article', 'article')
                    else:
                        # Tutorial photo not taken yet - return the "standing in pee" message
                        return True, table_response, {}
                else:
                    return True, table_response, {}
            
            return True, f"I examine the {target}.", {}
    
    def _handle_mirror_examine(self) -> Tuple[bool, str, Dict]:
        """Handle mirror examine with cycling quips"""
        self.game_state['mirror_exam_count'] += 1
        count = self.game_state['mirror_exam_count']
        
        mirror_quips = [
            "Like Kenneth, you're a 'mirror' shadow of your former self...",
            "It's you, dummy",
            "Mirror, mirror, on the wall, this magic phrase was never said at all",
            "Pull some faces if your feelin froggy",
            "Take a picture it will last longer"
        ]
        
        if count <= len(mirror_quips):
            response = mirror_quips[count - 1]
            state_changes = {}
            
            # On the 5th examine, enable camera using template
            if count == 5:
                return self.start_photo_script('mirror', 'mirror')
            
            return True, response, state_changes
        else:
            # After 5 examines, just repeat the last quip
            return True, mirror_quips[-1], {}
    
    def _handle_door_examine(self) -> Tuple[bool, str, Dict]:
        """Handle door examine with Patch messages"""
        # Add Patch messages for door examine
        patch_messages = [
            {'sender': 'patch', 'message': "Real fake doors", 'timestamp': self._get_timestamp()},
            {'sender': 'patch', 'message': "Every time a door opens, a toilet seat closes... Or something like that.", 'timestamp': self._get_timestamp()}
        ]
        for msg in patch_messages:
            self.game_state['patch_messages'].append(msg)
        self.game_state['patch_unread_count'] += len(patch_messages)
        
        return True, "This is a door with a latch I can now see", {
            'patch_message': True,
            'show_patch_button': True
        }
    
    def _handle_map(self) -> Tuple[bool, str, Dict]:
        """Handle showing the room map"""
        map_text = self.get_room_map()
        return True, map_text, {}
    
    def _handle_unlatch_door(self) -> Tuple[bool, str, Dict]:
        """Handle unlatching the door"""
        if not self.can_reach_item('door'):
            return False, "I can't reach the door from here.", {}
        
        if self.game_state['room_state'] == 'dark':
            return False, "I can't see the latch in the darkness.", {}
        
        if self.game_state['door_unlatched']:
            return False, "The door is already unlatched.", {}
        
        self.game_state['door_unlatched'] = True
        return True, "I reach up and unlatch the door. It's now ready to open.", {
            'door_unlatched': True
        }
    
    def _handle_open_door(self) -> Tuple[bool, str, Dict]:
        """Handle opening the door"""
        if not self.can_reach_item('red door'):
            return False, "I can't reach the door from here. Maybe I should walk to the door first.", {}
        
        if not self.game_state['door_unlatched']:
            if self.game_state['room_state'] == 'dark':
                return False, "I try to open the door, but it doesn't budge. I can't see what's preventing it from opening.", {}
            else:
                return False, "The door is latched. You need to unlatch it first.", {}
        
        # For now, just indicate success - Room 1 will be implemented later
        return True, "I open the door. Beyond lies Room 1... (Coming soon!)", {
            'door_opened': True
        }
    
    def _handle_help(self) -> Tuple[bool, str, Dict]:
        """Handle help command"""
        help_text = """HELP - Vantablack Game

MOVEMENT:
- walk to [location] (explore the space)
- go to [location]
- move to [location]

ACTIONS:
- feel around (explore by touch)
- examine [object] (when you can see)
- pick up [object] (when available)
- open [object] (when possible)
- map (show room map - when you have light)

CURRENT STATE:
- Room: """ + self.game_state['room_state'] + """
- Position: """ + self.game_state['player_position'] + """

TIP: You're in complete darkness. Try exploring by touch first!"""
        
        return True, help_text, {}
    
    def _handle_fuck_around(self) -> Tuple[bool, str, Dict]:
        """Handle the special 'fuck around' easter egg"""
        return True, "I fucked around and found out.", {}
    
    def _handle_silly_action(self, action: str, target: str) -> Tuple[bool, str, Dict]:
        """Handle silly/absurd actions with humorous responses"""
        silly_responses = {
            'moon': [
                "I attempt to moon the room. The darkness doesn't seem particularly impressed.",
                "I moon the void. It's not very responsive.",
                "I bare my behind to the darkness. It remains unimpressed."
            ],
            'dance': [
                "I attempt to dance with the darkness. It's a terrible dance partner.",
                "I dance alone in the void. The darkness doesn't know the steps.",
                "I bust a move in the blackness. The darkness remains unimpressed."
            ],
            'sing': [
                "I sing to the darkness. It doesn't sing back.",
                "I serenade the void. The acoustics are terrible.",
                "I belt out a tune in the blackness. The darkness remains silent."
            ],
            'yell': [
                "I yell into the darkness. The echo is surprisingly underwhelming.",
                "I scream at the void. It doesn't scream back.",
                "I shout into the blackness. The darkness remains unimpressed."
            ],
            'scream': [
                "I scream into the darkness. The void doesn't scream back.",
                "I let out a blood-curdling scream. The darkness remains unfazed.",
                "I scream at the top of my lungs. The darkness is not impressed."
            ],
            'whisper': [
                "I whisper to the darkness. It doesn't whisper back.",
                "I speak softly to the void. The darkness remains silent.",
                "I whisper secrets to the blackness. It keeps them well."
            ],
            'kick': [
                "I contemplate the logistics of kicking my own hand. It's harder than it sounds.",
                "I attempt to kick my own hand. The physics are against me.",
                "I try to kick my own hand. My coordination isn't quite up to the task."
            ],
            'jump': [
                "I feel a bit silly jumping into the void. The darkness doesn't seem particularly impressed.",
                "I attempt to jump into the void. It's not very responsive.",
                "I jump into the darkness. The void remains unimpressed."
            ],
            'mosey': [
                "I mosey around but don't find anything.",
                "I saunter through the darkness. The void doesn't seem to care.",
                "I amble around but the darkness remains unimpressed."
            ]
        }
        
        import random
        if action in silly_responses:
            response = random.choice(silly_responses[action])
            return True, response, {}
        
        return True, f"I {action} {target or 'around'}. The darkness remains unimpressed.", {}
    
    def _handle_discovery(self, target: str) -> Tuple[bool, str, Dict]:
        """Handle discovery actions - find objects in darkness"""
        target_lower = target.lower()
        
        # Check if player is looking for specific objects
        if target_lower in ['toilet', 'bathroom', 'fixture']:
            # Player is looking for toilet - but they need to discover it first!
            discovered_items = self.game_state.get('discovered_items', set())
            if 'toilet' in discovered_items:
                return True, "I feel around and my hand brushes against cold, smooth ceramic. I've found what feels like a toilet.", {'discovered_toilet': True}
            else:
                return True, "I search for a toilet but find nothing. I need to explore more to discover what's in this room.", {}
        elif target_lower in ['sink', 'faucet', 'basin']:
            # Player is looking for sink
            discovered_items = self.game_state.get('discovered_items', set())
            if 'sink' in discovered_items:
                return True, "I reach out and feel cold, smooth porcelain. I've found what appears to be a sink.", {'discovered_sink': True}
            else:
                return True, "I search for a sink but find nothing. I need to explore more to discover what's in this room.", {}
        elif target_lower in ['door', 'exit', 'way out']:
            # Player is looking for door
            discovered_items = self.game_state.get('discovered_items', set())
            if 'door' in discovered_items:
                return True, "I feel along the wall and encounter a solid surface. I've found what feels like a door.", {'discovered_door': True}
            else:
                return True, "I search for a door but find nothing. I need to explore more to discover what's in this room.", {}
        else:
            # Generic search - let AI handle it
            return True, "", {'ai_narration': True}
    
    def _handle_general_exploration(self) -> Tuple[bool, str, Dict]:
        """Handle general exploration without specific target"""
        # Check what the player has already discovered
        discovered_items = self.game_state.get('discovered_items', set())
        print(f"DEBUG: discovered_items = {discovered_items}")
        
        # Random chance to discover something new
        import random
        roll = random.random()
        print(f"DEBUG: roll = {roll}, threshold = 0.9")
        if roll < 0.9:  # 90% chance to find something
            # Available discoveries based on what hasn't been found yet
            available_discoveries = []
            
            # Always discover door first to create the mystery
            if 'door' not in discovered_items:
                available_discoveries.append(("door", "I feel along the wall and encounter a solid surface. I've found what feels like a door."))
            
            if 'toilet' not in discovered_items:
                available_discoveries.append(("toilet", "I feel around and my hand brushes against cold, smooth ceramic. I've found what feels like a toilet."))
            
            if 'sink' not in discovered_items:
                available_discoveries.append(("sink", "I reach out and feel cold, smooth porcelain. I've found what appears to be a sink."))
            
            if available_discoveries:
                # Pick randomly from available discoveries
                selected_item, selected_message = random.choice(available_discoveries)
                
                discovered_items.add(selected_item)
                self.game_state['discovered_items'] = discovered_items
                
                # Update player position to match discovered item
                if selected_item == 'toilet':
                    self.game_state['player_position'] = 'at_toilet'
                elif selected_item == 'sink':
                    self.game_state['player_position'] = 'at_sink'
                elif selected_item == 'door':
                    self.game_state['player_position'] = 'at_door'
                
                return True, selected_message, {'discovered_item': selected_item}
        
        # If nothing discovered, let AI handle the general exploration
        return True, "", {'ai_narration': True}
    
    def _handle_unlatch_door(self) -> Tuple[bool, str, Dict]:
        """Handle unlatching the door"""
        if self.game_state['room_state'] != 'room_lit':
            return False, "It's too dark to see the latch. You need more light.", {}
        
        if self.game_state['door_unlatched']:
            return False, "The door is already unlatched.", {}
        
        self.game_state['door_unlatched'] = True
        return True, "I reach up and unlatch the door. It's now unlocked.", {}
    
    def _handle_open_door(self) -> Tuple[bool, str, Dict]:
        """Handle opening the door"""
        if not self.game_state['door_unlatched']:
            return False, "The door is locked. You need to unlatch it first.", {}
        
        return True, "I open the door and step through to the next room.", {'show_vantablack': True}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def reset_game(self):
        """Reset game to initial state"""
        self.game_state = {
            'room_id': 'room0',
            'room_state': 'dark',
            'room_light': RoomLight.DARK,
            'player_position': 'center',
            'player_xy': {'x': 50.0, 'y': 50.0},
            'player_name': None,
            'device_picked_up': False,
            'door_unlatched': False,
            'patch_messages': [],
            'patch_unread_count': 0,
            'conversation_history': [],
            'recent_phrases': [],
            'discovered_items': set(),
            'tutorial': Tutorial.NOT_STARTED,
            # Legacy flags for backward compatibility
            'tutorial_step': 0,
            'tutorial_photo_needed': False,
            'photo_request_active': False,
            # New state tracking
            'mirror_exam_count': 0,
            'photo_script': None
        }
