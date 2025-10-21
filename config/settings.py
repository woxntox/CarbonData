# Feature flags for the relationship system
# Set to False to disable any component

# Core relationship system
RELATIONSHIP_SYSTEM_ENABLED = False  # Start disabled for safety

# Individual components
SESSION_TRACKING_ENABLED = False     # Track player actions and behavior
PERSONALITY_ANALYSIS_ENABLED = False  # Analyze player personality traits
MEMORY_SYSTEM_ENABLED = False        # Cross-session memory persistence
ENHANCED_RESPONSES_ENABLED = False   # Relationship-aware Patch responses

# Data storage settings
SESSION_DATA_DIR = "plugins/relationship/data/sessions"
PROFILE_DATA_DIR = "plugins/relationship/data/profiles"
MAX_SESSION_AGE_DAYS = 30  # Auto-cleanup old session data

# Performance settings
MAX_ACTIONS_PER_SESSION = 1000  # Prevent memory bloat
ANALYSIS_FREQUENCY = 5  # Analyze personality every N actions
