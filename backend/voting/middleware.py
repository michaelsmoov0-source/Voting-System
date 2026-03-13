import os

from django.conf import settings
from django.http import HttpResponse


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
