from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from io import BytesIO
from pypdf import PdfReader

from .factories import UserFactory, TicketFactory, OrderFactory, EventFactory, TicketClassFactory, OrderItemFactory
from mainForm.services import PDFService, EmailService, AsaasService
from mainForm.models import EmailLog

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)

class PDFServiceTests(TestCase):
    def setUp(self):
        """Set up test data for PDF service tests."""
        self.user = UserFactory(
            full_name="João Silva",
            email="joao@example.com"
        )
        self.event = EventFactory(
            name="Evento Teste CDPI",
            location="Centro de Convenções",
            city="São Paulo",
            state="SP",
            start=timezone.now() + timezone.timedelta(days=30)
        )
        self.ticket_class = TicketClassFactory(
            event=self.event,
            name="VIP"
        )
        # Create an OrderItem that links them all together
        order_item = OrderItemFactory(
            ticket_class=self.ticket_class,
            order__user=self.user
        )
        # Now create the ticket correctly linked to the order item
        self.ticket = TicketFactory(order_item=order_item)

    def test_generate_ticket_pdf(self):
        """
        Ensure the PDF service generates a valid PDF bytes object.
        """
        # Act
        pdf_content = PDFService.generate_ticket_pdf(self.ticket)

        # Assert
        self.assertIsInstance(pdf_content, bytes)
        self.assertTrue(len(pdf_content) > 0)
        # A simple check to see if it starts with the PDF magic number
        self.assertTrue(pdf_content.startswith(b'%PDF-'))
        # Check if PDF contains event information
        pdf_text = extract_text_from_pdf(pdf_content)
        self.assertIn('INGRESSO DO EVENTO', pdf_text)
        self.assertIn(self.event.name, pdf_text)

    @patch('mainForm.services.cache')
    def test_generate_qr_code_image_with_cache(self, mock_cache):
        """
        Test QR code generation with cache functionality.
        """
        # Arrange
        mock_cache.get.return_value = None  # Cache miss

        # Act
        qr_image_buffer = PDFService.generate_qr_code_image(self.ticket)

        # Assert
        self.assertIsInstance(qr_image_buffer, BytesIO)
        # Check that cache.set was called
        mock_cache.set.assert_called_once()
        # Check that the buffer contains PNG data
        qr_image_buffer.seek(0)
        png_data = qr_image_buffer.read()
        self.assertTrue(png_data.startswith(b'\x89PNG'))

    @patch('mainForm.services.cache')
    def test_generate_qr_code_image_cache_hit(self, mock_cache):
        """
        Test QR code generation when cache hit occurs.
        """
        # Arrange
        fake_cached_data = b'fake_png_data'
        mock_cache.get.return_value = fake_cached_data

        # Act
        qr_image_buffer = PDFService.generate_qr_code_image(self.ticket)

        # Assert
        self.assertIsInstance(qr_image_buffer, BytesIO)
        # Verify cache was checked
        mock_cache.get.assert_called_once()
        # Verify cache.set was NOT called (since we had a cache hit)
        mock_cache.set.assert_not_called()


class EmailServiceTests(TestCase):
    def setUp(self):
        """Set up test data for email service tests."""
        self.user = UserFactory(
            full_name="Maria Santos",
            email="maria@cdpipass.com"
        )
        self.event = EventFactory(name="Workshop Farmacêutico CDPI")
        self.ticket_class = TicketClassFactory(
            event=self.event,
            name="Geral"
        )
        # Create an OrderItem that links them all together
        order_item = OrderItemFactory(
            ticket_class=self.ticket_class,
            order__user=self.user
        )
        # Now create the ticket correctly linked to the order item
        self.ticket = TicketFactory(
            order_item=order_item,
            holder_name="Maria Santos"
        )

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.SendGridAPIClient')
    def test_send_ticket_calls_sendgrid_and_logs_success(self, mock_sendgrid_client, mock_getenv):
        """
        Ensure the send_ticket service:
        1. Attempts to send an email via the SendGrid client.
        2. Creates a successful EmailLog entry.
        """
        # Arrange
        mock_getenv.side_effect = lambda key: {
            'SENDGRID_API_KEY': 'test_api_key',
            'FROM_EMAIL': 'noreply@cdpipass.com.br'
        }.get(key)
        
        pdf_content = b'%PDF-1.4 fake pdf content'
        
        # Configure the mock to simulate a successful API response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sendgrid_client.return_value.send.return_value = mock_response

        # Act
        success = EmailService.send_ticket(self.ticket, pdf_content)

        # Assert
        self.assertTrue(success)
        # Check that the 'send' method on the mocked client was called exactly once
        mock_sendgrid_client.return_value.send.assert_called_once()
        # Check that a success log was created in our database
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertTrue(email_log.success)
        self.assertEqual(email_log.user, self.user)
        self.assertEqual(email_log.email_type, 'ticket_confirmation')
        self.assertIn('Seu ingresso para', email_log.subject)

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.SendGridAPIClient')
    def test_send_ticket_handles_sendgrid_error(self, mock_sendgrid_client, mock_getenv):
        """
        Test that send_ticket handles SendGrid API errors gracefully.
        """
        # Arrange
        mock_getenv.side_effect = lambda key: {
            'SENDGRID_API_KEY': 'test_api_key',
            'FROM_EMAIL': 'noreply@cdpipass.com.br'
        }.get(key)
        
        pdf_content = b'%PDF-1.4 fake pdf content'
        
        # Configure the mock to simulate an API error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_sendgrid_client.return_value.send.return_value = mock_response

        # Act
        success = EmailService.send_ticket(self.ticket, pdf_content)

        # Assert
        self.assertFalse(success)
        # Check that an error log was created
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertFalse(email_log.success)
        self.assertIn('SendGrid status 400', email_log.error_message)

    @patch('mainForm.services.getenv')
    def test_send_ticket_missing_api_key(self, mock_getenv):
        """
        Test that send_ticket fails gracefully when API key is missing.
        """
        # Arrange
        mock_getenv.return_value = None  # No API key
        pdf_content = b'%PDF-1.4 fake pdf content'

        # Act
        success = EmailService.send_ticket(self.ticket, pdf_content)

        # Assert
        self.assertFalse(success)
        # Should create an error log
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertFalse(email_log.success)

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.SendGridAPIClient')
    def test_send_welcome_email(self, mock_sendgrid_client, mock_getenv):
        """
        Test welcome email functionality.
        """
        # Arrange
        mock_getenv.side_effect = lambda key: {
            'SENDGRID_API_KEY': 'test_api_key',
            'FROM_EMAIL': 'noreply@cdpipass.com.br'
        }.get(key)
        
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sendgrid_client.return_value.send.return_value = mock_response

        # Act
        success = EmailService.send_welcome_email(self.user)

        # Assert
        self.assertTrue(success)
        mock_sendgrid_client.return_value.send.assert_called_once()
        
        # Check email log
        email_log = EmailLog.objects.first()
        self.assertEqual(email_log.email_type, 'welcome')
        self.assertEqual(email_log.subject, 'Welcome to Our Platform!')

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.SendGridAPIClient')
    def test_send_complimentary_link(self, mock_sendgrid_client, mock_getenv):
        """
        Test complimentary link email functionality.
        """
        # Arrange
        mock_getenv.side_effect = lambda key: {
            'SENDGRID_API_KEY': 'test_api_key',
            'FROM_EMAIL': 'noreply@cdpipass.com.br'
        }.get(key)
        
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sendgrid_client.return_value.send.return_value = mock_response

        event = EventFactory(name="Evento Cortesia CDPI")
        email_context = {
            'user_name': self.user.full_name,
            'event': event,
            'complimentary_link': 'https://cdpipass.com.br/cortesia/abc123'
        }

        # Act
        success = EmailService.send_complimentary_link(
            user=self.user,
            event=event,
            email_context=email_context,
            subject="Sua cortesia para o evento CDPI",
            html_template="emails/complimentary.html",
            text_template="emails/complimentary.txt"
        )

        # Assert
        self.assertTrue(success)
        mock_sendgrid_client.return_value.send.assert_called_once()
        
        # Check email log
        email_log = EmailLog.objects.first()
        self.assertEqual(email_log.email_type, 'complimentary_link')


class AsaasServiceTests(TestCase):
    def setUp(self):
        """Set up test data for Asaas service tests."""
        self.user = UserFactory(
            full_name="Carlos Silva",
            email="carlos@cdpipass.com",
            cpf="123.456.789-01",
            phone="(11) 99999-9999"
        )
        self.order = OrderFactory(
            user=self.user,
            total_amount=150.50
        )

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.requests.post')
    def test_ensure_customer_creates_new_customer(self, mock_post, mock_getenv):
        """
        Test that ensure_customer creates a new customer when user doesn't have asaas_customer_id.
        """
        # Arrange
        mock_getenv.return_value = 'test_api_key'
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'cus_123456789'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Ensure user doesn't have asaas_customer_id
        self.user.asaas_customer_id = None
        self.user.save()

        # Act
        customer_id = AsaasService.ensure_customer(self.user)

        # Assert
        self.assertEqual(customer_id, 'cus_123456789')
        # Check that requests.post was called once
        mock_post.assert_called_once()
        
        # Check the payload sent to Asaas
        _, call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs['json']['name'], self.user.full_name)
        self.assertEqual(call_kwargs['json']['email'], self.user.email)
        self.assertEqual(call_kwargs['json']['cpfCnpj'], '12345678901')  # CPF without formatting
        self.assertEqual(call_kwargs['json']['phone'], self.user.phone)
        
        # Check that user was updated with customer_id
        self.user.refresh_from_db()
        self.assertEqual(self.user.asaas_customer_id, 'cus_123456789')

    def test_ensure_customer_returns_existing_id(self):
        """
        Test that ensure_customer returns existing customer ID without API call.
        """
        # Arrange
        existing_customer_id = 'cus_existing_123'
        self.user.asaas_customer_id = existing_customer_id
        self.user.save()

        # Act
        with patch('mainForm.services.requests.post') as mock_post:
            customer_id = AsaasService.ensure_customer(self.user)

        # Assert
        self.assertEqual(customer_id, existing_customer_id)
        # Ensure no API call was made
        mock_post.assert_not_called()

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.requests.post')
    def test_create_charge_for_order_pix(self, mock_post, mock_getenv):
        """Test creating a PIX charge for an order."""
        # Arrange
        mock_getenv.return_value = 'test_api_key'
        
        # Mock existing customer
        self.user.asaas_customer_id = 'cus_existing'
        self.user.save()
        
        # Configure the mock to return a success response
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'pay_123', 'status': 'PENDING'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Act
        result = AsaasService.create_charge_for_order(self.order, 'PIX')
        
        # Assert
        # Verify the mock was called exactly once
        mock_post.assert_called_once()
        
        # Capture the call arguments
        call_args, call_kwargs = mock_post.call_args
        
        # 1. Validate the URL (positional argument)
        url_called = call_args[0]
        self.assertTrue(url_called.endswith('/payments'))
        self.assertEqual(url_called, 'https://api.asaas.com/v3/payments')
        
        # 2. Validate the payload (keyword argument 'json')
        payload = call_kwargs.get('json')
        self.assertIsNotNone(payload)
        self.assertEqual(payload['customer'], self.user.asaas_customer_id)
        self.assertEqual(payload['billingType'], 'PIX')
        self.assertEqual(payload['value'], float(self.order.total_amount))
        
        # 3. Validate the headers (keyword argument 'headers')
        headers = call_kwargs.get('headers')
        self.assertIsNotNone(headers)
        self.assertEqual(headers['access_token'], 'test_api_key')
        
        # 4. Validate the result returned by the service
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'pay_123')

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.requests.post')
    def test_create_charge_for_order_boleto(self, mock_post, mock_getenv):
        """
        Test creating a BOLETO charge for an order.
        """
        # Arrange
        mock_getenv.return_value = 'test_api_key'
        
        # Mock existing customer
        self.user.asaas_customer_id = 'cus_existing'
        self.user.save()
        
        # Mock payment response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'pay_boleto_123',
            'status': 'PENDING',
            'bankSlipUrl': 'https://asaas.com/boleto/123'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Act
        result = AsaasService.create_charge_for_order(self.order, billing_type="BOLETO")

        # Assert
        self.assertEqual(result['id'], 'pay_boleto_123')
        
        # Check that only payment creation was called (no customer creation)
        mock_post.assert_called_once()
        _, call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs['json']['billingType'], 'BOLETO')

    @patch('mainForm.services.getenv')
    def test_headers_method(self, mock_getenv):
        """
        Test that _headers method returns correct headers.
        """
        # Arrange
        mock_getenv.return_value = 'test_api_key_12345'

        # Act
        headers = AsaasService._headers()

        # Assert
        expected_headers = {
            "Content-Type": "application/json",
            "access_token": "test_api_key_12345"
        }
        self.assertEqual(headers, expected_headers)

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.requests.post')
    def test_create_charge_handles_api_error(self, mock_post, mock_getenv):
        """
        Test that create_charge_for_order handles API errors properly.
        """
        # Arrange
        mock_getenv.return_value = 'test_api_key'
        self.user.asaas_customer_id = 'cus_existing'
        self.user.save()
        
        # Mock API error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_post.return_value = mock_response

        # Act & Assert
        with self.assertRaises(Exception):
            AsaasService.create_charge_for_order(self.order)

    def test_base_url_constant(self):
        """
        Test that BASE_URL is correctly set.
        """
        self.assertEqual(AsaasService.BASE_URL, "https://api.asaas.com/v3")


# Additional integration test
class ServiceIntegrationTests(TestCase):
    """
    Integration tests that test multiple services working together.
    """
    
    def setUp(self):
        self.user = UserFactory(
            full_name="Ana Costa",
            email="ana@cdpipass.com"
        )
        self.event = EventFactory(name="Summit CDPI 2024")
        self.ticket = TicketFactory(
            user=self.user,
            event=self.event
        )

    @patch('mainForm.services.getenv')
    @patch('mainForm.services.SendGridAPIClient')
    def test_complete_ticket_generation_and_email_flow(self, mock_sendgrid, mock_getenv):
        """
        Test the complete flow: generate PDF + send email.
        """
        # Arrange
        mock_getenv.side_effect = lambda key: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'noreply@cdpipass.com.br'
        }.get(key)
        
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sendgrid.return_value.send.return_value = mock_response

        # Act - Generate PDF
        pdf_content = PDFService.generate_ticket_pdf(self.ticket)
        
        # Act - Send email with PDF
        email_success = EmailService.send_ticket(self.ticket, pdf_content)

        # Assert
        self.assertIsNotNone(pdf_content)
        self.assertTrue(pdf_content.startswith(b'%PDF-'))
        self.assertTrue(email_success)
        
        # Verify email was attempted
        mock_sendgrid.return_value.send.assert_called_once()
        
        # Check that EmailLog was created
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertTrue(email_log.success)
        self.assertEqual(email_log.email_type, 'ticket_confirmation')