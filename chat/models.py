from django.db import models
from django.contrib.auth.models import User
from marketplace.models import Item


class Conversation(models.Model):
    """
    Une conversation est liée à 1 item, entre un acheteur et un vendeur.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="conversations")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_conversations")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("item", "buyer", "seller")

    def __str__(self):
        return f"Conv#{self.id} item#{self.item_id} {self.buyer.username}->{self.seller.username}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()

    is_hidden = models.BooleanField(default=False)  # modération admin
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg#{self.id} conv#{self.conversation_id} by {self.sender.username}"
