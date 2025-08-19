import factory
from faker import Faker
from factory.django import DjangoModelFactory
from datetime import timedelta
from django.contrib.auth.hashers import make_password

from mainForm.models import (
    Event, User, TicketClass, Order, PaymentWebhook, Ticket, EmailLog, OrderItem
)

fake = Faker("pt_BR")

BRAZIL_STATES = ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'GO', 'PE', 'CE']
TICKET_TYPES = {
    'geral': 'Geral',
    'cortesia': 'Cortesia',
    'vip': 'VIP',
}


def generate_cpf():
    # Generates a valid Brazilian CPF with check digits
    numbers = [fake.random_int(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum((len(numbers) + 1 - i) * v for i, v in enumerate(numbers)) % 11
        numbers.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, numbers[:3]))}.{''.join(map(str, numbers[3:6]))}.{''.join(map(str, numbers[6:9]))}-{''.join(map(str, numbers[9:]))}"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker('email')
    full_name = factory.Faker('name', locale='pt_BR')
    phone = factory.Faker('phone_number', locale='pt_BR')
    cpf = factory.LazyFunction(generate_cpf)
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=110)
    # Ensure required fields are always provided
    address = factory.Faker('street_address', locale='pt_BR')
    city = factory.Faker('city', locale='pt_BR')
    state = factory.Faker('random_element', elements=BRAZIL_STATES)
    postal_code = factory.Faker('postcode', locale='pt_BR')
    partner_company = factory.Faker('company', locale='pt_BR')
    privacy_consent = True
    marketing_consent = factory.Faker('boolean')
    password = factory.LazyFunction(lambda: make_password('testpass123'))
    is_active = True


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    name = factory.Faker('catch_phrase', locale='pt_BR')
    description = factory.Faker('text', max_nb_chars=500)
    start = factory.Faker('future_datetime', end_date='+30d')
    end = factory.LazyAttribute(lambda obj: obj.start + timedelta(hours=fake.random_int(1, 8)))
    location = factory.Faker('company', locale='pt_BR')
    city = factory.Faker('city', locale='pt_BR')
    state = factory.Faker('random_element', elements=BRAZIL_STATES)
    speakers = factory.Faker('name', locale='pt_BR')
    is_active = True

    class Params:
        past_event = factory.Trait(
            start=factory.Faker('past_datetime', start_date='-30d'),
            end=factory.LazyAttribute(lambda obj: obj.start + timedelta(hours=2))
        )
        inactive = factory.Trait(is_active=False)
        multi_day = factory.Trait(
            end=factory.LazyAttribute(lambda obj: obj.start + timedelta(days=2))
        )


class TicketClassFactory(DjangoModelFactory):
    class Meta:
        model = TicketClass

    ticket_type = factory.Faker('random_element', elements=list(TICKET_TYPES.keys()))
    name = factory.LazyAttribute(lambda obj: TICKET_TYPES[obj.ticket_type])
    price = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    description = factory.Faker('text', max_nb_chars=200)
    event = factory.SubFactory(EventFactory)

    class Params:
        free_ticket = factory.Trait(
            ticket_type='cortesia',
            price=0
        )


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    total_amount = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    status = factory.Faker('random_element', elements=['pendente', 'pago', 'falha', 'estornado'])
    expires_at = factory.Faker('future_datetime', end_date='+7d')
    payment_method = factory.Faker('random_element', elements=['pix', 'boleto', 'credit_card', 'debit_card', 'cortesia'])
    payment_id = factory.Faker('uuid4')
    payment_data = factory.Faker('pydict', nb_elements=3, value_types=[str, int, bool])

    class Params:
        paid = factory.Trait(
            status='pago',
            paid_at=factory.Faker('past_datetime', start_date='-30d')
        )
        courtesy = factory.Trait(
            status='pago',
            payment_method='cortesia',
            total_amount=0
        )
        expired = factory.Trait(
            status='pendente',
            expires_at=factory.Faker('past_datetime', start_date='-30d')
        )

class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    # Create an Order and a TicketClass automatically
    order = factory.SubFactory(OrderFactory)
    ticket_class = factory.SubFactory(TicketClassFactory)
    
    # Ensure the OrderItem's event is the same as its TicketClass's event
    event = factory.SelfAttribute('ticket_class.event')
    
    quantity = 1
    
    # Use the price from the related ticket_class
    unit_price = factory.SelfAttribute('ticket_class.price')
    
    # Calculate the subtotal based on the other fields
    subtotal = factory.LazyAttribute(lambda o: o.unit_price * o.quantity)

class PaymentWebhookFactory(DjangoModelFactory):
    class Meta:
        model = PaymentWebhook

    order = factory.SubFactory(OrderFactory)
    provider = factory.Faker('random_element', elements=['mercadopago', 'pagseguro', 'stripe', 'asaas'])
    webhook_id = factory.Faker('uuid4')
    event_type = factory.Faker('random_element', elements=['payment.created', 'payment.approved', 'payment.cancelled'])
    payload = factory.LazyFunction(lambda: {
        'id': fake.uuid4(),
        'status': fake.random_element(['approved', 'pending', 'cancelled'])
    })
    processed = False

    class Params:
        is_processed = factory.Trait(processed=True)
        asaas_provider = factory.Trait(
            provider='asaas',
            event_type='payment.updated'
        )


class TicketFactory(DjangoModelFactory):
    class Meta:
        model = Ticket

    order_item = factory.SubFactory(OrderItemFactory)
    order = factory.SelfAttribute('order_item.order')
    
    holder_name = factory.Faker('name', locale='pt_BR')
    holder_email = factory.Faker('email')

    @factory.post_generation
    def user(self, create, extracted, **kwargs):
        """
        Allow passing user=... to TicketFactory. Apply it to the related Order,
        since Ticket.user is a read-only property that proxies order.user.
        """
        if extracted:
            self.order.user = extracted
            if create:
                self.order.save(update_fields=['user'])

    @factory.post_generation
    def event(self, create, extracted, **kwargs):
        """
        Allow passing event=... to TicketFactory. Apply it to the related
        OrderItem and keep TicketClass.event consistent as well.
        """
        if extracted:
            self.order_item.event = extracted
            # Keep TicketClass.event consistent with the new event
            if self.order_item.ticket_class.event_id != extracted.id:
                self.order_item.ticket_class.event = extracted
                if create:
                    self.order_item.ticket_class.save(update_fields=['event'])
            if create:
                self.order_item.save(update_fields=['event'])

    class Params:
        redeemed = factory.Trait(
            is_redeemed=True,
            redeemed_at=factory.Faker('past_datetime', start_date='-7d'),
            redeemed_by_staff=factory.Faker('name', locale='pt_BR')
        )
        anonymous = factory.Trait(
            holder_name='',
            holder_email=''
        )


class EmailLogFactory(DjangoModelFactory):
    class Meta:
        model = EmailLog

    user = factory.SubFactory(UserFactory)
    email_type = factory.Faker('random_element', elements=['ticket_confirmation', 'payment_confirmation', 'event_reminder'])
    order = factory.SubFactory(OrderFactory)
    subject = factory.Faker('sentence', nb_words=6)
    success = True

    class Params:
        failed = factory.Trait(
            success=False,
            error_message=factory.Faker('sentence')
        )
        no_order = factory.Trait(order=None)
