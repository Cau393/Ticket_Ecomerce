from rest_framework import serializers

from .models import (
    Event,
    User,
    TicketClass,
    Order,
    OrderItem,
    PaymentWebhook,
    Ticket,
    EmailLog,
)


class EventSerializer(serializers.ModelSerializer):
    is_upcoming = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'start', 'end', 'location',
            'city', 'state', 'image', 'speakers', 'is_active',
            'created_at', 'updated_at', 'is_upcoming',
        ]

    def validate(self, attrs):
        start = attrs.get('start', getattr(self.instance, 'start', None))
        end = attrs.get('end', getattr(self.instance, 'end', None))
        if start and end and start >= end:
            raise serializers.ValidationError({'start': 'Start must be before end date'})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'cpf', 'date_of_birth',
            'address', 'city', 'state', 'postal_code',
            'partner_company', 'privacy_consent', 'marketing_consent',
            'is_active', 'last_login', 'date_joined', 'password', 'asaas_customer_id',
        ]
        read_only_fields = ['id', 'is_active', 'last_login', 'date_joined']
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password) # Use set_password so the password is hashed
        user.save()
        return user


class TicketClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketClass
        fields = ['id', 'name', 'price', 'ticket_type', 'description']


class OrderItemSerializer(serializers.ModelSerializer):
    # Write via PKs (recommended); also expose compact read-only details
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    ticket_class = serializers.PrimaryKeyRelatedField(queryset=TicketClass.objects.all())
    event_detail = EventSerializer(source='event', read_only=True)
    ticket_class_detail = TicketClassSerializer(source='ticket_class', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'event', 'ticket_class',
            'quantity', 'unit_price', 'subtotal',
            'event_detail', 'ticket_class_detail',
        ]
        read_only_fields = ['id', 'subtotal']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantity must be positive')
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Price cannot be negative')
        return value

class TicketSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    # Derived shortcuts for clients; avoids exposing full nested objects
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)
    event_id = serializers.ReadOnlyField(source='order_item.event.id')
    ticket_class_id = serializers.ReadOnlyField(source='order_item.ticket_class.id')

    class Meta:
        model = Ticket
        fields = [
            'id', 'order', 'qr_code', 'is_redeemed',
            'issued_at', 'redeemed_at', 'redeemed_by_staff',
            'holder_name', 'holder_email',
            'user_id', 'event_id', 'ticket_class_id',
        ]
        read_only_fields = [
            'id', 'qr_code', 'is_redeemed', 'issued_at', 'redeemed_at',
        ]

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    tickets = TicketSerializer(many=True, read_only=True)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'total_amount',
            'status', 'state', 'created_at', 'updated_at',
            'expires_at', 'redemption_token',
            'payment_method', 'payment_id', 'payment_data', 'paid_at',
            'is_paid', 'items', 'tickets',
        ]
        read_only_fields = [
            'id', 'status', 'state', 'created_at', 'updated_at',
            'redemption_token', 'payment_id', 'payment_data', 'paid_at',
            'is_paid',
        ]


class PaymentWebhookSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'order', 'provider', 'webhook_id',
            'event_type', 'payload', 'processed', 'created_at',
        ]
        read_only_fields = ['id', 'processed', 'created_at']




class EmailLogSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all(), allow_null=True, required=False)

    class Meta:
        model = EmailLog
        fields = [
            'id', 'user', 'email_type', 'order', 'subject',
            'sent_at', 'success', 'error_message',
        ]
        read_only_fields = ['id', 'sent_at']

class HolderDataSerializer(serializers.Serializer):
    """A simple serializer to validate holder data provided during checkout."""
    holder_name = serializers.CharField(max_length=150)
    holder_email = serializers.EmailField()

class OrderCreateItemSerializer(serializers.Serializer):
    """Serializer for a single item in the creation request."""
    ticket_class_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    # Add this new field. It's optional ('required=False').
    holders = HolderDataSerializer(many=True, required=False)

    def validate(self, data):
        # Ensure that if holders are provided, the count matches the quantity.
        if 'holders' in data and len(data['holders']) != data['quantity']:
            raise serializers.ValidationError(
                "The number of holders provided must match the ticket quantity."
            )
        return data

class OrderCreateSerializer(serializers.Serializer):
    """Serializer for the overall order creation request."""
    items = OrderCreateItemSerializer(many=True, allow_empty=False)
    billing_type = serializers.ChoiceField(choices=["PIX", "BOLETO", "CREDIT_CARD"], default="PIX")

class TicketAssignmentSerializer(serializers.Serializer):
    """Serializer for assigning a name and email to a ticket."""
    holder_name = serializers.CharField(max_length=150, required=True)
    holder_email = serializers.EmailField(required=True)

    def validate_holder_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Holder name cannot be empty.")
        return value