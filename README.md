# Vantablack - Interactive Narrative Game

A text-based adventure game with AI-powered narration and Patch, the sentient narrator.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root with:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=vantablack-secret-key-change-in-production
   ```

3. **Run the game:**
   ```bash
   python run.py
   ```

4. **Access the game:**
   Open your browser to `http://localhost:5001`

## How to Play

### Three-Input System

- **DO:** Physical actions (flush toilet, pick up device, examine door)
- **SAY:** Speak aloud (Patch may respond if you're trying to communicate)
- **PATCH:** Direct chat with Patch, the AI narrator

### Game Flow

1. **Start in darkness** - You can't see anything
2. **Feel around** - Find the toilet, sink, door
3. **Flush the toilet** - This lights up the Patch device
4. **Pick up the device** - Now you have light and can see the room
5. **Examine the door** - Find the latch
6. **Unlatch and open** - Exit to Room 1 (coming soon!)

### Patch Features

- **Notification system** - Red badge shows unread messages
- **Auto-open** - First message opens automatically
- **Full chat history** - Scrollable conversation
- **Witty personality** - Sarcastic but helpful AI narrator

## Development

The game is built with:
- Flask (web framework)
- OpenAI API (AI narration and Patch personality)
- HTML/CSS/JavaScript (frontend)
- JSON configuration (room data)

## Room 0 Specifications

- **Dark bathroom** with toilet, sink, and red door
- **Patch device** that lights up after flushing toilet
- **Position tracking** (center, at_toilet, at_sink, at_door)
- **State progression** (dark → device_lit → room_lit)
- **Door latch** revealed only when room is lit

## Future Features

- Audio system (ambient music, sound effects)
- Room 1 and beyond
- Album integration
- Save/load system

