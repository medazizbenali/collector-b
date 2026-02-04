from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from marketplace.models import Item, Category


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    interests = models.ManyToManyField(
        Category,
        blank=True,
        related_name="interested_users"
    )

    def __str__(self):
        return f"Profile({self.user.username})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class ItemViewEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="item_views"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="view_events"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"View({self.user.username} -> item#{self.item_id})"
