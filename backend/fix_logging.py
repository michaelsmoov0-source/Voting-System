#!/usr/bin/env python
"""
Quick script to fix [object Object] logging issues
Run this script to test and fix logging configuration
"""

import logging
import os
import sys
from django.conf import settings

def test_logging():
    """Test logging configuration"""
    print("Testing logging configuration...")
    
    # Test basic logging
    logger = logging.getLogger('voting')
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Test with object
    test_object = {"key": "value", "number": 42}
    logger.info(f"Testing object logging: {test_object}")
    
    print("Logging test completed. Check logs for [object Object] errors.")

def fix_logging_config():
    """Apply simple logging fix"""
    print("Applying simple logging configuration...")
    
    # Override logging with simple config
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(levelname)s %(asctime)s %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
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
                'filename': '/tmp/django_simple.log',
                'formatter': 'simple',
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
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    }
    
    # Apply configuration
    logging.config.dictConfig(LOGGING_CONFIG)
    print("Simple logging configuration applied.")

if __name__ == "__main__":
    # Set up Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        import django
        django.setup()
        
        # Test current logging
        test_logging()
        
        # Ask user if they want to apply fix
        response = input("Apply simple logging fix? (y/n): ").lower().strip()
        if response == 'y':
            fix_logging_config()
            print("Testing fixed logging...")
            test_logging()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Applying simple logging fix anyway...")
        fix_logging_config()
