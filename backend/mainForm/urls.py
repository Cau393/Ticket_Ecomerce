from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserRegistrationAPIView, 
    UserMeView, 
    EventViewSet, 
    OrderViewSet, 
    AsaasWebHookView,
    TicketAssignmentView,
    LoginAPIView,
    LogoutAPIView,
    CsrfTokenView,
)

# Create a router and register our viewsets.
router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'orders', OrderViewSet, basename='order')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    # This includes all generated ViewSet URLs (e.g., /api/orders/, /api/events/, etc.)
    path('', include(router.urls)), 

    # Auth endpoints
    path('auth/csrf/', CsrfTokenView.as_view(), name='auth-csrf'),
    path('auth/login/', LoginAPIView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='auth-logout'),
    path('auth/register/', UserRegistrationAPIView.as_view(), name='user-register'),

    # Standalone views
    path('users/me/', UserMeView.as_view(), name='user-me'),
    path('webhooks/asaas/', AsaasWebHookView.as_view(), name='asaas-webhook'),
    path('courtesy/<int:pk>/', TicketAssignmentView.as_view(), name='ticket-courtesy'),
    path('tickets/<int:pk>/assign/', TicketAssignmentView.as_view(), name='ticket-assign'),
]