from django.conf import settings
from django.db.models import Q  # Add this import for Q objects
from celery import shared_task
from .models import User
import qrcode
from io import BytesIO
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition
)

@shared_task
def check_user_task(user_data, client_ip=None):
    """
    1. Checks if user exists by email OR name in the official list
    2. If user exists, updates the event and passes data to next task
    """
    try:
        # Check if user exists by email OR name
        user = User.objects.get(
            Q(email=user_data['email']) |
            Q(name=user_data['name'])
        )
        
        # Update event field
        user.event = user_data.get('event', '')
        user.save(update_fields=['event'])
        
        # User found, proceed with QR code generation
        generate_qr_code_task.delay(user.token, user.email)
        return f"User check for {user.email} started - QR code generation initiated."
        
    except User.DoesNotExist:
        return f"User with email {user_data['email']} or name {user_data['name']} not found in official list."
    except Exception as e:
        return f"Error checking user: {str(e)}"

@shared_task
def generate_qr_code_task(user_token, user_email):
    """
    1. Generates a QR code from the given token (No DB hit).
    2. Passes the email and image data to the next task.
    """
    try:
        qr_image = qrcode.make(user_token)
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Call the final task, passing along the email and the encoded image
        send_qr_code_email.delay(user_email, encoded_image)
        return f"QR Code generated for {user_email}."
    except Exception as e:
        return f"Error generating QR code for {user_email}: {str(e)}"

@shared_task
def send_qr_code_email(user_email, encoded_image):
    """
    1. Receives email address and image data (No DB hit).
    2. Constructs and sends the email.
    """
    try:
        message = Mail(
            from_email=settings.FROM_EMAIL,
            to_emails=user_email,
            subject='Seu QR Code de acesso CDPI!',
            html_content='<strong>Aqui está seu QR code para entrar no evento.</strong><p>Por favor esteja com ele em mãos na entrada.</p>'
        )
        
        message.attachment = Attachment(
            FileContent(encoded_image),
            FileName('qrcode.png'),
            FileType('image/png'),
            Disposition('attachment')
        )
        
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        return f"Email sent to {user_email} with status code {response.status_code}"
        
    except Exception as e:
        print(f"Error sending email: {e}")
        raise e

@shared_task
def update_presence(user_id, client_ip=None, timestamp=None):
    """
    Update user presence to True
    """
    try:
        user = User.objects.get(pk=user_id)
        user.presence = True
        user.save(update_fields=['presence'])
        return f"Presence updated for {user.email}."
    except User.DoesNotExist:
        return f"User with id {user_id} not found."
    except Exception as e:
        return f"Error updating presence for user {user_id}: {str(e)}"