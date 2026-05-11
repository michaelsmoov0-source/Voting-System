import logging
import logging.config
import json
import os
from datetime import datetime
from django.conf import settings


class SafeJSONFormatter(logging.Formatter):
    """Custom JSON formatter that handles objects safely"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module if hasattr(record, 'module') else 'unknown',
            'message': record.getMessage(),
            'process_id': record.process,
            'thread_id': record.thread,
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Handle exception info
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class SafeStringFormatter(logging.Formatter):
    """Custom string formatter that handles objects safely"""
    
    def format(self, record):
        try:
            # Get message and ensure it's a string
            message = record.getMessage()
            if not isinstance(message, str):
                try:
                    message = str(message)
                except Exception:
                    message = f"[Object of type {type(record.msg).__name__}]"
            
            # Safely get module name
            module = getattr(record, 'module', 'unknown')
            if not isinstance(module, str):
                module = str(module)
            
            # Format with safe string conversion
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            return f"{record.levelname} {timestamp} {module} {record.process} {record.thread} {message}"
            
        except Exception as e:
            # Ultimate fallback
            return f"LOG_ERROR {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Unable to format log record: {str(e)}"


def get_safe_logging_config():
    """Get logging configuration that prevents [object Object] errors"""
    
    base_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'safe_json': {
                '()': 'voting.logging_config.SafeJSONFormatter',
            },
            'safe_string': {
                '()': 'voting.logging_config.SafeStringFormatter',
            },
            'simple': {
                'format': '%(levelname)s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': os.getenv('LOG_FILE', '/tmp/django.log'),
                'formatter': 'safe_json' if os.getenv('VERCEL') else 'safe_string',
                'encoding': 'utf-8',
            },
            'security': {
                'level': 'WARNING',
                'class': 'logging.FileHandler',
                'filename': os.getenv('SECURITY_LOG_FILE', '/tmp/security.log'),
                'formatter': 'safe_json',
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'voting': {
                'handlers': ['console', 'file', 'security'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'security': {
                'handlers': ['security'],
                'level': 'WARNING',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    }
    
    return base_config


def configure_logging():
    """Configure logging with safe formatters"""
    logging.config.dictConfig(get_safe_logging_config())


# Monkey patch to prevent object serialization issues
def safe_log_record_factory(*args, **kwargs):
    """Factory function that creates safe log records"""
    record = logging.LogRecord(*args, **kwargs)
    
    # Ensure message is string
    if not isinstance(record.getMessage(), str):
        try:
            record.msg = str(record.msg)
        except Exception:
            record.msg = f"[Object of type {type(record.msg).__name__}]"
    
    return record


# Apply safe logging
logging.setLogRecordFactory(safe_log_record_factory)
