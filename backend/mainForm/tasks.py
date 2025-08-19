import logging

from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone


from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import Order, Ticket, EmailLog

from .services import EmailService, PDFService

logger = logging.getLogger(__name__)


class TicketGenerationError(Exception):
    """Custom exception for ticket generation failures"""
    pass


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_jitter=True
)
def process_ticket_generation(self, order_id):
    """
    Generate all tickets for a paid order and email them.
    
    Args:
        order_id (int): The ID of the order to process
        
    Returns:
        str: Success message with ticket count
        
    Raises:
        TicketGenerationError: When ticket generation fails
    """
    
    logger.info(f"Starting ticket generation for order {order_id}")
    
    try:
        # Step 1: Fetch order with related data in one query
        try:
            order = Order.objects.select_related('user').prefetch_related(
                'items__event',
                'items__ticket_class',
                'tickets'
            ).get(id=order_id)
        except Order.DoesNotExist:
            error_msg = f"Order {order_id} does not exist"
            logger.error(error_msg)
            raise TicketGenerationError(error_msg)
        
        # Step 2: Validate order status and conditions
        if not _validate_order_for_ticket_generation(order):
            error_msg = f"Order {order_id} is not eligible for ticket generation"
            logger.warning(error_msg)
            return error_msg
            
        # Step 3: Generate tickets within a transaction
        tickets_created = []

        try:
            with transaction.atomic():
                tickets_created = _create_tickets_for_order(order)
                logger.info(f"Created {len(tickets_created)} tickets for order {order_id}")
                
        except Exception as e:
            logger.error(f"Failed to create tickets for order {order_id}: {str(e)}")
            raise TicketGenerationError(f"Ticket creation failed: {str(e)}")
        
        
        # Step 5: Log the overall email activity
        msg = f"Generated {len(tickets_created)} tickets for order {order_id}."
        return msg
        
    except TicketGenerationError:
        # Re-raise custom exceptions without retrying
        raise
        
    except MaxRetriesExceededError:
        error_msg = f"Max retries exceeded for order {order_id}"
        logger.error(error_msg)
        _log_failed_ticket_generation(order_id, error_msg)
        raise TicketGenerationError(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error processing order {order_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry for unexpected errors
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_ticket_page(self, ticket_ids):
    """
    Process a batch of tickets: generate PDFs and send emails.
    """
    successful = 0
    failed = 0

    tickets = Ticket.objects.in_bulk(ticket_ids)
    for ticket_id in ticket_ids:
        try:
            ticket = tickets[ticket_id]

            pdf_content = _generate_ticket_pdf(ticket)
            email_sent = EmailService.send_ticket(ticket, pdf_content)

            if email_sent:
                successful += 1
            else:
                failed += 1

        except Exception as e:
            logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
            failed += 1

    logger.info(f"Processed batch: {successful} success, {failed} failed")
    return {"success": successful, "failed": failed}


def _validate_order_for_ticket_generation(order):
    """
    Validate if order is eligible for ticket generation.
    
    Args:
        order (Order): The order to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if order.status != 'pago':
        logger.warning(f"Order {order.id} is not paid (status: {order.status})")
        return False
        
    if order.state != 'ativo':
        logger.warning(f"Order {order.id} is not active (state: {order.state})")
        return False
    
    if order.tickets.exists():
        logger.warning(f"Tickets already exist for order {order.id}")
        return False
        
    if not order.items.exists():
        logger.warning(f"No order items found for order {order.id}")
        return False
    
    return True


def _create_tickets_for_order(order):
    """
    Create all tickets for an order based on OrderItems.
    
    Args:
        order (Order): The order to create tickets for
        
    Returns:
        list[Ticket]: List of created tickets
    """
    tickets_to_create = []
    for order_item in order.items.all():
        tickets_to_create.extend(
            Ticket(order=order, order_item=order_item) 
            for _ in range(order_item.quantity)
        )
    return Ticket.objects.bulk_create(tickets_to_create)

def _generate_ticket_pdf(ticket):
    """
    Generate PDF for a single ticket.
    
    Args:
        ticket (Ticket): The ticket to generate PDF for
        
    Returns:
        bytes: PDF content
    """
    pdf_content = PDFService.generate_ticket_pdf(ticket)
    return pdf_content

def _log_failed_ticket_generation(order_id, error_message):
    """
    Log failed ticket generation attempt.
    
    Args:
        order_id (int): The order ID that failed
        error_message (str): Error description
    """
    try:
        order = Order.objects.get(id=order_id)
        EmailLog.objects.create(
            user=order.user,
            email_type='ticket_confirmation',
            order=order,
            subject=f"FAILED: Ticket generation for order {order_id}",
            sent_at=timezone.now(),
            success=False,
            error_message=error_message
        )
    except Order.DoesNotExist:
        logger.error(f"Could not log failed ticket generation - Order {order_id} not found")


# Additional helper task for retrying individual ticket emails
@shared_task(bind=True, max_retries=3)
def retry_ticket_email(self, ticket_id):
    """
    Retry sending email for a specific ticket.
    
    Args:
        ticket_id (int): ID of the ticket to retry email for
    """
    try:
        ticket = Ticket.objects.select_related(
            'order__user', 
            'order_item__event', 
            'order_item__ticket_class'
        ).get(id=ticket_id)
        
        # Generate PDF and send email
        pdf_content = _generate_ticket_pdf(ticket)
        success = EmailService.send_ticket(ticket, pdf_content)
        
        if success:
            logger.info(f"Successfully retried email for ticket {ticket_id}")
            return f"Email sent successfully for ticket {ticket_id}"
        else:
            logger.info(f"Email sending failed, retry amount reached {self.request.retries}")
            raise Exception("Email sending failed")
            
    except Ticket.DoesNotExist:
        logger.error(f"Ticket {ticket_id} does not exist")
        raise
        
    except Exception as e:
        logger.error(f"Failed to retry email for ticket {ticket_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# Task for sending complimentary tickets
@shared_task(bind=True, max_retries=3)
def send_complimentary_ticket_link(self, user_id, event_id):
    """
    Send complimentary ticket link to partner company users.
    
    Args:
        user_id (int): ID of the user to send link to
        event_id (int): ID of the event
    """
    from .models import User, Event  # Import here to avoid circular imports
    
    try:
        user = User.objects.get(id=user_id)
        event = Event.objects.get(id=event_id)
        
        if not user.partner_company:
            raise ValueError(f"User {user_id} is not associated with a partner company")
        
        # Generate complimentary ticket link logic here
        # This would integrate with your complimentary ticket system
        
        subject = f"Link de cortesia para {event.name}"
        
        email_context = {
            'user': user,
            'event': event,
            'company': user.partner_company,
        }
        
        # Send email using SendGrid
        success = EmailService.send_email_with_attachment(
            user=user,
            email_context=email_context,
            subject=subject,
            html_template='emails/complimentary_link.html',
            text_template='emails/complimentary_link.txt',
            email_type='complimentary_link'
        )
        
        if success:
            logger.info(f"Complimentary ticket link sent to {user.email}")
            return f"Complimentary link sent to {user.email}"
        else:
            logger.info("Failed to send complimentary email via SendGrid")
            raise Exception("Failed to send complimentary email via SendGrid")
        
    except (User.DoesNotExist, Event.DoesNotExist) as e:
        logger.error(f"Invalid user or event: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Failed to send complimentary link: {str(e)}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email_task(self, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        EmailService.send_welcome_email(user)
        logger.info(f"Welcome email sent to {user.email}")
        return f"Welcome email sent to {user.email}"

    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3)
def generate_and_send_courtesy_link(self, event_id: int, recipient_email: str, partner_company: str, quantity: int = 1):
    """
    Creates a courtesy order with a specific quantity of tickets and emails a unique redemption link.
    """
    logger.info(f"Generating courtesy link for {quantity} tickets for event {event_id} to {recipient_email}")
    try:
        with transaction.atomic():
            # 1. Find the specific 'cortesia' ticket class for the event
            ticket_class = TicketClass.objects.get(event_id=event_id, ticket_type='cortesia')
            if ticket_class.price > 0:
                raise ValueError("Courtesy ticket class must have a price of 0.")

            # 2. Create the placeholder Order (no changes here)
            order = Order.objects.create(
                user=None,
                total_amount=0.00,
                status='pendente',
                state='ativo',
                payment_method='cortesia'
            )

            # 3. Create the OrderItem with the correct quantity
            OrderItem.objects.create(
                order=order,
                event_id=event_id,
                ticket_class=ticket_class,
                quantity=quantity, # Use the new quantity parameter
                unit_price=0.00,
                subtotal=0.00
            )
            
            # 4. Prepare and send the email
            event = Event.objects.get(id=event_id)
            redemption_url = f"https://www.cdpipass.com.br/redeem/{order.redemption_token}"
            
            email_context = {
                'event_name': event.name,
                'partner_company': partner_company,
                'redemption_url': redemption_url,
            }
            
            # This is a simplified call; you should create proper email templates
            # as defined in your EmailService.
            EmailService.send_email_with_attachment(
                user={'email': recipient_email}, # Temporarily pass a dict
                subject=f"Você recebeu uma cortesia para o evento {event.name}",
                html_template='emails/complimentary_link.html',
                text_template='emails/complimentary_link.txt',
                email_context=email_context,
                email_type='complimentary_link'
            )

        logger.info(f"Successfully sent courtesy link for order {order.id} to {recipient_email}")
        return f"Link sent for order {order.id}"

    except (Event.DoesNotExist, TicketClass.DoesNotExist) as e:
        logger.error(f"Configuration error for courtesy link generation: {e}")
        # Do not retry for configuration errors
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Failed to send courtesy link: {e}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def send_assigned_ticket_email(self, ticket_id):
    """
    Generates a PDF for a single assigned ticket and emails it to the holder.
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        if not ticket.holder_email:
            logger.warning(f"Attempted to email ticket {ticket_id} with no holder email.")
            return

        logger.info(f"Generating PDF and sending email for ticket {ticket_id} to {ticket.holder_email}")

        pdf_content = PDFService.generate_ticket_pdf(ticket)
        
        # We need to send the email to the TICKET HOLDER, not the order owner.
        # We'll create a temporary "user-like" object for the EmailService.
        holder_info = {'email': ticket.holder_email}
        
        # Manually construct and send email via EmailService
        subject = f"Seu ingresso para {ticket.order_item.event.name}"
        context = {
            'user_name': ticket.holder_name,
            'event': ticket.order_item.event,
        }
        filename = f"ingresso_{ticket.order_item.event.name.replace(' ', '_')}_{ticket.id}.pdf"
        
        success = EmailService.send_email_with_attachment(
            user=holder_info, # Sending to the ticket holder
            subject=subject,
            html_template='emails/ticket_confirmation.html',
            text_template='emails/ticket_confirmation.txt',
            email_context=context,
            email_type='ticket_confirmation',
            order=ticket.order,
            pdf_content=pdf_content,
            attachment_filename=filename
        )

        if not success:
            raise Exception("EmailService failed to send the ticket.")

        return f"Successfully sent email for ticket {ticket_id}"

    except Ticket.DoesNotExist:
        logger.error(f"Cannot send email: Ticket {ticket_id} not found.")
    except Exception as e:
        logger.error(f"Error sending assigned ticket email for ticket {ticket_id}: {e}")
        raise self.retry(exc=e)