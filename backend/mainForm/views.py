import redis
import json
import logging
import hashlib
import secrets
from .models import User
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone  # Add this import
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from .serializers import UserSerializer
from .tasks import check_user_task, update_presence
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

# --- Redis Connection Pool Setup ---
pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=10,
    decode_responses=True,
    socket_connect_timeout=5,  # Connection timeout
    socket_timeout=5,          # Read/write timeout
    retry_on_timeout=True
)

class SecureAnonRateThrottle(AnonRateThrottle):
    """Custom throttling for anonymous users"""
    scope = 'anon_user_creation'

class UserCreateAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SecureAnonRateThrottle]
    
    @method_decorator(never_cache)  # Prevent caching sensitive operations
    def post(self, request, *args, **kwargs):
        # Enhanced logging
        logger.info(f"User creation attempt from IP: {self.get_client_ip(request)}")
        
        try:
            redis_conn = redis.Redis(connection_pool=pool)
            
            # Enhanced idempotency key validation
            idempotency_key = request.headers.get('Idempotency-Key')
            if not idempotency_key or not self.is_valid_idempotency_key(idempotency_key):
                logger.warning(f"Invalid idempotency key from IP: {self.get_client_ip(request)}")
                return Response(
                    {"error": "Valid Idempotency-Key header is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Hash the idempotency key for security
            hashed_key = self.hash_idempotency_key(idempotency_key)
            lock_key = f"lock:idempotency:{hashed_key}"
            result_key = f"idempotency:result:{hashed_key}"
            
            # Lock the connection with an idempotency key
            with redis_conn.lock(lock_key, timeout=10):
                stored_result = redis_conn.get(result_key)
                if stored_result:
                    logger.info("Returning cached result for idempotency key")
                    try:
                        cached_data = json.loads(stored_result)
                        return Response(cached_data, status=status.HTTP_200_OK)
                    except json.JSONDecodeError:
                        logger.error("Failed to decode cached result")
                        redis_conn.delete(result_key)  # Clean up corrupted cache
                
                # Input validation with serializer
                serializer = UserSerializer(data=request.data)
                try:
                    serializer.is_valid(raise_exception=True)
                except Exception as e:
                    logger.warning(f"Validation failed from IP {self.get_client_ip(request)}: {str(e)}")
                    return Response(
                        {"error": "Invalid input data", "details": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Queue the task
                transaction.on_commit(
                    lambda: check_user_task.delay(
                        serializer.validated_data,
                        client_ip=self.get_client_ip(request)
                    )
                )
                
                # This is the dictionary that should be returned
                response_data = {
                    "message": "User creation request has been accepted and is being processed.",
                    "request_id": secrets.token_urlsafe(16)  # Tracking ID
                }

                # Store the result in Redis for idempotency
                redis_conn.set(result_key, json.dumps(response_data), ex=1800)  # 30 minutes
                
                logger.info(f"User creation queued successfully from IP: {self.get_client_ip(request)}")

                # This line MUST return `response_data`
                return Response(response_data, status=status.HTTP_202_ACCEPTED)
                
        except redis.RedisError as e:
            logger.error(f"Redis error in user creation: {str(e)}")
            return Response(
                {"error": "Service temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error in user creation: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        """Get real client IP, handling proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_valid_idempotency_key(self, key):
        """Validate idempotency key format and length"""
        if not key or len(key) < 10 or len(key) > 255:
            return False
        # Check for reasonable characters (alphanumeric + some symbols)
        import re
        return bool(re.match(r'^[a-zA-Z0-9\-_\.]+$', key))
    
    def hash_idempotency_key(self, key):
        """Hash idempotency key for security"""
        return hashlib.sha256(key.encode()).hexdigest()


class UserCheckInRateThrottle(AnonRateThrottle):
    """Specific throttling for check-in operations"""
    scope = 'user_checkin'


class UserCheckInAPIView(APIView):
    """
    API view to handle user check-in via QR code token.
    Uses PATCH for a partial update of the user's presence.
    """
    permission_classes = [AllowAny]
    throttle_classes = [UserCheckInRateThrottle]
    
    @method_decorator(never_cache)
    def patch(self, request, token, *args, **kwargs):
        # Enhanced logging
        logger.info(f"Check-in attempt from IP: {self.get_client_ip(request)} for token: {token[:8]}...")
        
        try:
            # Basic token presence check
            if not token:
                logger.warning(f"Missing token from IP: {self.get_client_ip(request)}")
                return Response(
                    {"error": "Token is required in the URL."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            redis_conn = redis.Redis(connection_pool=pool)
            
            # Rate limiting per token
            rate_limit_key = f"rate_limit:checkin:{token}"
            current_attempts = redis_conn.get(rate_limit_key)
            if current_attempts and int(current_attempts) >= 5:  # 5 attempts per minute
                logger.warning(f"Rate limit exceeded for token {token[:8]}... from IP: {self.get_client_ip(request)}")
                return Response(
                    {"error": "Too many check-in attempts. Please wait."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Increment rate limit counter
            redis_conn.incr(rate_limit_key)
            redis_conn.expire(rate_limit_key, 60)  # Reset after 1 minute
            
            lock_key = f"lock:check-in:{token}"
            with redis_conn.lock(lock_key, timeout=10):
                try:
                    user = User.objects.select_for_update().get(token=token)
                except User.DoesNotExist:
                    logger.warning(f"Invalid token {token[:8]}... from IP: {self.get_client_ip(request)}")
                    return Response(
                        {"error": "Invalid token. User not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                if user.presence:
                    logger.info(f"User {user.name} already checked in from IP: {self.get_client_ip(request)}")
                    return Response(
                        {"message": "User already checked in.", "user": user.name},
                        status=status.HTTP_200_OK
                    )
                
                # Send task to Celery with additional context
                update_presence.delay(
                    user.id,
                    client_ip=self.get_client_ip(request),
                    timestamp=timezone.now().isoformat()
                )
                
                logger.info(f"Check-in successful for user {user.name} from IP: {self.get_client_ip(request)}")
                return Response(
                    {"message": "Check-in successful.", "user": user.name},
                    status=status.HTTP_200_OK
                )
                
        except redis.RedisError as e:
            logger.error(f"Redis error in check-in: {str(e)}")
            return Response(
                {"error": "Service temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error in check-in: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        """Get real client IP, handling proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip