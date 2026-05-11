import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db import DatabaseError
import traceback

logger = logging.getLogger('voting')


class VotingSystemException(Exception):
    """Base exception for voting system"""
    def __init__(self, message, error_code=None, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class ElectionNotActiveException(VotingSystemException):
    """Raised when trying to vote in an inactive election"""
    def __init__(self, election_title):
        message = f"Election '{election_title}' is not currently active for voting"
        super().__init__(message, error_code='ELECTION_NOT_ACTIVE', status_code=status.HTTP_400_BAD_REQUEST)


class VoterNotRegisteredException(VotingSystemException):
    """Raised when voter is not registered for an election"""
    def __init__(self):
        message = "You are not registered for this election"
        super().__init__(message, error_code='VOTER_NOT_REGISTERED', status_code=status.HTTP_403_FORBIDDEN)


class VoterAlreadyVotedException(VotingSystemException):
    """Raised when voter has already cast a vote"""
    def __init__(self):
        message = "You have already cast a vote for this election"
        super().__init__(message, error_code='VOTER_ALREADY_VOTED', status_code=status.HTTP_400_BAD_REQUEST)


class InvalidVoteException(VotingSystemException):
    """Raised when vote data is invalid"""
    def __init__(self, reason):
        message = f"Invalid vote: {reason}"
        super().__init__(message, error_code='INVALID_VOTE', status_code=status.HTTP_400_BAD_REQUEST)


class ElectionFullException(VotingSystemException):
    """Raised when election has reached maximum votes"""
    def __init__(self):
        message = "This election has reached its maximum number of votes"
        super().__init__(message, error_code='ELECTION_FULL', status_code=status.HTTP_400_BAD_REQUEST)


class MFANotEnabledException(VotingSystemException):
    """Raised when MFA is not enabled for admin user"""
    def __init__(self):
        message = "Multi-factor authentication is not enabled for this account"
        super().__init__(message, error_code='MFA_NOT_ENABLED', status_code=status.HTTP_403_FORBIDDEN)


class MFAVerificationFailedException(VotingSystemException):
    """Raised when MFA verification fails"""
    def __init__(self):
        message = "Invalid multi-factor authentication code"
        super().__init__(message, error_code='MFA_VERIFICATION_FAILED', status_code=status.HTTP_401_UNAUTHORIZED)


class RateLimitExceededException(VotingSystemException):
    """Raised when rate limit is exceeded"""
    def __init__(self, retry_after):
        message = f"Rate limit exceeded. Please try again in {retry_after} seconds"
        super().__init__(message, error_code='RATE_LIMIT_EXCEEDED', status_code=status.HTTP_429_TOO_MANY_REQUESTS)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for REST framework
    """
    # Log the exception
    logger.error(f"Exception occurred: {type(exc).__name__}: {str(exc)}")
    logger.error(f"Context: {context}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    # Handle custom exceptions
    if isinstance(exc, VotingSystemException):
        response_data = {
            'error': exc.message,
            'error_code': exc.error_code,
            'timestamp': context['request'].META.get('HTTP_X_REQUEST_TIME', 'unknown')
        }
        return Response(response_data, status=exc.status_code)

    # Handle Django validation errors
    if isinstance(exc, ValidationError):
        response_data = {
            'error': 'Validation failed',
            'details': dict(exc),
            'error_code': 'VALIDATION_ERROR'
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    # Handle database errors
    if isinstance(exc, DatabaseError):
        response_data = {
            'error': 'Database operation failed',
            'error_code': 'DATABASE_ERROR'
        }
        logger.error(f"Database error: {str(exc)}")
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Handle 404 errors
    if isinstance(exc, Http404):
        response_data = {
            'error': 'Resource not found',
            'error_code': 'NOT_FOUND'
        }
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    # Default exception handling
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the default response
        custom_response_data = {
            'error': 'An error occurred',
            'error_code': 'INTERNAL_ERROR',
            'details': response.data if hasattr(response, 'data') else None
        }
        response.data = custom_response_data
    
    return response


def validate_election_access(election, user, request_data=None):
    """
    Validate that user can access the election for voting
    """
    # Check if election is active
    if election.status != 'open':
        raise ElectionNotActiveException(election.title)
    
    # Check if election is within time bounds
    from django.utils import timezone
    now = timezone.now()
    if now < election.starts_at or now > election.ends_at:
        raise ElectionNotActiveException(election.title)
    
    # Check if election is full
    if election.max_votes is not None:
        from .models import Vote
        current_votes = Vote.objects.filter(election=election).count()
        if current_votes >= election.max_votes:
            raise ElectionFullException()
    
    # Check election password if required
    if election.requires_password:
        election_password = request_data.get('election_password', '') if request_data else ''
        if not election.check_access_password(election_password):
            raise InvalidVoteException("Invalid election access password")


def validate_voter_eligibility(election, username, request_data=None):
    """
    Validate that voter is eligible to vote in the election
    """
    # Check if user is registered (if registration is required)
    if election.registration_starts_at and election.registration_ends_at:
        if not election.is_registration_open:
            raise VoterNotRegisteredException()
        
        if not election.is_user_registered(username):
            raise VoterNotRegisteredException()
    
    # Check voter filter pattern
    if not election.user_can_vote(username):
        raise InvalidVoteException("You are not eligible to vote in this election based on the voter filter criteria")
    
    # Check if user has already voted
    import hashlib
    from .models import Vote
    voter_hash = hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()
    if Vote.objects.filter(election=election, voter_hash=voter_hash).exists():
        raise VoterAlreadyVotedException()


def log_security_event(event_type, details, request=None):
    """
    Log security-related events for audit purposes
    """
    security_logger = logging.getLogger('security')
    
    log_data = {
        'event_type': event_type,
        'details': details,
        'timestamp': timezone.now().isoformat(),
    }
    
    if request:
        log_data.update({
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
            'path': request.path,
            'method': request.method,
        })
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            log_data['user_id'] = request.user.id
            log_data['username'] = request.user.username
    
    security_logger.warning(f"Security event: {event_type} - {details}")


def get_client_ip(request):
    """
    Get client IP address considering proxies
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
