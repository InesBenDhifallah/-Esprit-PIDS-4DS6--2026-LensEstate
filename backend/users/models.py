from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone      = models.CharField(max_length=20, blank=True)
    avatar     = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # these two lines fix the clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True
    )

    def __str__(self):
        return self.email


class Favorite(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    listing_id = models.IntegerField()   # references listings table by id
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing_id')  # no duplicate favorites

    def __str__(self):
        return f"{self.user.email} → listing {self.listing_id}"


class SavedSearch(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    name       = models.CharField(max_length=100)
    filters    = models.JSONField()          # e.g. {"city": "Tunis", "max_price": 200000}
    alert_on   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.name}"


class ChatSession(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role} @ {self.created_at}"