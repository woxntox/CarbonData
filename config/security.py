# Security configuration for VantablackGame

# File upload security
MAX_FILE_SIZE = 1024 * 1024  # 1MB
ALLOWED_EXTENSIONS = {'.txt'}
MAX_DECRYPTED_CONTENT_SIZE = 10 * 1024  # 10KB

# Rate limiting (simple in-memory implementation)
RATE_LIMIT_REQUESTS = 10  # Max requests per minute per IP
RATE_LIMIT_WINDOW = 60  # Time window in seconds

# Content validation
SUSPICIOUS_PATTERNS = [
    '<script', 'javascript:', 'data:', 'vbscript:', 
    'onload=', 'onerror=', 'onclick=', 'onmouseover=',
    'eval(', 'Function(', 'setTimeout(', 'setInterval('
]

DANGEROUS_FILENAME_CHARS = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']

# Player name validation
MAX_PLAYER_NAME_LENGTH = 50
MAX_SESSION_ID_LENGTH = 20

# Required content keywords for valid save files
REQUIRED_CONTENT_KEYWORDS = ['patch', 'muses', 'player', 'game']
