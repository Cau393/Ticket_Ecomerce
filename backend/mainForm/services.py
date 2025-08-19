# Models import
from .models import EmailLog, User

# Asaas
import requests

# Logging import
import logging
logger = logging.getLogger(__name__)

# Timezone import
from django.utils import timezone

import base64
from django.template.loader import render_to_string

# SendGrid imports
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage
from reportlab import rl_config

# Qr code imports
import qrcode
from io import BytesIO
from django.core.cache import cache

# .env file
from os import getenv
from dotenv import load_dotenv
load_dotenv()

class EmailService:
    @staticmethod
    def send_email_with_attachment(
        *,
        user,
        subject,
        html_template,
        text_template,
        email_context,
        email_type,
        order=None,
        pdf_content=None,
        attachment_filename=None
    ) -> bool:
        try:
            api_key = getenv('SENDGRID_API_KEY')
            if not api_key:
                logger.error("SENDGRID_API_KEY not configured")
                # record failure in EmailLog as expected by tests
                EmailLog.objects.create(
                    user=user,
                    email_type=email_type,
                    order=order,
                    subject=subject,
                    sent_at=timezone.now(),
                    success=False,
                    error_message="SENDGRID_API_KEY not configured"
                )
                return False

            html_content = render_to_string(html_template, email_context)
            text_content = render_to_string(text_template, email_context)
            from_email = getenv('FROM_EMAIL')

            message = Mail(
                from_email=from_email,
                to_emails=user.email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )

            if pdf_content and attachment_filename:
                encoded_pdf = base64.b64encode(pdf_content).decode()
                attachment = Attachment(
                    FileContent(encoded_pdf),
                    FileName(attachment_filename),
                    FileType('application/pdf'),
                    Disposition('attachment')
                )
                message.attachment = attachment

            sg = SendGridAPIClient(api_key=api_key)
            response = sg.send(message)

            success = response.status_code in [200, 201, 202]
            EmailLog.objects.create(
                user=user,
                email_type=email_type,
                order=order,
                subject=subject,
                sent_at=timezone.now(),
                success=success,
                error_message="" if success else f"SendGrid status {response.status_code}"
            )

            if success:
                logger.info(f"Email '{subject}' sent successfully to {user.email}")
            else:
                logger.error(f"Email '{subject}' failed to {user.email}")

            return success

        except Exception as e:
            logger.error(f"Error sending '{subject}' to {user.email}: {str(e)}", exc_info=True)
            EmailLog.objects.create(
                user=user,
                email_type=email_type,
                order=order,
                subject=subject,
                sent_at=timezone.now(),
                success=False,
                error_message=str(e)
            )
            return False

    @staticmethod
    def send_ticket(ticket, pdf_content) -> bool:
        subject = f"Seu ingresso para {ticket.order_item.event.name}"
        context = {
            'user_name': ticket.holder_name or ticket.user.full_name,
            'event': ticket.order_item.event,
            'ticket': ticket,
            'ticket_class': ticket.order_item.ticket_class,
        }
        filename = f"ingresso_{ticket.order_item.event.name.replace(' ', '_')}_{ticket.id}.pdf"
        return EmailService.send_email_with_attachment(
            user=ticket.user,
            subject=subject,
            html_template='emails/ticket_confirmation.html',
            text_template='emails/ticket_confirmation.txt',
            email_context=context,
            email_type='ticket_confirmation',
            order=ticket.order,
            pdf_content=pdf_content,
            attachment_filename=filename
        )

    @staticmethod
    def send_complimentary_link(user, event, email_context, subject, html_template, text_template) -> bool:
        return EmailService.send_email_with_attachment(
            user=user,
            subject=subject,
            html_template=html_template,
            text_template=text_template,
            email_context=email_context,
            email_type='complimentary_link'
        )
    
    @staticmethod
    def send_welcome_email(user):
        return EmailService.send_email_with_attachment(
            user=user,
            subject="Welcome to Our Platform!",
            html_template="emails/welcome.html",
            text_template="emails/welcome.txt",
            email_context={'full_name': user.full_name},
            email_type="welcome"
        )

class PDFService:
    @staticmethod
    def generate_ticket_pdf(ticket):
        """
        Generate a PDF ticket with QR code and event details.
        
        Args:
            ticket (Ticket): The ticket to generate PDF for
            
        Returns:
            bytes: PDF content as bytes
        """
        # Create PDF in memory
        buffer = BytesIO()
        
        # Use A4 page size
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*inch,
            leftMargin=1*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2E86AB'),
            alignment=1  # Center alignment
        )
        
        # Build PDF content
        story = []
        
        # Event information
        event = ticket.order_item.event
        ticket_class = ticket.order_item.ticket_class
        
        # Title
        story.append(Paragraph("INGRESSO DO EVENTO", title_style))
        story.append(Spacer(1, 20))
        
        # Event details
        event_info = [
            f"<b>Evento:</b> {event.name}",
            f"<b>Data:</b> {event.start.strftime('%d/%m/%Y às %H:%M')}",
            f"<b>Local:</b> {event.location}",
            f"<b>Cidade:</b> {event.city}, {event.state}",
            f"<b>Classe:</b> {ticket_class.name}",
            f"<b>Portador:</b> {ticket.holder_name or ticket.user.full_name}",
            f"<b>E-mail:</b> {ticket.holder_email or ticket.user.email}",
        ]
        
        for info in event_info:
            story.append(Paragraph(info, styles['Normal']))
            story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 30))
        
        # Generate QR Code
        qr_image = PDFService.generate_qr_code_image(ticket)
        
        # Add QR code to PDF
        qr_reportlab_image = ReportLabImage(qr_image, width=2*inch, height=2*inch)
        story.append(qr_reportlab_image)
        story.append(Spacer(1, 20))
        
        # QR Code info
        story.append(Paragraph(f"<b>Código QR:</b> {str(ticket.qr_code)}", styles['Normal']))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "<i>Apresente este ingresso na entrada do evento</i>", 
            styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        buffer.seek(0)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    @staticmethod
    def generate_qr_code_image(ticket):
        """
        Generate QR code image from ticket.
        
        Args:
            ticket (Ticket): Ticket to encode in QR code
            
        Returns:
            BytesIO: QR code image buffer
        """
        cache_key = f"qr_{ticket.order_item.event_id}_{ticket.qr_code}"
        try:
            if cached := cache.get(cache_key):
                return BytesIO(cached)  # Cache stores bytes, not BytesIO
        except Exception as e:
            logger.warning(f"Cache read failed: {str(e)}")
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(ticket.qr_code))
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_buffer = BytesIO()    
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Get bytes
        img_bytes = img_buffer.getvalue()

        # Cache info
        cache.set(cache_key, img_bytes, 60 * 60 * 1)
        
        return BytesIO(img_bytes)

class AsaasService:
    BASE_URL = "https://api.asaas.com/v3"

    @classmethod
    def _headers(cls):
        API_KEY = getenv("ASAAS_API_KEY")
        return {
            "Content-Type": "application/json",
            "access_token": API_KEY
        }

    @classmethod
    def ensure_customer(cls, user: User) -> str:
        if getattr(user, "asaas_customer_id", None):
            return user.asaas_customer_id

        payload = {
            "name": user.full_name,
            "email": user.email,
            "cpfCnpj": user.cpf.replace(".", "").replace("-", ""),
            "phone": user.phone,
            **({"externalReference": str(user.id)} if user.id else {})
        }
        r = requests.post(f"{cls.BASE_URL}/customers", json=payload, headers=cls._headers())
        r.raise_for_status()
        data = r.json()
        user.asaas_customer_id = data["id"]
        user.save(update_fields=["asaas_customer_id"])
        return data["id"]

    @classmethod
    def create_charge_for_order(cls, order, billing_type="PIX"):
        """
        Create a payment charge for the given order using the specified billing type.
        Defaults to PIX, but supports BOLETO, CREDIT_CARD, or using UNDEFINED for UI flow.
        """
        customer_id = cls.ensure_customer(order.user)

        payload = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": float(order.total_amount),
            "dueDate": (order.expires_at or timezone.now()).date().isoformat(),
            "description": f"Payment for Order #{order.id}",
        }

        r = requests.post(f"{cls.BASE_URL}/payments", json=payload, headers=cls._headers())
        r.raise_for_status()
        return r.json()