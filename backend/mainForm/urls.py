# mainForm/urls.py

from django.urls import path
from .views import UserCreateAPIView, UserCheckInAPIView # Import your view from the local views.py

# This list is what Django will look at to match the requested URL.
urlpatterns = [
    # Defines a URL pattern for creating a user.
    path('users/add/', UserCreateAPIView.as_view(), name='user-add'),
    # Defines a URL pattern for checking in a user.
    path('users/check-in/<str:token>/', UserCheckInAPIView.as_view(), name='user-check-in'),
]