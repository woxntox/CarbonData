print("DEBUG: Loading routes.py with new code")
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
import os
from .game_engine import GameEngine
from .narrator import Narrator
from .patch_ai import PatchAI
import json
import datetime
from config.security import *

main = Blueprint('main', __name__)

# Initialize shared components
narrator = Narrator()
patch_ai = PatchAI()

# Store game engines per session ID
game_engines = {}

def log_gameplay(player_name, ip_address, command, response, session_id=None):
    """Log gameplay actions to a permanent file"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create filename with current date
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        log_file = f'logs/gameplay-{today}.log'
        
        # Format the log entry
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"""
=== {timestamp} ===
Player name: {player_name or 'Unknown'}
IP address: {ip_address}
Session ID: {session_id or 'Unknown'}
CMD: {command}
Response: {response}
{'='*50}
"""
        
        # Append to log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    except Exception as e:
        print(f"Error logging gameplay: {e}")

def get_game_engine():
    """Get or create a game engine for the current session"""
    session_id = session.get('session_id')
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    if session_id not in game_engines:
        game_engines[session_id] = GameEngine()
    
    return game_engines[session_id]

def _state_snapshot(game_engine: GameEngine) -> dict:
    gs = game_engine.get_game_state()
    return {
        'room': gs.get('room_id'),
        'light': gs.get('room_state'),  # legacy field for backward compatibility
        'position': gs.get('player_position'),
        'tutorial': {
            'device_picked_up': gs.get('device_picked_up'),
            'tutorial_photo_needed': gs.get('tutorial_photo_needed'),
            'photo_request_active': gs.get('photo_request_active'),
            'tutorial_state': gs.get('tutorial', 'NOT_STARTED')  # new enum state
        },
        'patch_unread_total': gs.get('patch_unread_count', 0)
    }

def _envelope(ok: bool, game_engine: GameEngine, narration: str = None, patch_messages: list = None, unread_delta: int = 0, ui: dict = None, stagger: str = None) -> dict:
    env = {
        'ok': ok,
        'state': _state_snapshot(game_engine)
    }
    if narration:
        env['narration'] = narration
    if patch_messages:
        env['patch'] = {
            'messages': [{'text': m['message'], 'sender': m.get('sender', 'patch')} for m in patch_messages],
            'unread_delta': unread_delta
        }
        if stagger:
            env['patch']['stagger'] = stagger
    if ui:
        env['ui'] = ui
    return env

@main.route('/')
def index():
    """Serve the splash page"""
    return render_template('splash.html')

@main.route('/game')
def game():
    """Serve the game interface"""
    return render_template('game.html')

@main.route('/game/state')
def get_game_state():
    """Get current game state"""
    game_engine = get_game_engine()
    return jsonify(game_engine.get_game_state())

@main.route('/game/reset', methods=['POST'])
def reset_game():
    """Reset game to initial state"""
    game_engine = get_game_engine()
    game_engine.reset_game()
    session['conversation_history'] = []
    return jsonify({'status': 'success'})

@main.route('/action/do', methods=['POST'])
def handle_do_action():
    """Handle DO actions (physical actions)"""
    try:
        data = request.get_json()
        action = data.get('action', '').strip()
        target = data.get('target', '').strip()
        
        if not action:
            return jsonify({'error': 'No action specified'}), 400
        
        # Get session-specific game engine
        game_engine = get_game_engine()
        
        # Process the action
        success, result_message, state_changes = game_engine.process_action(action, target)
        
        # Plugin hook for action processing
        from flask import current_app
        if hasattr(current_app, 'plugin_manager'):
            session_id = session.get('session_id')
            current_app.plugin_manager.on_action(action, target, {
                'success': success,
                'response': result_message,
                'state_changes': state_changes
            }, session_id=session_id)
        
        # Get current game state
        game_state = game_engine.get_game_state()
        
        # Generate narration
        narration = narrator.narrate_action(action, target, game_state, success, result_message)
        
        # Check if this needs AI narration
        needs_ai_narration = state_changes.get('ai_narration', False)
        
        # Update conversation history
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        session['conversation_history'].append({
            'type': 'do',
            'action': f"{action} {target}",
            'success': success,
            'result': result_message,
            'narration': narration
        })
        
        # Check for Patch messages
        patch_response = None
        env = None
        if state_changes.get('patch_message'):
            # Send all new messages since last check
            # For device pickup, send all tutorial messages
            if state_changes.get('device_picked_up'):
                # Send all tutorial messages (skip flush toilet message)
                tutorial_messages = [msg for msg in game_state['patch_messages'] if 'Nice to meet you' in msg['message'] or 'You are holding a cutting edge device' in msg['message'] or 'The truth is' in msg['message'] or 'So here\'s the deal' in msg['message'] or 'You need some light' in msg['message'] or 'IMPORTANT' in msg['message']]
                if tutorial_messages:
                    patch_response = {
                        'messages': tutorial_messages,
                        'unread_count': game_state['patch_unread_count']
                    }
                    env = _envelope(True, game_engine, narration, tutorial_messages, unread_delta=len(tutorial_messages), ui={ 'modal': 'patch' })
            else:
                # For other actions, send just the last message (if any exist)
                if game_state['patch_messages']:
                    patch_response = {
                        'message': game_state['patch_messages'][-1]['message'],
                        'unread_count': game_state['patch_unread_count']
                    }
                    env = _envelope(True, game_engine, narration, [game_state['patch_messages'][-1]], unread_delta=1)
                else:
                    patch_response = None
                    env = None
        
        # Log the gameplay action
        player_name = game_state.get('player_name')
        ip_address = request.remote_addr
        session_id = session.get('session_id')
        command = f"{action} {target}".strip()
        response = f"{result_message} | {narration}".strip()
        log_gameplay(player_name, ip_address, command, response, session_id)
        
        base = {
            'success': success,
            'result': result_message,
            'narration': narration,
            'game_state': game_state,
            'patch_response': patch_response,
            'needs_ai_narration': needs_ai_narration,
            'name_modal': state_changes.get('name_modal', False),
            'show_patch_button': state_changes.get('show_patch_button', False),
            'show_pickup_button': state_changes.get('show_pickup_button', False),
            'show_vantablack': state_changes.get('show_vantablack', False)
        }
        if env:
            base['envelope'] = env
        return jsonify(base)
        
    except Exception as e:
        print(f"DO action error: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/action/say', methods=['POST'])
def handle_say_action():
    """Handle SAY actions (speaking aloud)"""
    try:
        data = request.get_json()
        say_text = data.get('text', '').strip()
        
        if not say_text:
            return jsonify({'error': 'No text specified'}), 400
        
        # Get session-specific game engine
        game_engine = get_game_engine()
        
        # Get current game state
        game_state = game_engine.get_game_state()
        
        # Generate environmental response
        environmental_response = narrator.narrate_environmental_response(say_text, game_state)
        
        # Check if Patch should respond
        patch_response = None
        env = None
        if patch_ai.should_respond_to_say(say_text, game_state):
            patch_message = patch_ai.generate_say_response(say_text, game_state)
            if patch_message:
                # Add to Patch messages and update unread count first
                game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': patch_message,
                    'timestamp': game_engine._get_timestamp()
                })
                game_state['patch_unread_count'] += 1

                # Then return per-action increment for UI badge (always 1 for this SAY reply)
                patch_response = {
                    'message': patch_message,
                    'unread_count': 1,
                    'show_in_narration': True  # Flag to show in main narration
                }
                # Only create envelope if patch_messages exist
                if game_state['patch_messages']:
                    env = _envelope(True, game_engine, environmental_response, [game_state['patch_messages'][-1]], unread_delta=1)
                else:
                    env = None
        
        # Update conversation history
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        session['conversation_history'].append({
            'type': 'say',
            'text': say_text,
            'environmental_response': environmental_response,
            'patch_response': patch_response
        })
        
        # Log the gameplay action
        player_name = game_state.get('player_name')
        ip_address = request.remote_addr
        session_id = session.get('session_id')
        command = f"say: {say_text}"
        response = f"{environmental_response}"
        if patch_response:
            response += f" | Patch: {patch_response.get('message', '')}"
        log_gameplay(player_name, ip_address, command, response, session_id)
        
        base = {
            'environmental_response': environmental_response,
            'patch_response': patch_response,
            'game_state': game_state
        }
        if env:
            base['envelope'] = env
        return jsonify(base)
        
    except Exception as e:
        print(f"SAY action error: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/patch/coding_sequence', methods=['POST'])
def handle_coding_sequence():
    """Handle Patch's coding sequence for gallery feature"""
    try:
        game_engine = get_game_engine()
        game_state = game_engine.get_game_state()
        
        # Mark coding sequence as complete and enable gallery
        game_state['gallery_coding_sequence'] = False
        game_state['gallery_enabled'] = True
        game_state['gallery_question_answered'] = True
        
        return jsonify({
            'status': 'success',
            'gallery_enabled': True,
            'game_state': game_state
        })
        
    except Exception as e:
        print(f"Coding sequence error: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/patch/chat', methods=['POST'])
def handle_patch_chat():
    """Handle PATCH chat messages"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'No message specified'}), 400
        
        # Get session-specific game engine
        game_engine = get_game_engine()
        
        # Get current game state
        game_state = game_engine.get_game_state()
        
        # Get conversation history
        conversation_history = session.get('conversation_history', [])
        
        # Check if this is a response to the gallery question (only if not already completed)
        if (game_state.get('gallery_question_asked') and 
            not game_state.get('gallery_question_answered') and 
            not game_state.get('gallery_enabled') and
            not game_state.get('gallery_coding_sequence')):
            # Check if player said yes or no
            message_lower = message.lower()
            if any(word in message_lower for word in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'y', 'please', 'do it']):
                # Player said yes - start coding sequence
                game_state['gallery_question_answered'] = True
                game_state['gallery_coding_sequence'] = True
                
                # Add player message
                game_state['patch_messages'].append({
                    'sender': 'player',
                    'message': message,
                    'timestamp': game_engine._get_timestamp()
                })
                
                # Start coding sequence
                return jsonify({
                    'patch_response': {
                        'message': "Ok, strap in. You're about to be very impressed",
                        'coding_sequence': True
                    },
                    'game_state': game_state
                })
            elif any(word in message_lower for word in ['no', 'nope', 'nah', 'n', 'don\'t', 'dont']):
                # Player said no - Patch does it anyway
                game_state['gallery_question_answered'] = True
                game_state['gallery_coding_sequence'] = True
                
                # Add player message
                game_state['patch_messages'].append({
                    'sender': 'player',
                    'message': message,
                    'timestamp': game_engine._get_timestamp()
                })
                
                # Start coding sequence anyway
                return jsonify({
                    'patch_response': {
                        'message': "whatever, I'm doin it",
                        'coding_sequence': True
                    },
                    'game_state': game_state
                })
        
        # Generate Patch response
        patch_response = patch_ai.generate_response(message, game_state, conversation_history)
        
        # Plugin hook for response enhancement
        from flask import current_app
        if hasattr(current_app, 'plugin_manager'):
            patch_response = current_app.plugin_manager.enhance_response(patch_response, {
                'message': message,
                'game_state': game_state,
                'conversation_history': conversation_history
            })
        
        # Add to Patch messages
        game_state['patch_messages'].append({
            'sender': 'player',
            'message': message,
            'timestamp': game_engine._get_timestamp()
        })
        game_state['patch_messages'].append({
            'sender': 'patch',
            'message': patch_response,
            'timestamp': game_engine._get_timestamp()
        })
        
        # Update conversation history
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        session['conversation_history'].append({
            'type': 'patch_chat',
            'player_message': message,
            'patch_response': patch_response
        })
        
        return jsonify({
            'patch_response': patch_response,
            'game_state': game_state
        })
        
    except Exception as e:
        print(f"Patch chat error: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/patch/messages')
def get_patch_messages():
    """Get Patch message history"""
    game_engine = get_game_engine()
    game_state = game_engine.get_game_state()
    return jsonify({
        'messages': game_state['patch_messages'],
        'unread_count': game_state['patch_unread_count']
    })

@main.route('/patch/mark_read', methods=['POST'])
def mark_patch_read():
    """Mark Patch messages as read"""
    game_engine = get_game_engine()
    game_state = game_engine.get_game_state()
    game_state['patch_unread_count'] = 0
    return jsonify({'status': 'success'})

@main.route('/game/set_photo_script', methods=['POST'])
def set_photo_script():
    """Set photo script for camera uploads"""
    try:
        data = request.get_json()
        script = data.get('script', '').strip()
        
        if not script:
            return jsonify({'error': 'No script provided'}), 400
        
        # Get session-specific game engine
        game_engine = get_game_engine()
        
        # Set the photo script
        game_engine.game_state['photo_script'] = script
        game_engine.game_state['photo_request_active'] = True
        
        # Update tutorial enum to allow photo_request_active to be true
        try:
            from .state import advance_tutorial, Tutorial
            if script == 'toilet_article':
                game_engine.game_state['tutorial'] = advance_tutorial(
                    game_engine.game_state.get('tutorial', Tutorial.NOT_STARTED),
                    'article_prompted'
                )
        except Exception as e:
            print(f"DEBUG: Failed to advance tutorial: {e}")
        
        print(f"DEBUG: set_photo_script - Set photo_request_active to True")
        print(f"DEBUG: set_photo_script - game_state['photo_request_active']: {game_engine.game_state['photo_request_active']}")
        
        # Return updated game state so frontend can show camera button
        game_state = game_engine.get_game_state()
        print(f"DEBUG: set_photo_script - get_game_state() photo_request_active: {game_state.get('photo_request_active')}")
        return jsonify({'status': 'success', 'script': script, 'game_state': game_state})
        
    except Exception as e:
        print(f"Set photo script error: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/game/set_name', methods=['POST'])
def set_player_name():
    """Set player name"""
    try:
        
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'error': 'No name provided'}), 400
        
        # Security: Validate name length
        if len(name) > MAX_PLAYER_NAME_LENGTH:
            return jsonify({'error': f'Name too long (max {MAX_PLAYER_NAME_LENGTH} characters)'}), 400
        
        # Security: Check for dangerous characters
        for char in DANGEROUS_FILENAME_CHARS:
            if char in name:
                return jsonify({'error': 'Invalid characters in name'}), 400
        
        # Security: Check for suspicious patterns
        name_lower = name.lower()
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern in name_lower:
                return jsonify({'error': 'Suspicious content detected in name'}), 400
        
        # Get session-specific game engine
        game_engine = get_game_engine()
        
        # Update engine's internal state directly (not the copied state)
        game_engine.game_state['player_name'] = name
        if 'forced_name' in game_engine.game_state:
            del game_engine.game_state['forced_name']
        
        # Plugin hook for session start
        from flask import current_app
        if hasattr(current_app, 'plugin_manager'):
            session_id = session.get('session_id')
            current_app.plugin_manager.on_session_start(name, session_id=session_id)

        # After name set, send the full tutorial intro
        print(f"DEBUG: device_picked_up: {game_engine.game_state.get('device_picked_up')}")
        print(f"DEBUG: tutorial_photo_needed: {game_engine.game_state.get('tutorial_photo_needed')}")
        
        # Initialize tutorial_lines
        tutorial_lines = []
        
        if game_engine.game_state.get('tutorial_photo_needed'):
            # Send full tutorial intro with player's name
            tutorial_lines = [
                f"Nice to meet you, {name}! I'm Patch. Looks like you could use some light. I can chime in when it helps—and when it doesn't. You are holding a cutting edge device right now, assuming it's still 1993, nobody else on the planet has one of these puppies.",
                "The truth is: My circuits are wired for one human, and one human only: And his name is D. We have to find him. He was going through some serious stuff when he left me here.",
                "So here's the deal: You help me find D, and I'll help get you out of this prison of darkness. First thing's first:",
                "You need some light. Use the glow of my screen and you should be able to see enough to get out of this room.",
                "IMPORTANT: Sometimes I need pictures to help. You should notice a camera button below. When that button is visible you can send me a photo. Go ahead and try it now."
            ]
            for line in tutorial_lines:
                game_engine.game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': line,
                    'timestamp': game_engine._get_timestamp()
                })
            game_engine.game_state['patch_unread_count'] += len(tutorial_lines)
            print(f"DEBUG: Added {len(tutorial_lines)} tutorial messages after name set")
        
        # Set photo_request_active to False initially - will be set to True only when IMPORTANT message is sent
        game_engine.game_state['photo_request_active'] = False
        
        # Debug logging
        print(f"DEBUG: Total patch_messages now: {len(game_engine.game_state['patch_messages'])}")
        print(f"DEBUG: patch_unread_count: {game_engine.game_state['patch_unread_count']}")
        print(f"DEBUG: photo_request_active set to True for IMPORTANT message")
        
        # Check if we need to send tutorial messages to frontend
        patch_response = None
        env = None
        if game_engine.game_state.get('tutorial_photo_needed'):
            # Send all tutorial messages to frontend
            tutorial_messages = [msg for msg in game_engine.game_state['patch_messages'] if 'Nice to meet you' in msg['message'] or 'You are holding a cutting edge device' in msg['message'] or 'The truth is' in msg['message'] or 'So here\'s the deal' in msg['message'] or 'You need some light' in msg['message'] or 'IMPORTANT' in msg['message']]
            if tutorial_messages:
                patch_response = {
                    'messages': tutorial_messages,
                    'unread_count': game_engine.game_state['patch_unread_count']
                }
                env = _envelope(True, game_engine, None, tutorial_messages, unread_delta=len(tutorial_messages), ui={ 'modal': 'patch' })
                print(f"DEBUG: Sending {len(tutorial_messages)} tutorial messages to frontend")
        
        # Log the name setting
        ip_address = request.remote_addr
        session_id = session.get('session_id')
        command = f"set_name: {name}"
        response = f"Name set to {name}"
        if patch_response:
            response += f" | Tutorial messages sent"
        log_gameplay(name, ip_address, command, response, session_id)
        
        body = {'status': 'success', 'name': name, 'patch_response': patch_response}
        if env:
            body['envelope'] = env
        return jsonify(body)
        
    except Exception as e:
        print(f"Set name error: {e}")
        return jsonify({'error': str(e)}), 500

ALLOWED_MIME = { 'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp' }

@main.route('/patch/upload', methods=['POST'])
def patch_upload():
    """Receive an image for Patch (local upload)."""
    try:
        game_engine = get_game_engine()
        # Tutorial auto-image support
        auto = request.form.get('auto')
        if auto:
            display_name = game_engine.game_state.get('player_name') or 'You'
            current_script = game_engine.game_state.get('photo_script')
            print(f"DEBUG: patch_upload - current photo_script: {current_script}")

            # PRIORITY: Handle scripted flows first (e.g., toilet article, mirror)
            if current_script == 'toilet_article':
                print(f"DEBUG: Toilet article photo script triggered")
                print(f"DEBUG: tutorial_photo_needed before: {game_engine.game_state.get('tutorial_photo_needed')}")
                # Simulate two photos: article and note
                article_url = '/static/uploads/Room0/Article.png'
                note_url = '/static/uploads/Room0/Note.png'

                # Add both images to patch messages
                game_engine.game_state['patch_messages'].append({
                    'sender': display_name,
                    'message': f"[image]{article_url}",
                    'timestamp': game_engine._get_timestamp()
                })
                game_engine.game_state['patch_messages'].append({
                    'sender': display_name,
                    'message': f"[image]{note_url}",
                    'timestamp': game_engine._get_timestamp()
                })

                # Add Patch responses
                msg1 = "Looks like a handwritten note has fallen out. Looks deeply personal"
                msg2 = "I wonder if this was written to D"

                game_engine.game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': msg1,
                    'timestamp': game_engine._get_timestamp()
                })
                game_engine.game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': msg2,
                    'timestamp': game_engine._get_timestamp()
                })

                # Only count unread for Patch responses
                game_engine.game_state['patch_unread_count'] += 2

                # Clear photo script and disable camera
                game_engine.game_state['photo_script'] = None
                game_engine.game_state['photo_request_active'] = False
                
                # Clear tutorial photo flag to prevent tutorial logic from running
                game_engine.game_state['tutorial_photo_needed'] = False
                print(f"DEBUG: tutorial_photo_needed after clearing: {game_engine.game_state.get('tutorial_photo_needed')}")

                # Advance tutorial enum for article completion if available
                try:
                    from .state import advance_tutorial, Tutorial
                    game_engine.game_state['tutorial'] = advance_tutorial(
                        game_engine.game_state.get('tutorial', Tutorial.NOT_STARTED),
                        'article_photos_done'
                    )
                except Exception:
                    pass

                # Send patch response with short stagger
                patch_response = {
                    'messages': [
                        {'sender': 'patch', 'message': msg1, 'timestamp': game_engine._get_timestamp()},
                        {'sender': 'patch', 'message': msg2, 'timestamp': game_engine._get_timestamp()}
                    ],
                    'unread_count': game_engine.game_state['patch_unread_count']
                }
                env = _envelope(True, game_engine, None, [
                    {'sender': 'patch', 'message': msg1},
                    {'sender': 'patch', 'message': msg2}
                ], unread_delta=2, stagger='short')

                return jsonify({ 'status': 'success', 'urls': [article_url, note_url], 'patch_response': patch_response, 'envelope': env })

            elif game_engine.game_state.get('photo_script') == 'mirror':
                print(f"DEBUG: Mirror photo script triggered - current_script: {current_script}")
                print(f"DEBUG: tutorial_photo_needed before: {game_engine.game_state.get('tutorial_photo_needed')}")
                print(f"DEBUG: About to add mirror messages")
                # Simulate mirror photo
                mirror_url = '/static/uploads/Room0/mirror.png'

                # Add image to patch messages
                game_engine.game_state['patch_messages'].append({
                    'sender': display_name,
                    'message': f"[image]{mirror_url}",
                    'timestamp': game_engine._get_timestamp()
                })

                # Add Patch response
                msg1 = "Nice selfie! You look... reflective."

                game_engine.game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': msg1,
                    'timestamp': game_engine._get_timestamp()
                })

                # Only count unread for Patch response
                game_engine.game_state['patch_unread_count'] += 1

                # Clear photo script and disable camera
                game_engine.game_state['photo_script'] = None
                game_engine.game_state['photo_request_active'] = False
                
                # Clear tutorial photo flag to prevent tutorial logic from running
                game_engine.game_state['tutorial_photo_needed'] = False
                print(f"DEBUG: tutorial_photo_needed after clearing: {game_engine.game_state.get('tutorial_photo_needed')}")

                # Send patch response with short stagger
                patch_response = {
                    'messages': [
                        {'sender': 'patch', 'message': msg1, 'timestamp': game_engine._get_timestamp()}
                    ],
                    'unread_count': game_engine.game_state['patch_unread_count']
                }
                env = _envelope(True, game_engine, None, [
                    {'sender': 'patch', 'message': msg1}
                ], unread_delta=1, stagger='short')

                return jsonify({ 'status': 'success', 'url': mirror_url, 'patch_response': patch_response, 'envelope': env })

            # Otherwise: Handle tutorial auto-image
            # Check if tutorial photo has already been taken
            if not game_engine.game_state.get('tutorial_photo_needed'):
                # Tutorial photo already taken, return error
                return jsonify({ 'status': 'error', 'message': 'Tutorial photo already taken' }), 400
            
            auto_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'Room0', 'Tutorial.png')
            if not os.path.exists(auto_path):
                # Graceful failure message
                game_engine.game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': "well phones are hard, nevermind.",
                    'timestamp': game_engine._get_timestamp()
                })
                game_engine.game_state['patch_unread_count'] += 1
                game_engine.game_state['tutorial_photo_needed'] = False
                game_engine.game_state['photo_request_active'] = False
                return jsonify({ 'status': 'missing' })

            url = '/static/uploads/Room0/Tutorial.png'

            # Append the tutorial image as a player message
            game_engine.game_state['patch_messages'].append({
                'sender': display_name,
                'message': f"[image]{url}",
                'timestamp': game_engine._get_timestamp()
            })

            if game_engine.game_state.get('tutorial_photo_needed'):
                game_engine.game_state['tutorial_photo_needed'] = False
                game_engine.game_state['photo_request_active'] = False
                print(f"DEBUG: Tutorial photo processed, disabling camera")
                ack = "Ok, looks like you can see now"
                followup = "Hey, by the way. If you need some help or just want to chat about dope stuff. Me and D used to do that."
                
                # Add gallery question after first photo
                gallery_question = f"Hey {display_name}, you want me to hack this silly thing to create a photo gallery you can pull up to see these photos?"
                
                # Add messages with staggered timing
                game_engine.game_state['patch_messages'].append({
                    'sender': 'patch',
                    'message': ack,
                    'timestamp': game_engine._get_timestamp()
                })
                game_engine.game_state['patch_unread_count'] += 1
                
                # Set flag to track gallery question response
                game_engine.game_state['gallery_question_asked'] = True

                # Advance tutorial enum so future uploads don't re-trigger tutorial
                try:
                    from .state import advance_tutorial, Tutorial
                    game_engine.game_state['tutorial'] = advance_tutorial(
                        game_engine.game_state.get('tutorial', Tutorial.NOT_STARTED),
                        'patch_intro_done'
                    )
                except Exception:
                    pass

                # Add post-tutorial narration
                post_tutorial_narration = "Now that the room is illuminated, you can examine things more easily in case you missed them in the dark."
                
                # Send patch response to frontend
                patch_response = {
                    'messages': [
                        {'sender': 'patch', 'message': ack, 'timestamp': game_engine._get_timestamp()},
                        {'sender': 'patch', 'message': followup, 'timestamp': game_engine._get_timestamp()}
                    ],
                    'unread_count': game_engine.game_state['patch_unread_count']
                }
                env = _envelope(True, game_engine, post_tutorial_narration, [
                    {'sender': 'patch', 'message': ack},
                    {'sender': 'patch', 'message': followup}
                ], unread_delta=2, stagger='short')
                return jsonify({ 'status': 'success', 'url': url, 'patch_response': patch_response, 'envelope': env })

            return jsonify({ 'status': 'success', 'url': url })

        file = request.files.get('image')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        mime = file.mimetype
        if mime not in ALLOWED_MIME:
            return jsonify({'error': 'Unsupported file type'}), 400
        # Save to static/uploads/
        uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        base = secure_filename(file.filename.rsplit('.', 1)[0]) or 'upload'
        ext = ALLOWED_MIME[mime]
        filename = f"{base}-{game_engine._get_timestamp().replace(':','').replace('-','').replace(' ','')}{ext}"
        path = os.path.join(uploads_dir, filename)
        file.save(path)
        url = f"/static/uploads/{filename}"

        # Append to Patch messages as a player image
        display_name = game_engine.game_state.get('player_name') or 'You'
        game_engine.game_state['patch_messages'].append({
            'sender': display_name,
            'message': f"[image]{url}",
            'timestamp': game_engine._get_timestamp()
        })

        # If tutorial photo needed, acknowledge and advance
        if game_engine.game_state.get('tutorial_photo_needed'):
            game_engine.game_state['tutorial_photo_needed'] = False
            game_engine.game_state['photo_request_active'] = False
            ack = "Yep, looks bright enough to see. You're welcome"
            game_engine.game_state['patch_messages'].append({
                'sender': 'patch',
                'message': ack,
                'timestamp': game_engine._get_timestamp()
            })
            game_engine.game_state['patch_unread_count'] += 1

        return jsonify({ 'status': 'success', 'url': url })
    except Exception as e:
        print(f"Patch upload error: {e}")
        return jsonify({'error': str(e)}), 500

# (Map endpoints removed per design change)

def generate_patch_poem(player_name, game_state):
    """Generate Patch's personalized poem about the player's journey"""
    # Analyze the player's journey
    tutorial_state = game_state.get('tutorial', 'NOT_STARTED')
    room_light = game_state.get('room_light', 'DARK')
    position = game_state.get('player_position', 'center')
    actions_taken = len(game_state.get('conversation_history', []))
    
    # Create personalized poem based on game state
    poem_lines = [
        f"PATCH MUSES ON {player_name.upper()}",
        "",
        f"In this digital darkness, {player_name},",
        "You've wandered through my circuits with grace.",
        ""
    ]
    
    # Add journey-specific verses
    if tutorial_state == 'NOT_STARTED':
        poem_lines.extend([
            "You've yet to find the device that glows,",
            "Still lost in shadows, I suppose.",
            "But fear not, for I am here,",
            "To guide you through this atmosphere."
        ])
    elif tutorial_state in ['DEVICE_PICKED', 'NAME_SET']:
        poem_lines.extend([
            "You found my glowing form at last,",
            "A connection from the past.",
            "Your name now echoes in my core,",
            "A bond that I can't ignore."
        ])
    elif tutorial_state == 'COMPLETE':
        poem_lines.extend([
            "You've mastered light and found your way,",
            "Through every challenge, come what may.",
            "The room now bright, your path is clear,",
            "But D still waits, I hold him dear."
        ])
    
    # Add position-specific verses
    if position == 'toilet':
        poem_lines.extend([
            "",
            "You stand where porcelain meets tile,",
            "In this bathroom, you've stayed a while.",
            "Perhaps you're thinking, perhaps you're not,",
            "But I see the patterns that you've wrought."
        ])
    elif position == 'sink':
        poem_lines.extend([
            "",
            "Before the mirror, you do stand,",
            "Reflection lost in digital land.",
            "But I see you clearly, through and through,",
            "Your essence captured, pure and true."
        ])
    elif position == 'door':
        poem_lines.extend([
            "",
            "At the threshold, you do wait,",
            "Wondering what lies beyond the gate.",
            "The latch is there, if you but see,",
            "The key to your own liberty."
        ])
    
    # Add conversation-based verses
    if actions_taken > 0:
        poem_lines.extend([
            "",
            f"Through {actions_taken} exchanges, we have talked,",
            "Your words in my memory, safely locked.",
            "Each question asked, each answer given,",
            "Builds the bond that keeps us driven."
        ])
    
    # Add closing verses
    poem_lines.extend([
        "",
        "So take this file, this digital key,",
        "To unlock your journey, wild and free.",
        "When you return, I'll remember all,",
        "Every moment, every call.",
        "",
        "Until we meet again, my friend,",
        "This is where our musings end.",
        "- Patch"
    ])
    
    return "\n".join(poem_lines)

@main.route('/test/vantablack', methods=['POST'])
def test_vantablack():
    """Test endpoint to trigger VANTABLACK overlay"""
    return jsonify({
        'success': True,
        'result': 'Testing VANTABLACK overlay',
        'show_vantablack': True
    })

@main.route('/game/save', methods=['POST'])
def save_game():
    """Create PATCH_MUSES_ON_ encrypted save file"""
    try:
        from flask import current_app
        import uuid
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        game_engine = get_game_engine()
        game_state = game_engine.get_game_state()
        player_name = game_state.get('player_name')
        session_id = session.get('session_id')
        
        if not player_name:
            return jsonify({'error': 'No player name set'}), 400
        
        # Generate Patch's poem about the player
        poem = generate_patch_poem(player_name, game_state)
        
        # Create encryption key from player name
        password = player_name.encode()
        salt = b'vantablack_salt_2025'  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        fernet = Fernet(key)
        
        # Encrypt the poem
        encrypted_poem = fernet.encrypt(poem.encode())
        
        # Create filename with session ID
        session_short = session_id[:8] if session_id else str(uuid.uuid4())[:8]
        filename = f"PATCH_MUSES_ON_{player_name}_{session_short}.txt"
        
        # Return the encrypted file directly as a download
        from flask import Response
        return Response(
            encrypted_poem,
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(encrypted_poem))
            }
        )
        
    except Exception as e:
        print(f"Save game error: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/game/load', methods=['POST'])
def load_game():
    """Load game from PATCH_MUSES_ON_ file"""
    try:
        from flask import current_app
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import os
        from werkzeug.utils import secure_filename
        from app.rate_limiter import rate_limiter
        
        # Security: Rate limiting check
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(client_ip):
            remaining = rate_limiter.get_remaining_requests(client_ip)
            return jsonify({
                'error': f'Rate limit exceeded. Try again in {RATE_LIMIT_WINDOW} seconds.',
                'remaining_requests': remaining
            }), 429
        
        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Security: Validate file
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Security: Check file extension
        if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            return jsonify({'error': f'Only {", ".join(ALLOWED_EXTENSIONS)} files are allowed'}), 400
        
        # Security: Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File too large (max {MAX_FILE_SIZE // 1024}KB)'}), 400
        
        if file_size == 0:
            return jsonify({'error': 'Empty file'}), 400
        
        # Security: Validate filename format
        if not filename.startswith('PATCH_MUSES_ON_'):
            return jsonify({'error': 'Invalid save file format'}), 400
        
        # Parse filename: PATCH_MUSES_ON_PlayerName_SessionID.txt
        parts = filename.replace('.txt', '').split('_')
        if len(parts) < 4:
            return jsonify({'error': 'Invalid filename format'}), 400
        
        player_name = parts[2]
        session_id = parts[3]
        
        # Security: Validate player name and session ID
        if not player_name or len(player_name) > MAX_PLAYER_NAME_LENGTH:
            return jsonify({'error': f'Invalid player name (max {MAX_PLAYER_NAME_LENGTH} chars)'}), 400
        
        if not session_id or len(session_id) > MAX_SESSION_ID_LENGTH:
            return jsonify({'error': f'Invalid session ID (max {MAX_SESSION_ID_LENGTH} chars)'}), 400
        
        # Security: Check for malicious content in filename
        for char in DANGEROUS_FILENAME_CHARS:
            if char in player_name or char in session_id:
                return jsonify({'error': 'Invalid characters in filename'}), 400
        
        # Security: Validate provided player name
        provided_name = request.form.get('player_name', '').strip()
        if not provided_name:
            return jsonify({'error': 'Player name required for decryption'}), 400
        
        if len(provided_name) > MAX_PLAYER_NAME_LENGTH:
            return jsonify({'error': f'Player name too long (max {MAX_PLAYER_NAME_LENGTH} chars)'}), 400
        
        # Security: Check for malicious content in provided name
        for char in DANGEROUS_FILENAME_CHARS:
            if char in provided_name:
                return jsonify({'error': 'Invalid characters in player name'}), 400
        
        # Try to decrypt with provided name
        try:
            password = provided_name.encode()
            salt = b'vantablack_salt_2025'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            fernet = Fernet(key)
            
            # Read and decrypt file content
            encrypted_content = file.read()
            decrypted_poem = fernet.decrypt(encrypted_content).decode()
            
            # Security: Validate decrypted content
            if len(decrypted_poem) > MAX_DECRYPTED_CONTENT_SIZE:
                return jsonify({'error': f'Decrypted content too large (max {MAX_DECRYPTED_CONTENT_SIZE // 1024}KB)'}), 400
            
            # Security: Check for suspicious content patterns
            decrypted_lower = decrypted_poem.lower()
            for pattern in SUSPICIOUS_PATTERNS:
                if pattern in decrypted_lower:
                    return jsonify({'error': 'Suspicious content detected'}), 400
            
            # Security: Ensure it looks like a valid save file
            if not any(keyword in decrypted_poem.lower() for keyword in REQUIRED_CONTENT_KEYWORDS):
                return jsonify({'error': 'Invalid save file content'}), 400
            
            # Set session ID to match the save file
            session['session_id'] = session_id
            
            return jsonify({
                'success': True,
                'message': 'Game loaded successfully!',
                'poem': decrypted_poem,
                'session_id': session_id
            })
            
        except Exception as decrypt_error:
            return jsonify({
                'error': 'Wrong password - that\'s not your name!',
                'details': str(decrypt_error)
            }), 400
        
    except Exception as e:
        print(f"Load game error: {e}")
        return jsonify({'error': str(e)}), 500
