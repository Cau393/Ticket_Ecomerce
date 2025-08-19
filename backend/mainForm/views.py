# Logging import
import logging
logger = logging.getLogger(__name__)

# Generics
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, UpdateAPIView

# Services
from .services import AsaasService

# Asaas
import requests
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

# Utils
from django.utils import timezone

# Confs
from django.conf import settings

# Views
from rest_framework.views import APIView

# Viewsets
from rest_framework.viewsets import ModelViewSet

# Decorators
from rest_framework.decorators import action
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

# Permissions
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

# Serializers
from .serializers import UserSerializer, EventSerializer, OrderSerializer, OrderCreateSerializer, TicketAssignmentSerializer

# Tasks
from .tasks import send_welcome_email_task, send_assigned_ticket_email

# Models
from .models import Event, Order, TicketClass, OrderItem, PaymentWebhook

# Auth
from django.contrib.auth import authenticate, login as django_login, logout as django_logout

class UserRegistrationAPIView(CreateAPIView):
    """
    Register a new user.
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Only send welcome email if we have a valid task system
        try:
            send_welcome_email_task.delay(user.id)
        except Exception as e:
            logger.warning(f"Failed to queue welcome email for user {user.id}: {e}")

class UserMeView(RetrieveUpdateAPIView):
    """
    View to get and update the current user's profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class EventViewSet(ModelViewSet):
    """
    Viewset for listing, retrieving and (superuser-only) creating events.
    """
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        # Only superusers can create events
        if self.action == 'create':
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        return Event.objects.filter(is_active=True, start__gt=timezone.now())

class OrderViewSet(ModelViewSet):
    """
    Viewset for creating, listing, and retrieving orders.
    """
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Ensure users can only see their own orders."""
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'tickets')

    def get_serializer_class(self):
        """Use a different serializer for the 'create' action."""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer # Use the default for all other actions (list, retrieve, etc.)

    def create(self, request, *args, **kwargs):
        """
        Overrides the default create method to handle order and order item creation.
        """
        # Step 1: Validate the incoming request data using our "write" serializer
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        validated_data = write_serializer.validated_data
        items_data = validated_data['items']
        billing_type = validated_data['billing_type']

        try:
            # Step 2: Use a database transaction to ensure all or nothing is created.
            with transaction.atomic():
                all_holders_data = [holder for item in items_data for holder in item.get('holders', [])]
                total_amount = 0
                order_items_to_create = []

                # Step 3: Loop through items to calculate total and prepare OrderItems
                for item_data in items_data:
                    try:
                        ticket_class = TicketClass.objects.get(id=item_data['ticket_class_id'])
                    except TicketClass.DoesNotExist:
                        return Response(
                            {'error': f"TicketClass with id {item_data['ticket_class_id']} not found."},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    
                    # Validate quantity
                    quantity = item_data['quantity']
                    if quantity <= 0:
                        return Response(
                            {'error': 'Quantity must be positive'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    subtotal = ticket_class.price * quantity
                    total_amount += subtotal

                    order_items_to_create.append(
                        OrderItem(
                            # The 'order' FK will be set after the order is created
                            event=ticket_class.event, # Assuming TicketClass has a FK to Event
                            ticket_class=ticket_class,
                            quantity=quantity,
                            unit_price=ticket_class.price,
                            subtotal=subtotal
                        )
                    )

                # Step 4: Create the parent Order instance
                order = Order.objects.create(
                    user=request.user,
                    total_amount=total_amount,
                    status='pendente' # Start with a pending status
                )

                # Step 5: Assign the created order to each OrderItem and bulk create them
                tickets_to_create = []
                for i, item in enumerate(order_items_to_create):
                    item.order = order
                    item.save() # Save the OrderItem to get an ID

                    holders_for_this_item = all_holders_data[i]
                    
                    for j in range(item.quantity):
                        ticket = Ticket(order=order, order_item=item)
                        # If holder data was provided for this ticket, add it now.
                        if j < len(holders_for_this_item):
                            holder_data = holders_for_this_item[j]
                            ticket.holder_name = holder_data['holder_name']
                            ticket.holder_email = holder_data['holder_email']
                        
                        tickets_to_create.append(ticket)

                Ticket.objects.bulk_create(tickets_to_create)

                if order.total_amount > 0:
                    payment_details = AsaasService.create_charge_for_order(order, billing_type=billing_type)
                    order.payment_id = payment_details.get("id")
                    order.payment_data = payment_details
                    order.save(update_fields=["payment_id", "payment_data"])
                else:
                    # If it's a zero-cost (courtesy) order, mark it as paid instantly.
                    order.status = 'pago'
                    order.paid_at = timezone.now()
                    order.save(update_fields=['status', 'paid_at'])

                # Step 7: Serialize the final, created order for the response
                read_serializer = OrderSerializer(order)
                return Response(read_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Catch any other exceptions and return a generic error
            logger.error(f"Error creating order: {e}")
            return Response(
                {'error': f'An unexpected error occurred during order creation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # @action(detail=True, methods=['post'])
    # def create_payment_charge(self, request, pk=None):
    #     """
    #     Create a payment charge for an order using Asaas service.
    #     """
    #     order = self.get_object()
    #     billing_type = request.data.get("billing_type", "PIX").upper()
        
    #     # Validate billing type
    #     valid_billing_types = {"PIX", "BOLETO", "CREDIT_CARD", "UNDEFINED"}
    #     if billing_type not in valid_billing_types:
    #         return Response(
    #             {"error": f"Unsupported billing_type. Valid options are: {', '.join(valid_billing_types)}"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     # Validate order status
    #     if order.status != 'pendente':
    #         return Response(
    #             {"error": "Payment charges can only be created for pending orders"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     try:
    #         payment_details = AsaasService.create_charge_for_order(order, billing_type=billing_type)
    #         order.payment_id = payment_details.get("id")
    #         order.payment_data = payment_details
    #         order.save(update_fields=["payment_id", "payment_data"])
    #         return Response(payment_details, status=status.HTTP_200_OK)
    #     except requests.HTTPError as e:
    #         logger.error(f"Asaas API error for order {order.id}: {e}")
    #         return Response({"error": f"Asaas API error: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
    #     except Exception as e:
    #         logger.error(f"Unexpected error creating payment charge for order {order.id}: {e}")
    #         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AsaasWebHookView(APIView):
    permission_classes = [AllowAny] # Must be accessible by the external service

    def post(self, request, *args, **kwargs):
        """
        Webhook endpoint for Asaas
        """

        # Get the token from the headers
        token = request.headers.get("Asaas-Webhook-Token")

        # Compare it to your secret token stored in settings (or .env file)
        if not token or token != settings.ASAAS_WEBHOOK_SECRET:
            # If tokens don't match, it's an unauthorized request.
            logger.warning(f"Unauthorized webhook request with token: {token}")
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data
        
        # Store webhook for audit
        try:
            PaymentWebhook.objects.create(
                provider='asaas',
                webhook_id=payload.get('id'),
                event_type=payload.get('event'),
                payload=payload
            )
        except Exception as e:
            logger.error(f"Failed to store webhook: {e}")

        event_type = payload.get('event')
        payment_id = payload.get('payment', {}).get('id')

        if event_type == 'PAYMENT_RECEIVED' and payment_id:
            try:
                order = Order.objects.get(payment_id=payment_id)
                order.status = 'pago'
                order.paid_at = timezone.now()
                order.save(update_fields=['status', 'paid_at'])
                logger.info(f"Order {order.id} marked as paid via webhook")
                # process_ticket_generation.delay(order.id)  # Uncomment when Celery task available
            except Order.DoesNotExist:
                logger.error(f"Order with payment_id {payment_id} not found.")
            except Exception as e:
                logger.error(f"Error processing payment webhook: {e}")

        return Response(status=status.HTTP_200_OK)

class TicketAssignmentView(UpdateAPIView):
    """
    Assigns holder details to an unassigned ticket and triggers the confirmation email.
    """
    serializer_class = TicketAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only assign tickets from orders they own.
        return Ticket.objects.filter(order__user=self.request.user)

    def update(self, request, *args, **kwargs):
        ticket = self.get_object()

        # Prevent re-assigning an already assigned ticket
        if ticket.holder_name or ticket.holder_email:
            return Response(
                {'error': 'This ticket has already been assigned.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update the ticket object
        ticket.holder_name = serializer.validated_data['holder_name']
        ticket.holder_email = serializer.validated_data['holder_email']
        ticket.save()

        # Trigger the email to the new ticket holder
        send_assigned_ticket_email.delay(ticket.id)

        # Return the fully updated ticket details
        read_serializer = TicketSerializer(ticket)
        return Response(read_serializer.data, status=status.HTTP_200_OK)

class CourtesyDataView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            # Get the courtesy order and prefetch related data
            courtesy_order = Order.objects.select_related('event').prefetch_related(
                'items__ticket_class'
            ).get(redemption_token=token, status='cortesia_pendente')

            # Prepare the response data structure
            response_data = {
                'order': {
                    'id': courtesy_order.id,
                    'redemption_token': courtesy_order.redemption_token,
                    'total_amount': courtesy_order.total_amount,
                    'status': courtesy_order.status,
                    'created_at': courtesy_order.created_at,
                },
                'event': {
                    'id': courtesy_order.event.id,
                    'name': courtesy_order.event.name,
                    'description': courtesy_order.event.description,
                    'start': courtesy_order.event.start,
                    'end': courtesy_order.event.end,
                    'location': courtesy_order.event.location,
                },
                'items': []
            }

            # Add order items data
            for item in courtesy_order.items.all():
                item_data = {
                    'id': item.id,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'subtotal': item.subtotal,
                    'ticket_class': {
                        'id': item.ticket_class.id,
                        'name': item.ticket_class.name,
                        'description': item.ticket_class.description,
                        'price': item.ticket_class.price,
                    }
                }
                response_data['items'].append(item_data)

            return Response(response_data)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Courtesy offer not found or expired'}, 
                status=status.HTTP_404_NOT_FOUND
            )

@method_decorator(ensure_csrf_cookie, name="get")
class CsrfTokenView(APIView):
    """
    Ensures the CSRF cookie is set for the client.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set"}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(APIView):
    """
    Session-based login endpoint. Accepts JSON: { email, password }.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email") or request.data.get("username")
        password = request.data.get("password")
        if not email or not password:
            return Response({"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        django_login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

class LogoutAPIView(APIView):
    """
    Session-based logout endpoint.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        django_logout(request)
        return Response({"detail": "Logged out"}, status=status.HTTP_200_OK)