import uuid
from django.db import models
from .managers import CustomUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from localflavor.br.models import BRCPFField, BRStateField, BRPostalCodeField
from django.utils.functional import cached_property

class Event(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nome do Evento')
    description = models.TextField(verbose_name='Descrição')
    start = models.DateTimeField(verbose_name='Data/Hora de Início')
    end = models.DateTimeField(verbose_name='Data/Hora de Término')
    location = models.CharField(max_length=300, verbose_name='Local')
    city = models.CharField(max_length=100, verbose_name='Cidade')
    state = BRStateField(verbose_name='Estado')
    image = models.ImageField(upload_to='events/', blank=True, verbose_name='Imagem do Evento')
    speakers = models.TextField(blank=True, verbose_name='Palestrantes')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['start']
        indexes = [
            models.Index(fields=['start', 'is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_upcoming(self):
        return self.start > timezone.now()
    
    def clean(self):
        if self.start >= self.end:
            raise ValidationError("Start must be before end date")


class User(AbstractUser):
    username = None  
    email = models.EmailField(unique=True, verbose_name='E-mail')
    full_name = models.CharField(max_length=150, verbose_name='Nome Completo')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    cpf = BRCPFField(verbose_name='CPF')
    date_of_birth = models.DateField(verbose_name='Data de Nascimento', null=True, blank=True)
    asaas_customer_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Address fields
    address = models.CharField(max_length=255, verbose_name='Endereço')
    city = models.CharField(max_length=100, verbose_name='Cidade')
    state = BRStateField(verbose_name='Estado')
    postal_code = BRPostalCodeField(verbose_name='CEP')
    
    # Partner company for complimentary tickets
    partner_company = models.CharField(max_length=200, blank=True, verbose_name='Empresa Parceira', default=None, null=True)
    
    # Privacy consent (LGPD compliance)
    privacy_consent = models.BooleanField(default=False, verbose_name='Consentimento LGPD')
    marketing_consent = models.BooleanField(default=False, verbose_name='Aceita Marketing')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'cpf']

    objects = CustomUserManager()

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


class TicketClass(models.Model):
    TICKET_TYPES = [
        ('geral', 'Geral'),
        ('cortesia', 'Cortesia'),
        ('vip', 'VIP'),
    ]
    
    name = models.CharField(max_length=100, default='Geral', verbose_name='Nome')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço')
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPES, default='geral')
    description = models.TextField(blank=True, verbose_name='Descrição')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_classes')

    class Meta:
        verbose_name = 'Classe de Ingresso'
        verbose_name_plural = 'Classes de Ingresso'

    def __str__(self):
        return f"{self.name} - R$ {self.price}"

# Order QuerySet
class OrderQuerySet(models.QuerySet):
    def paid(self):
        return self.filter(status='pago')
    
    def active(self):
        return self.filter(state='ativo')
    
    def for_event(self, event_id):
        return self.filter(items__event_id=event_id)
        
    def expired(self):
        return self.filter(expires_at__lt=timezone.now())

class Order(models.Model):
    # Define QuerySet
    objects = OrderQuerySet.as_manager()

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('falha', 'Falha'),
        ('estornado', 'Estornado'),
    ]

    STATE_CHOICES = [
        ('ativo', 'Ativo'),
        ('cancelado', 'Cancelado'),
        ('expirado', 'Expirado'),
    ]

    PAYMENT_METHODS = [
        ('pix', 'PIX'),
        ('boleto', 'Boleto Bancário'),
        ('credit_card', 'Cartão de Crédito'),
        ('debit_card', 'Cartão de Débito'),
        ('cortesia', 'Cortesia'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário')
    
    # Pricing
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Valor Total')
    
    # Order tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente')
    state = models.CharField(max_length=30, choices=STATE_CHOICES, default='ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expira em')
    redemption_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Token de Resgate')
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
    payment_id = models.CharField(max_length=200, blank=True, verbose_name='ID do Pagamento')  # External payment reference
    payment_data = models.JSONField(default=dict, blank=True)  # Store PIX QR codes, boleto URLs, etc.
    paid_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Pedido #{self.id} - {self.user.email} - R$ {self.total_amount}"

    @property
    def is_paid(self):
        return self.status in ['pago', 'cortesia_confirmada']
    
    def clean(self):
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError("Expiration date must be in the future")

    def calculate_total(self):
        return self.items.aggregate(
            total=models.Sum('subtotal')
        )['total'] or 0

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket_class = models.ForeignKey(TicketClass, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")
        if self.unit_price < 0:
            raise ValidationError("Price cannot be negative")

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

class PaymentWebhook(models.Model):
    """Store payment webhook data for audit and debugging"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='webhooks')
    provider = models.CharField(max_length=50)  # 'mercadopago', 'pagseguro', etc.
    webhook_id = models.CharField(max_length=200, blank=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Webhook de Pagamento'
        verbose_name_plural = 'Webhooks de Pagamento'


class Ticket(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tickets', verbose_name='Pedido')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='tickets', verbose_name='Item do Pedido')
    qr_code = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Código QR')
    is_redeemed = models.BooleanField(default=False, verbose_name='Resgatado')
    issued_at = models.DateTimeField(auto_now_add=True)
    redeemed_at = models.DateTimeField(null=True, blank=True, verbose_name='Resgatado em')
    redeemed_by_staff = models.CharField(max_length=100, blank=True, verbose_name='Resgatado por')
    
    # Optional individual ticket holder info (for corporate purchases)
    holder_name = models.CharField(max_length=150, blank=True, verbose_name='Nome do Portador')
    holder_email = models.EmailField(blank=True, verbose_name='E-mail do Portador')

    class Meta:
        ordering = ['issued_at']
        verbose_name = 'Ingresso'
        verbose_name_plural = 'Ingressos'
        indexes = [
            models.Index(fields=['qr_code']),
        ]

    def __str__(self):
        event = self.order.items.first().event if self.order.items.exists() else "No Event"
        return f"Ingresso {str(self.qr_code)[:8]} - {event}"

    @property
    def user(self):
        return self.order.user

    def redeem(self, staff_member=None):
        """Mark ticket as redeemed"""
        if self.is_redeemed:
            raise ValidationError("Ingresso já foi resgatado")
        
        self.is_redeemed = True
        self.redeemed_at = timezone.now()
        if staff_member:
            self.redeemed_by_staff = staff_member
        self.save()
    
    @cached_property
    def event_details(self):
        event = self.order_item.event
        return {
            'name': event.name,
            'date': event.start.strftime('%d/%m/%Y às %H:%M'),
            'location': event.location,
            'city': event.city,
            'state': event.state
        }


class EmailLog(models.Model):
    """Track email notifications sent to users"""
    EMAIL_TYPES = [
        ('ticket_confirmation', 'Confirmação de Ingresso'),
        ('complimentary_link', 'Link de Cortesia'),
        ('payment_confirmation', 'Confirmação de Pagamento'),
        ('payment_reminder', 'Lembrete de Pagamento'),
        ('event_reminder', 'Lembrete do Evento'),
        ('event_update', 'Atualização do Evento'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário')
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES, verbose_name='Tipo')
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200, verbose_name='Assunto')
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True, verbose_name='Sucesso')
    error_message = models.TextField(blank=True, verbose_name='Mensagem de Erro')

    class Meta:
        verbose_name = 'Log de E-mail'
        verbose_name_plural = 'Logs de E-mail'
        ordering = ['-sent_at']