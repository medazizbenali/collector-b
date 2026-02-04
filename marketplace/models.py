from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    title = models.CharField(max_length=200)
    description = models.TextField()

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="items"
    )

    price_cents = models.PositiveIntegerField()
    shipping_cents = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    is_sold = models.BooleanField(default=False)

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_cents(self):
        return self.price_cents + self.shipping_cents

    def __str__(self):
        return self.title


class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="items/")

    def __str__(self):
        return f"Image #{self.id} for Item #{self.item_id}"


class PriceHistory(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="price_history")
    old_price_cents = models.PositiveIntegerField()
    new_price_cents = models.PositiveIntegerField()
    changed_at = models.DateTimeField(auto_now_add=True)


# ✅ V2 – Parcours utilisateur (IMPORTANT)
class ItemViewEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
