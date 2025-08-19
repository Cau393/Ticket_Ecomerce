from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

from .factories import (
    UserFactory,
    EventFactory,
    TicketClassFactory,
    OrderFactory,
)
from mainForm.models import User, Order, OrderItem


class ViewTests(APITestCase):
    def setUp(self):
        self.user_password = "testpass123"
        self.user = UserFactory(password=self.user_password)

    # ---------- USER REGISTRATION ----------
    def test_user_registration_success(self):
        """
        Ensure a new user can be registered successfully.
        """
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'cpf': '70123710138',
            'password': 'strongpassword123',
            'address': 'Rua Teste, 123',
            'city': 'São Paulo',
            'state': 'SP',
            'postal_code': '01234-567'
        }
        url = reverse('user-register')
        response = self.client.post(url, data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)  # 1 from setUp + new one
        self.assertEqual(User.objects.latest('id').email, 'test@example.com')

    def test_user_registration_fail_no_email(self):
        """
        Registration should fail if email is missing.
        """
        data = {
            'full_name': 'Test User',
            'cpf': '12345678901',
            'password': 'pw',
            'address': 'Rua Teste, 123',
            'city': 'São Paulo',
            'state': 'SP',
            'postal_code': '01234-567'
        }
        url = reverse('user-register')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_fail_missing_required_fields(self):
        """
        Registration should fail if required fields are missing.
        """
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'cpf': '12345678901',
            'password': 'strongpassword123'
            # Missing address, city, state, postal_code
        }
        url = reverse('user-register')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- EVENT LISTING ----------
    def test_list_events_only_active_future(self):
        """
        Only active, upcoming events should be listed.
        """
        EventFactory()  # active & future
        EventFactory(past_event=True)  # past
        EventFactory(inactive=True)  # inactive

        url = reverse('event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Since no pagination is configured, data is returned directly as a list
        self.assertEqual(len(response.data), 1)

    # ---------- ORDER LISTING ----------
    def test_list_orders_unauthenticated(self):
        """
        Unauthenticated users should not be able to list orders.
        """
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_orders_authenticated_only_own(self):
        """
        Authenticated user should only see their own orders.
        """
        other_user = UserFactory()
        OrderFactory(user=self.user)
        OrderFactory(user=other_user)

        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Since no pagination is configured, data is returned directly as a list
        self.assertEqual(len(response.data), 1)

    # ---------- ORDER CREATION ----------
    def test_create_order_success(self):
        """
        Authenticated user can create a new order.
        """
        ticket_class = TicketClassFactory(price=100.00)
        payload = {
            "items": [
                {"ticket_class_id": ticket_class.id, "quantity": 2}
            ]
        }

        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(float(response.data['total_amount']), 200.00)

    def test_create_order_fail_invalid_ticket_class(self):
        """
        Creating an order with a non-existent ticket class should fail.
        """
        payload = {
            "items": [
                {"ticket_class_id": 9999, "quantity": 1}
            ]
        }
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_fail_unauthenticated(self):
        """
        Unauthenticated users cannot create orders.
        """
        ticket_class = TicketClassFactory(price=100.00)
        payload = {
            "items": [
                {"ticket_class_id": ticket_class.id, "quantity": 1}
            ]
        }
        url = reverse('order-list')
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---------- PAYMENT CREATION (COMPRA FLOW) ----------
    @patch('mainForm.services.AsaasService.create_charge_for_order')
    def test_create_payment_charge_success(self, mock_create_charge):
        """
        Payment charge creation should call AsaasService and return its response.
        """
        order = OrderFactory(user=self.user, status='pendente')
        mock_response = {"id": "pay_mock_id", "status": "PENDING", "value": 100.00}
        mock_create_charge.return_value = mock_response

        self.client.force_authenticate(user=self.user)
        url = reverse('order-create-payment-charge', args=[order.id])
        response = self.client.post(url, {"billing_type": "PIX"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_create_charge.assert_called_once_with(order, billing_type="PIX")
        self.assertEqual(response.data, mock_response)

    @patch('mainForm.services.AsaasService.create_charge_for_order')
    def test_create_payment_charge_unauthenticated(self, mock_create_charge):
        """
        Unauthenticated users cannot create payment charges.
        """
        order = OrderFactory(user=self.user, status='pendente')
        url = reverse('order-create-payment-charge', args=[order.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_create_charge.assert_not_called()

    @patch('mainForm.services.AsaasService.create_charge_for_order')
    def test_create_payment_charge_invalid_billing_type(self, mock_create_charge):
        """
        Invalid billing types should be rejected.
        """
        order = OrderFactory(user=self.user, status='pendente')
        self.client.force_authenticate(user=self.user)
        url = reverse('order-create-payment-charge', args=[order.id])
        response = self.client.post(url, {"billing_type": "INVALID_TYPE"})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unsupported billing_type", response.data["error"])
        mock_create_charge.assert_not_called()

    def test_create_payment_charge_other_user_order(self):
        """
        Users cannot create payment charges for orders that don't belong to them.
        """
        other_user = UserFactory()
        order = OrderFactory(user=other_user, status='pendente')
        
        self.client.force_authenticate(user=self.user)
        url = reverse('order-create-payment-charge', args=[order.id])
        response = self.client.post(url, {"billing_type": "PIX"})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- CORTESIA FLOW ----------
    def test_create_free_order_cortesia(self):
        """
        Cortesia flow: order total should be zero and status 'pago' immediately.
        """
        ticket_class = TicketClassFactory(price=0.00)
        payload = {
            "items": [
                {"ticket_class_id": ticket_class.id, "quantity": 1}
            ]
        }
        self.client.force_authenticate(user=self.user)
        url = reverse('order-list')
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.total_amount, 0.00)
        self.assertEqual(order.status, 'pago')

    # ---------- USER PROFILE ----------
    def test_user_profile_authenticated(self):
        """
        Authenticated users can access their profile.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse('user-me')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['full_name'], self.user.full_name)

    def test_user_profile_unauthenticated(self):
        """
        Unauthenticated users cannot access profile.
        """
        url = reverse('user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
