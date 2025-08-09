# Change the import to get your custom model
from .models import User
from rest_framework import serializers

# Change the base class to ModelSerializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # This field list now correctly matches your model
        fields = ['name', 'email', 'token', 'presence']