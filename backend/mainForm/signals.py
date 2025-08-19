from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from .tasks import send_assigned_ticket_email

@receiver(post_save, sender=Order)
def on_order_paid(sender, instance, created, **kwargs):
    """
    When an order is saved, check if it has just been marked as paid.
    If so, send emails for any tickets that have already been assigned a holder.
    """
    # We only care about updates to existing orders, not new ones.
    if created:
        return

    # Check if the status is 'pago' and if the status has actually changed.
    # The 'update_fields' check is a good practice for performance.
    if instance.status == 'pago' and kwargs.get('update_fields') and 'status' in kwargs['update_fields']:
        
        # Find all tickets for this order that have holder info but haven't been sent.
        # This is a simplified check; you might add a 'email_sent_at' field to the Ticket model
        # for more robust tracking.
        tickets_to_send = instance.tickets.filter(holder_email__isnull=False).exclude(holder_email='')
        
        for ticket in tickets_to_send:
            send_assigned_ticket_email.delay(ticket.id)