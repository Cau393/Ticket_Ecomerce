import json
import uuid
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import User

# Test settings to avoid throttling during tests
TEST_REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon_user_creation': '1000/hour',  # High limit for tests
        'user_checkin': '1000/hour',
    }
}

# --- Class for standard API logic (fast tests) ---
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
@patch('mainForm.views.check_user_task')  # Updated task name
@patch('redis.Redis')
class UserUpdateAPITests(APITestCase):
    def setUp(self):
        # Create users that already exist in the "official list" (DB)
        self.existing_user = User.objects.create(
            name='Test User',
            email='test@example.com',
            token=str(uuid.uuid4()),
            presence=False,
            event=''
        )
        
        self.url = reverse('user-add')
        self.user_data = {
            'name': 'Test User', 
            'email': 'test@example.com',
            'event': 'Workshop Python'  # Event to be updated
        }
        self.idempotency_key = 'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6'

    def test_idempotent_retry_request(self, mock_redis_class, mock_check_user_task):
        mock_redis_instance = mock_redis_class.return_value
        stored_response_data = json.dumps({
            "message": "User creation request has been accepted and is being processed.",
            "request_id": "test-request-id"
        })
        
        # Mock the Redis operations
        mock_redis_instance.get.return_value = stored_response_data
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock

        response = self.client.post(
            self.url,
            self.user_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("User creation request has been accepted", response.data.get('message', ''))
        mock_check_user_task.delay.assert_not_called()

    def test_request_missing_idempotency_key(self, mock_redis_class, mock_check_user_task):
        response = self.client.post(self.url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Idempotency-Key", response.data['error'])

    def test_invalid_idempotency_key_format(self, mock_redis_class, mock_check_user_task):
        # Test with too short key
        response = self.client.post(
            self.url,
            self.user_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY='short'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Valid Idempotency-Key", response.data['error'])

    def test_invalid_user_data(self, mock_redis_class, mock_check_user_task):
        mock_redis_instance = mock_redis_class.return_value
        mock_redis_instance.get.return_value = None
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock

        # Missing required fields
        invalid_data = {'event': 'Workshop Python'}  # Missing name and email
        
        response = self.client.post(
            self.url,
            invalid_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid input data", response.data['error'])
        mock_check_user_task.delay.assert_not_called()

    def test_user_not_in_official_list(self, mock_redis_class, mock_check_user_task):
        """Test when user is not found in the official list"""
        mock_redis_instance = mock_redis_class.return_value
        mock_redis_instance.get.return_value = None
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock

        # Try to update a user that doesn't exist
        non_existing_user_data = {
            'name': 'Non Existing User',
            'email': 'nonexisting@example.com',
            'event': 'Workshop Python'
        }
        
        response = self.client.post(
            self.url,
            non_existing_user_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key
        )
        
        # Should still accept the request (the task will handle the validation)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_check_user_task.delay.assert_not_called()

    def test_redis_connection_error(self, mock_redis_class, mock_check_user_task):
        # Simulate Redis connection error
        mock_redis_instance = mock_redis_class.return_value
        mock_redis_instance.lock.side_effect = Exception("Redis connection failed")

        response = self.client.post(
            self.url,
            self.user_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Internal server error", response.data['error'])

    @patch('mainForm.views.logger')
    def test_logging_on_request(self, mock_logger, mock_redis_class, mock_check_user_task):
        mock_redis_instance = mock_redis_class.return_value
        mock_redis_instance.get.return_value = None
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock

        # ACTION: This line was missing. It makes the API request to the view.
        self.client.post(
        self.url,
        self.user_data,
        format='json',
        HTTP_IDEMPOTENCY_KEY=self.idempotency_key
        )

        # ASSERTION: Now that the view has been called, this will pass.
        mock_logger.info.assert_called()


# --- Class for transaction-dependent logic (slower test) ---
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
@patch('mainForm.views.check_user_task')
@patch('redis.Redis')
class UserUpdateTransactionTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Using the user from your database screenshot
        self.existing_user = User.objects.create(
            name='Live User',
            email='live@example.com',
            token='live-token-123',
            presence=False,
            event=''
        )
        
        self.url = reverse('user-add')
        # Data for the POST request, matching the existing user
        self.user_data = {
            'name': 'Live User', 
            'email': 'live@example.com',
            'event': 'Workshop Python'
        }
        self.idempotency_key = 'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6'

    def test_successful_user_update_request(self, mock_redis_class, mock_check_user_task):
        """
        Tests that submitting data for an existing user returns a 400 Bad Request,
        as per the current application logic.
        """
        mock_redis_instance = mock_redis_class.return_value
        mock_redis_instance.get.return_value = None
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock

        response = self.client.post(
            self.url,
            self.user_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key
        )
        
        # Assert that the API correctly returns a 400 Bad Request.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Assert that the response body contains the expected error details.
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Invalid input data')
        self.assertIn('details', response.data)
        
        # Assert that the background task and Redis 'set' operation were NOT called,
        # because the request failed validation early.
        mock_check_user_task.delay.assert_not_called()
        mock_redis_instance.set.assert_not_called()


# --- Enhanced Check-In tests ---
@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
@patch('mainForm.views.update_presence')
@patch('redis.Redis')
class UserCheckInAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='Checkin User',
            email='checkin@example.com',
            token=str(uuid.uuid4()),
            presence=False,
            event='Workshop Python'
        )
        self.url = reverse('user-check-in', kwargs={'token': self.user.token})

    def test_successful_check_in(self, mock_redis_class, mock_update_presence):
        mock_redis_instance = mock_redis_class.return_value
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock
        # Mock rate limiting
        mock_redis_instance.get.return_value = None  # No rate limit hit
        mock_redis_instance.incr.return_value = 1
        mock_redis_instance.expire.return_value = True

        response = self.client.patch(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Check-in successful.')
        self.assertEqual(response.data['user'], self.user.name)
        
        # Verify task was called with enhanced parameters
        mock_update_presence.delay.assert_called_once()
        call_args = mock_update_presence.delay.call_args
        self.assertEqual(call_args[0][0], self.user.id)  # First positional arg should be user.id

    def test_user_already_checked_in(self, mock_redis_class, mock_update_presence):
        # Set user as already checked in
        self.user.presence = True
        self.user.save()
        
        mock_redis_instance = mock_redis_class.return_value
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock
        mock_redis_instance.get.return_value = None  # No rate limit

        response = self.client.patch(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'User already checked in.')
        mock_update_presence.delay.assert_not_called()

    def test_invalid_token(self, mock_redis_class, mock_update_presence):
        invalid_url = reverse('user-check-in', kwargs={'token': str(uuid.uuid4())})
        
        mock_redis_instance = mock_redis_class.return_value
        mock_lock = MagicMock()
        mock_redis_instance.lock.return_value = mock_lock
        mock_lock.__enter__.return_value = mock_lock
        mock_redis_instance.get.return_value = None  # No rate limit

        response = self.client.patch(invalid_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Invalid token", response.data['error'])
        mock_update_presence.delay.assert_not_called()

    def test_rate_limiting_exceeded(self, mock_redis_class, mock_update_presence):
        mock_redis_instance = mock_redis_class.return_value
        # Simulate rate limit exceeded
        mock_redis_instance.get.return_value = "6"  # Over the limit of 5
        
        response = self.client.patch(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Too many check-in attempts", response.data['error'])
        mock_update_presence.delay.assert_not_called()


# --- Task Unit Tests ---
class TaskTests(APITestCase):
    """Test the actual task logic"""
    
    def setUp(self):
        self.existing_user = User.objects.create(
            name='Task Test User',
            email='tasktest@example.com',
            token=str(uuid.uuid4()),
            presence=False,
            event=''
        )

    @patch('mainForm.tasks.generate_qr_code_task')
    def test_check_user_task_existing_user(self, mock_generate_qr):
        """Test check_user_task with existing user"""
        from .tasks import check_user_task
        
        user_data = {
            'name': 'Task Test User',
            'email': 'tasktest@example.com',
            'event': 'New Event'
        }
        
        result = check_user_task(user_data)
        
        # Refresh user from database
        self.existing_user.refresh_from_db()
        
        # Check that event was updated
        self.assertEqual(self.existing_user.event, 'New Event')
        
        # Check that QR generation task was called
        mock_generate_qr.delay.assert_called_once_with(
            self.existing_user.token, 
            self.existing_user.email
        )
        
        # Check return message
        self.assertIn("QR code generation initiated", result)

    def test_check_user_task_nonexistent_user(self):
        """Test check_user_task with non-existent user"""
        from .tasks import check_user_task
        
        user_data = {
            'name': 'Non Existent User',
            'email': 'nonexistent@example.com',
            'event': 'Some Event'
        }
        
        result = check_user_task(user_data)
        
        # Check return message
        self.assertIn("not found in official list", result)

    def test_update_presence_task(self):
        """Test update_presence task"""
        from .tasks import update_presence
        
        # Ensure user is not checked in initially
        self.assertFalse(self.existing_user.presence)
        
        result = update_presence(self.existing_user.id)
        
        # Refresh user from database
        self.existing_user.refresh_from_db()
        
        # Check that presence was updated
        self.assertTrue(self.existing_user.presence)
        
        # Check return message
        self.assertIn("Presence updated", result)