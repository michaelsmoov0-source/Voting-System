import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import psutil
import os

logger = logging.getLogger('voting')


@api_view(['GET'])
def health_check(request):
    """Comprehensive health check endpoint for monitoring"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0',
            'environment': 'production' if os.getenv('VERCEL') else 'development',
            'checks': {}
        }
        
        # Database connectivity check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        health_status['checks']['database'] = {
            'status': db_status,
            'connection_pool': get_connection_pool_info()
        }
        
        # Cache connectivity check
        try:
            cache.set('health_check', 'ok', 60)
            cache_result = cache.get('health_check')
            cache_status = 'healthy' if cache_result == 'ok' else 'unhealthy'
        except Exception as e:
            cache_status = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        health_status['checks']['cache'] = {'status': cache_status}
        
        # Memory usage check
        memory_info = psutil.virtual_memory()
        health_status['checks']['memory'] = {
            'status': 'healthy' if memory_info.percent < 85 else 'warning',
            'usage_percent': memory_info.percent,
            'available_gb': round(memory_info.available / (1024**3), 2)
        }
        
        # Disk space check
        disk_info = psutil.disk_usage('/')
        disk_percent = (disk_info.used / disk_info.total) * 100
        health_status['checks']['disk'] = {
            'status': 'healthy' if disk_percent < 85 else 'warning',
            'usage_percent': round(disk_percent, 2),
            'free_gb': round(disk_info.free / (1024**3), 2)
        }
        
        # Application-specific checks
        health_status['checks']['application'] = {
            'status': 'healthy',
            'debug_mode': settings.DEBUG,
            'secret_key_configured': bool(settings.SECRET_KEY),
            'database_configured': bool(settings.DATABASES)
        }
        
        response_status = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(health_status, status=response_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
def system_status(request):
    """Detailed system status endpoint for monitoring"""
    try:
        status_data = {
            'timestamp': timezone.now().isoformat(),
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                    'available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
                    'usage_percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
                    'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2),
                    'usage_percent': round((psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100, 2)
                }
            },
            'django': {
                'debug_mode': settings.DEBUG,
                'allowed_hosts': settings.ALLOWED_HOSTS,
                'database_engine': settings.DATABASES['default']['ENGINE'],
                'cache_backend': settings.CACHES['default']['BACKEND'] if hasattr(settings, 'CACHES') else 'default'
            },
            'application': {
                'active_elections': get_active_elections_count(),
                'total_votes': get_total_votes_count(),
                'registered_users': get_registered_users_count()
            }
        }
        
        return Response(status_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"System status check failed: {str(e)}")
        return Response({
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def readiness_check(request):
    """Readiness probe for Kubernetes/container orchestration"""
    try:
        # Check critical dependencies
        checks = {
            'database': check_database_readiness(),
            'cache': check_cache_readiness(),
            'configuration': check_configuration_readiness()
        }
        
        all_healthy = all(check['status'] == 'ready' for check in checks.values())
        
        response_data = {
            'status': 'ready' if all_healthy else 'not_ready',
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        }
        
        response_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(response_data, status=response_status)
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return Response({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def get_connection_pool_info():
    """Get database connection pool information"""
    try:
        # This is a simplified version - in production you might want to use
        # connection pool specific metrics
        return {
            'max_connections': 20,
            'min_connections': 5,
            'current_connections': len(connection.queries) if settings.DEBUG else 'unknown'
        }
    except Exception:
        return {'status': 'unknown'}


def get_active_elections_count():
    """Get count of active elections"""
    try:
        from .models import Election
        return Election.objects.filter(status='open').count()
    except Exception:
        return 0


def get_total_votes_count():
    """Get total votes count"""
    try:
        from .models import Vote
        return Vote.objects.count()
    except Exception:
        return 0


def get_registered_users_count():
    """Get registered users count"""
    try:
        from django.contrib.auth.models import User
        return User.objects.count()
    except Exception:
        return 0


def check_database_readiness():
    """Check database readiness"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return {'status': 'ready', 'response_time': 'fast'}
    except Exception as e:
        return {'status': 'not_ready', 'error': str(e)}


def check_cache_readiness():
    """Check cache readiness"""
    try:
        cache.set('readiness_check', 'ok', 10)
        result = cache.get('readiness_check')
        return {'status': 'ready' if result == 'ok' else 'not_ready'}
    except Exception as e:
        return {'status': 'not_ready', 'error': str(e)}


def check_configuration_readiness():
    """Check configuration readiness"""
    required_settings = ['SECRET_KEY', 'DATABASES']
    missing_settings = []
    
    for setting in required_settings:
        if not getattr(settings, setting, None):
            missing_settings.append(setting)
    
    if missing_settings:
        return {'status': 'not_ready', 'missing_settings': missing_settings}
    
    return {'status': 'ready'}
