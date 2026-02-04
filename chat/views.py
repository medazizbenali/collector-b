from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden

from marketplace.models import Item
from .models import Conversation, Message


@login_required
def start_conversation(request, item_id):
    item = get_object_or_404(Item, id=item_id, status="APPROVED")
    buyer = request.user
    seller = item.seller

    if buyer.id == seller.id:
        return HttpResponseForbidden("Tu ne peux pas te contacter toi-même.")

    conv, _ = Conversation.objects.get_or_create(
        item=item,
        buyer=buyer,
        seller=seller
    )
    return redirect("conversation_detail", conversation_id=conv.id)


@login_required
def my_conversations(request):
    user = request.user
    conversations = Conversation.objects.filter(Q(buyer=user) | Q(seller=user)).order_by("-updated_at")
    return render(request, "chat/my_conversations.html", {"conversations": conversations})


@login_required
def conversation_detail(request, conversation_id):
    user = request.user
    conv = get_object_or_404(Conversation, id=conversation_id)

    # sécurité : seul buyer ou seller peut accéder
    if user.id not in [conv.buyer_id, conv.seller_id]:
        return HttpResponseForbidden("Accès refusé.")

    # post message
    if request.method == "POST":
        content = (request.POST.get("content") or "").strip()
        if content:
            Message.objects.create(conversation=conv, sender=user, content=content)
            conv.save()  # update updated_at
        return redirect("conversation_detail", conversation_id=conv.id)

    # on cache les messages modérés si pas admin
    if user.is_staff:
        messages = conv.messages.all().order_by("created_at")
    else:
        messages = conv.messages.filter(is_hidden=False).order_by("created_at")

    return render(request, "chat/conversation_detail.html", {
        "conversation": conv,
        "messages": messages
    })
