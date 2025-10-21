"""
Simple in-memory rate limiter for VantablackGame
"""
import time
from collections import defaultdict, deque
from config.security import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

class RateLimiter:
    """Simple rate limiter using sliding window"""
    
    def __init__(self):
        self.requests = defaultdict(deque)
    
    def is_allowed(self, client_ip):
        """Check if request is allowed for given IP"""
        now = time.time()
        
        # Clean old requests outside the window
        while self.requests[client_ip] and self.requests[client_ip][0] <= now - RATE_LIMIT_WINDOW:
            self.requests[client_ip].popleft()
        
        # Check if under limit
        if len(self.requests[client_ip]) >= RATE_LIMIT_REQUESTS:
            return False
        
        # Add current request
        self.requests[client_ip].append(now)
        return True
    
    def get_remaining_requests(self, client_ip):
        """Get remaining requests for IP"""
        now = time.time()
        
        # Clean old requests
        while self.requests[client_ip] and self.requests[client_ip][0] <= now - RATE_LIMIT_WINDOW:
            self.requests[client_ip].popleft()
        
        return max(0, RATE_LIMIT_REQUESTS - len(self.requests[client_ip]))

# Global rate limiter instance
rate_limiter = RateLimiter()
