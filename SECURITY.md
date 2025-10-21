# VantablackGame Security Measures

## File Upload Security

The PATCH_MUSES_ON_ save system includes multiple layers of security to prevent malicious file uploads:

### 1. File Type Validation
- **Only .txt files allowed**: Prevents executable file uploads
- **Filename sanitization**: Uses `secure_filename()` to prevent path traversal
- **Extension whitelist**: Only specific extensions are permitted

### 2. File Size Limits
- **Upload limit**: Maximum 1MB per file
- **Decrypted content limit**: Maximum 10KB after decryption
- **Empty file detection**: Rejects zero-byte files

### 3. Content Validation
- **Filename format**: Must match `PATCH_MUSES_ON_PlayerName_SessionID.txt`
- **Character restrictions**: Blocks dangerous characters (`..`, `/`, `\`, `<`, `>`, etc.)
- **Length limits**: Player names max 50 chars, session IDs max 20 chars
- **Content scanning**: Detects and blocks suspicious patterns (JavaScript, HTML, etc.)
- **Consistent validation**: Same security rules apply to initial name entry and save file loading

### 4. Rate Limiting
- **Request limit**: Maximum 10 requests per minute per IP
- **Sliding window**: Uses time-based rate limiting
- **Automatic cleanup**: Old requests are automatically removed

### 5. Encryption Security
- **Strong encryption**: Uses PBKDF2 with 100,000 iterations
- **Fixed salt**: Prevents rainbow table attacks
- **Fernet encryption**: Authenticated encryption prevents tampering
- **Password-based**: Uses player name as decryption key

### 6. Content Validation
- **Required keywords**: Must contain game-related content
- **Pattern detection**: Blocks script injection attempts
- **Size validation**: Prevents oversized content attacks

## Security Configuration

All security settings are centralized in `config/security.py`:

```python
MAX_FILE_SIZE = 1024 * 1024  # 1MB
ALLOWED_EXTENSIONS = {'.txt'}
MAX_DECRYPTED_CONTENT_SIZE = 10 * 1024  # 10KB
RATE_LIMIT_REQUESTS = 10  # Max requests per minute
RATE_LIMIT_WINDOW = 60  # Time window in seconds
```

## Attack Prevention

### Path Traversal
- ✅ **Prevented**: `secure_filename()` sanitizes all filenames
- ✅ **Prevented**: Character filtering blocks `../` patterns

### Script Injection
- ✅ **Prevented**: Content scanning blocks JavaScript/HTML patterns
- ✅ **Prevented**: Only .txt files allowed (no executable uploads)
- ✅ **Prevented**: Name validation blocks script injection in player names

### DoS Attacks
- ✅ **Prevented**: File size limits prevent large file uploads
- ✅ **Prevented**: Rate limiting prevents request flooding

### Data Exfiltration
- ✅ **Prevented**: Content validation ensures only game saves
- ✅ **Prevented**: Encryption prevents unauthorized access

### Input Validation
- ✅ **Prevented**: Consistent validation across all name entry points
- ✅ **Prevented**: Client-side validation provides immediate feedback
- ✅ **Prevented**: Server-side validation prevents bypassing client checks

## Monitoring

The system logs all security violations:
- Invalid file uploads
- Rate limit violations
- Suspicious content detection
- Failed decryption attempts

## Recommendations

1. **Production deployment**: Consider using Redis for rate limiting
2. **Logging**: Implement comprehensive security logging
3. **Monitoring**: Set up alerts for security violations
4. **Updates**: Regularly update security patterns and limits

## Security Headers

Consider adding security headers in production:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: default-src 'self'`
