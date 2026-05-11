import os
import time
import logging
import hashlib
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security')


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware to prevent DDoS attacks and abuse"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        
        # Rate limits per endpoint
        self.rate_limits = {
            'login': {'requests': 5, 'window': 300},  # 5 requests per 5 minutes
            'register': {'requests': 3, 'window': 300},  # 3 requests per 5 minutes
            'vote': {'requests': 10, 'window': 3600},  # 10 requests per hour
            'mfa': {'requests': 10, 'window': 300},  # 10 requests per 5 minutes
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
        }
    
    def get_client_ip(self, request):
        """Get client IP address considering proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_rate_limit_key(self, ip, endpoint):
        """Generate cache key for rate limiting"""
        return f"rate_limit:{hashlib.md5(f'{ip}:{endpoint}'.encode()).hexdigest()}"
    
    def is_rate_limited(self, ip, endpoint):
        """Check if request should be rate limited"""
        limits = self.rate_limits.get(endpoint, self.rate_limits['default'])
        key = self.get_rate_limit_key(ip, endpoint)
        
        # Get current request count
        requests = cache.get(key, 0)
        
        if requests >= limits['requests']:
            return True
        
        # Increment request count
        cache.set(key, requests + 1, limits['window'])
        return False
    
    def process_request(self, request):
        """Process incoming request for rate limiting"""
        ip = self.get_client_ip(request)
        path = request.path.lower()
        
        # Determine endpoint type for rate limiting
        if '/api/auth/login' in path:
            endpoint = 'login'
        elif '/api/auth/register' in path:
            endpoint = 'register'
        elif '/api/votes' in path:
            endpoint = 'vote'
        elif '/api/auth/mfa' in path:
            endpoint = 'mfa'
        else:
            endpoint = 'default'
        
        # Check rate limit
        if self.is_rate_limited(ip, endpoint):
            logger.warning(f"Rate limit exceeded for IP: {ip}, endpoint: {endpoint}")
            return JsonResponse({
                'error': 'Rate limit exceeded. Please try again later.',
                'retry_after': self.rate_limits[endpoint]['window']
            }, status=429)
        
        return None


class SecurityLoggingMiddleware(MiddlewareMixin):
    """Security logging middleware for monitoring and audit trails"""
    
    def process_request(self, request):
        """Log incoming requests for security monitoring"""
        ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        method = request.method
        path = request.path
        
        # Log suspicious patterns
        suspicious_patterns = [
            'admin', 'test', 'scan', 'probe', 'hack', 'exploit',
            '../', 'select', 'drop', 'insert', 'update', 'delete'
        ]
        
        path_lower = path.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                logger.warning(f"Suspicious request pattern detected: {pattern} in {path} from {ip}")
                break
        
        # Log authentication attempts
        if '/api/auth/' in path_lower:
            logger.info(f"Auth attempt: {method} {path} from {ip} - {user_agent[:100]}")
    
    def process_response(self, request, response):
        """Log responses for security monitoring"""
        if response.status_code >= 400:
            ip = self.get_client_ip(request)
            logger.warning(f"Error response: {response.status_code} for {request.method} {request.path} from {ip}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address considering proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SimpleCORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = [
            origin.strip()
            for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
            if origin.strip()
        ]
        # Add Vercel frontend URL in production
        if os.getenv("VERCEL"):
            frontend_url = os.getenv("FRONTEND_URL", "")
            if frontend_url and frontend_url not in self.allowed_origins:
                self.allowed_origins.append(frontend_url)

    def __call__(self, request):
        origin = request.headers.get("Origin")
        origin_allowed = origin and ("*" in self.allowed_origins or origin in self.allowed_origins)
        if not origin_allowed and origin and settings.DEBUG and origin.startswith("http://localhost:"):
            origin_allowed = True
        if not origin_allowed and origin and settings.DEBUG and origin.startswith("http://127.0.0.1:"):
            origin_allowed = True
        # Allow Vercel frontend in production
        if not origin_allowed and origin and os.getenv("VERCEL") and origin.endswith(".vercel.app"):
            origin_allowed = True

        if request.method == "OPTIONS":
            response = HttpResponse(status=200)
            if origin_allowed:
                response["Access-Control-Allow-Origin"] = origin
                response["Vary"] = "Origin"
                response["Access-Control-Allow-Credentials"] = "true"
                response["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, X-Admin-Key, Accept, Origin"
                )
                response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
                response["Access-Control-Max-Age"] = "86400"
            return response

        response = self.get_response(request)

        if origin_allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Admin-Key, Accept, Origin"
            response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"

        return response
