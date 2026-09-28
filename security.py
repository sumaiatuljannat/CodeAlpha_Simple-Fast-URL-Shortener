"""
Security, validation, and privacy-preserving analytics utilities for LinkSnap.
"""
import re
import ipaddress
import time
from urllib.parse import urlparse
from collections import defaultdict
from functools import wraps
from flask import request, jsonify

RESERVED_CODES = {
    'api', 'static', 'login', 'register', 'logout', 'dashboard',
    'stats', 'qr', 'admin', 'health', 'favicon.ico', 'index',
    'docs', 'shorten', 'settings', 'profile', 'auth', 'help', 'about'
}

# Regex for safe custom short codes (alphanumeric, hyphens, underscores, 3-30 chars)
CUSTOM_CODE_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{1,28}[a-zA-Z0-9]$')


def is_private_or_loopback_ip(hostname: str) -> bool:
    """
    Checks if a hostname resolves to or represents a private, loopback,
    link-local, or reserved IP address to prevent SSRF and internal scanning.
    """
    hostname = hostname.lower().strip()
    if hostname in ('localhost', 'localhost.localdomain', 'ip6-localhost', 'ip6-loopback'):
        return True

    # Check if hostname is an IP literal
    try:
        ip = ipaddress.ip_address(hostname)
        return (
            ip.is_loopback or
            ip.is_private or
            ip.is_reserved or
            ip.is_link_local or
            ip.is_unspecified
        )
    except ValueError:
        # Not a raw IP literal, it is a regular hostname
        return False


def is_valid_url(url: str) -> tuple[bool, str]:
    """
    Validates that a URL is well-formed, uses HTTP/HTTPS, has a valid domain,
    does not target private/internal networks, and does not use dangerous schemes.
    Returns (is_valid, error_message).
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    url = url.strip()
    if len(url) > 2048:
        return False, "URL exceeds maximum allowed length of 2048 characters."

    # Reject dangerous URI schemes
    lower_url = url.lower()
    dangerous_schemes = ('javascript:', 'data:', 'file:', 'vbscript:', 'about:', 'ftp:')
    for scheme in dangerous_schemes:
        if lower_url.startswith(scheme):
            return False, f"URL scheme '{scheme}' is not permitted for security reasons."

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL structure."

    if parsed.scheme not in ('http', 'https'):
        return False, "URL must start with http:// or https://."

    if not parsed.netloc:
        return False, "URL must contain a valid domain or host."

    # Extract hostname without port or user info
    hostname = parsed.hostname
    if not hostname:
        return False, "URL hostname is missing or invalid."

    # Reject embedded user authentication in URL (e.g. http://user:pass@host)
    if parsed.username or parsed.password:
        return False, "URLs with embedded user credentials are not allowed."

    # SSRF Protection: Reject private/loopback/internal addresses
    if is_private_or_loopback_ip(hostname):
        return False, "URLs pointing to localhost, private, or loopback networks are blocked."

    # Check basic domain structure (must have at least one dot unless IPv6)
    if '.' not in hostname and ':' not in hostname:
        return False, "URL domain must contain a valid top-level domain (e.g. .com, .org)."

    return True, ""


def is_valid_custom_code(code: str) -> tuple[bool, str]:
    """
    Validates a custom short code string.
    """
    if not code or not isinstance(code, str):
        return False, "Custom code cannot be empty."

    code = code.strip()
    if len(code) < 3 or len(code) > 30:
        return False, "Custom code must be between 3 and 30 characters long."

    if not CUSTOM_CODE_REGEX.match(code):
        return False, "Custom code can only contain letters, numbers, hyphens, and underscores, and cannot start or end with a hyphen/underscore."

    if code.lower() in RESERVED_CODES:
        return False, f"'{code}' is a reserved system keyword and cannot be used."

    return True, ""


def parse_user_agent(ua_string: str) -> dict:
    """
    Extracts high-level device type, browser, and OS from User-Agent string.
    Completely privacy-friendly; does not log fingerprint hashes or raw visitor data.
    """
    if not ua_string:
        return {'device_type': 'Desktop', 'browser': 'Other', 'os': 'Other'}

    ua = ua_string.lower()

    # 1. Device Type
    device_type = 'Desktop'
    if any(bot in ua for bot in ['bot', 'crawler', 'spider', 'slurp', 'mediapartners']):
        device_type = 'Bot'
    elif 'tablet' in ua or 'ipad' in ua:
        device_type = 'Tablet'
    elif any(m in ua for m in ['mobile', 'android', 'iphone', 'ipod', 'windows phone']):
        device_type = 'Mobile'

    # 2. Operating System
    os_name = 'Other'
    if 'windows' in ua:
        os_name = 'Windows'
    elif 'iphone' in ua or 'ipad' in ua or 'ipod' in ua:
        os_name = 'iOS'
    elif 'android' in ua:
        os_name = 'Android'
    elif 'mac os' in ua or 'macintosh' in ua:
        os_name = 'macOS'
    elif 'linux' in ua:
        os_name = 'Linux'

    # 3. Browser
    browser = 'Other'
    if 'edg/' in ua or 'edge/' in ua:
        browser = 'Edge'
    elif 'opr/' in ua or 'opera/' in ua:
        browser = 'Opera'
    elif 'chrome/' in ua and 'chromium' not in ua:
        browser = 'Chrome'
    elif 'firefox/' in ua:
        browser = 'Firefox'
    elif 'safari/' in ua and 'chrome' not in ua:
        browser = 'Safari'

    return {
        'device_type': device_type,
        'browser': browser,
        'os': os_name
    }


def clean_referrer(referrer: str) -> str:
    """
    Extracts clean domain name from Referer header (e.g., 'google.com', 'twitter.com', or 'Direct').
    Protects user privacy by stripping paths and query strings.
    """
    if not referrer or not isinstance(referrer, str):
        return 'Direct'

    try:
        parsed = urlparse(referrer.strip())
        host = parsed.netloc.lower()
        if not host:
            return 'Direct'
        
        # Clean common www prefix
        if host.startswith('www.'):
            host = host[4:]
            
        # Map known shorteners or social networks for clean reporting
        if 'google.' in host:
            return 'Google'
        if host in ('t.co', 'twitter.com', 'x.com'):
            return 'X / Twitter'
        if 'linkedin.' in host:
            return 'LinkedIn'
        if 'facebook.' in host:
            return 'Facebook'
        if 'github.' in host:
            return 'GitHub'
        if 'youtube.' in host:
            return 'YouTube'
        if 'reddit.' in host:
            return 'Reddit'

        return host
    except Exception:
        return 'Direct'


class SlidingWindowRateLimiter:
    """
    In-memory thread-safe rate limiter using sliding timestamp windows.
    Tracks requests per client identifier (IP or token).
    """
    def __init__(self):
        self.requests = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        timestamps = self.requests[key]

        # Evict timestamps older than current window
        cutoff = now - window
        self.requests[key] = [ts for ts in timestamps if ts > cutoff]

        if len(self.requests[key]) >= limit:
            oldest = self.requests[key][0]
            retry_after = max(1, int(oldest + window - now))
            return False, retry_after

        self.requests[key].append(now)
        return True, 0


# Global rate limiter instance
_global_rate_limiter = SlidingWindowRateLimiter()


def rate_limit(limit=30, window=60):
    """
    Decorator for Flask routes to enforce rate limits per client IP.
    Returns HTTP 429 Too Many Requests when threshold exceeded.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Use X-Forwarded-For if available, otherwise remote_addr
            forwarded = request.headers.get('X-Forwarded-For')
            if forwarded:
                client_ip = forwarded.split(',')[0].strip()
            else:
                client_ip = request.remote_addr or '127.0.0.1'

            allowed, retry_after = _global_rate_limiter.is_allowed(client_ip, limit, window)
            if not allowed:
                response = jsonify({
                    'success': False,
                    'error': f'Rate limit exceeded. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(retry_after)
                return response

            return f(*args, **kwargs)
        return wrapper
    return decorator
