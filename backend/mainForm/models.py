from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    # Token for QR Code
    token = models.CharField(max_length=100, unique=True)
    # Presence
    presence = models.BooleanField(default=False)
    # Event type
    event = models.CharField(max_length=100, blank=True, default='')
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    class Meta:
        ordering = ['name']