import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Production settings for Vercel
if os.getenv("VERCEL"):
    DEBUG = False
    ALLOWED_HOSTS = [
        "voting-system-tbti.vercel.app",
        "*.vercel.app", 
        "localhost", 
        "127.0.0.1"
    ]
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    # For monorepo, we need to allow the same origin
    CORS_ALLOWED_ORIGINS = ["https://*.vercel.app", "http://localhost:3000", "http://localhost:5173"]
else:
    DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
    ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if host.strip()]
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_BROWSER_XSS_FILTER = False
    X_FRAME_OPTIONS = 'SAMEORIGIN'

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "voting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "voting.middleware.RateLimitMiddleware",
    "voting.middleware.SecurityLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=0, ssl_require=True)
    }
else:
    # Production: Use PostgreSQL on Vercel, Development: Use PostgreSQL locally
    if os.getenv("VERCEL"):
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DB_NAME", ""),
                "USER": os.getenv("DB_USER", ""),
                "PASSWORD": os.getenv("DB_PASSWORD", ""),
                "HOST": os.getenv("DB_HOST", ""),
                "PORT": os.getenv("DB_PORT", "5432"),
                "OPTIONS": {
                    "sslmode": "require",
                }
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DB_NAME", ""),
                "USER": os.getenv("DB_USER", ""),
                "PASSWORD": os.getenv("DB_PASSWORD", ""),
                "HOST": os.getenv("DB_HOST", ""),
                "PORT": os.getenv("DB_PORT", "5432"),
                "OPTIONS": {
                    "sslmode": "require",
                }
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Production caching configuration
if os.getenv("VERCEL"):
    # Production - Use Redis or Memcached if available, fallback to file-based caching
    REDIS_URL = os.getenv("REDIS_URL", "")
    if REDIS_URL:
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": REDIS_URL,
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "SOCKET_CONNECT_TIMEOUT": 5,
                    "SOCKET_TIMEOUT": 5,
                    "RETRY_ON_TIMEOUT": True,
                    "MAX_CONNECTIONS": 50,
                },
                "KEY_PREFIX": "voting_system",
                "TIMEOUT": 300,  # 5 minutes default
            }
        }
    else:
        # Fallback to file-based caching for production
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
                "LOCATION": "/tmp/django_cache",
                "TIMEOUT": 300,  # 5 minutes default
                "OPTIONS": {
                    "MAX_ENTRIES": 1000,
                    "CULL_FREQUENCY": 3,
                }
            }
        }
else:
    # Development - Use local memory caching
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "voting-system-cache",
            "TIMEOUT": 300,  # 5 minutes default
        }
    }

# Session configuration
if os.getenv("VERCEL"):
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
    SESSION_COOKIE_AGE = 3600  # 1 hour
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
    SESSION_COOKIE_AGE = 86400  # 24 hours
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False

# Production logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.getenv("LOG_FILE", "/tmp/django.log"),
            "formatter": "json" if os.getenv("VERCEL") else "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "security": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": os.getenv("SECURITY_LOG_FILE", "/tmp/security.log"),
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "voting": {
            "handlers": ["console", "file", "security"],
            "level": "DEBUG",
            "propagate": False,
        },
        "security": {
            "handlers": ["security"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Election Results Encryption
ENCRYPT_ELECTION_RESULTS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "voting.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
ADMIN_INVITE_KEY = os.getenv("ADMIN_INVITE_KEY", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
VERCEL="true"
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "candidate-images")
CANDIDATE_RETENTION_DAYS = int(os.getenv("CANDIDATE_RETENTION_DAYS", "2"))
MFA_CODE_INTERVAL_SECONDS = int(os.getenv("MFA_CODE_INTERVAL_SECONDS", "30"))
MFA_PREAUTH_MAX_AGE_SECONDS = int(os.getenv("MFA_PREAUTH_MAX_AGE_SECONDS", "345600"))  # 4 days = 4 * 24 * 60 * 60
ADMIN_MFA_REVERIFY_HOURS = int(os.getenv("ADMIN_MFA_REVERIFY_HOURS", "0"))  # Require MFA every login

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@votingsystem.local")
