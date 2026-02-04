from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from .models import Item, ItemViewEvent
from .forms import ItemCreateForm


def catalog(request):
    items = Item.objects.filter(
        status="APPROVED", is_sold=False
    ).order_by("-created_at")

    return render(request, "marketplace/item_list.html", {"items": items})


def item_partial(request):
    q = request.GET.get("q", "").strip()

    items = Item.objects.filter(status="APPROVED", is_sold=False)

    if q:
        items = items.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    return render(request, "marketplace/_item_list.html", {"items": items})


def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id, status="APPROVED")

    if request.user.is_authenticated:
        ItemViewEvent.objects.create(user=request.user, item=item)

    return render(request, "marketplace/item_detail.html", {"item": item})


@login_required
def item_create(request):
    if request.method == "POST":
        form = ItemCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(seller=request.user)
            return redirect("catalog")
    else:
        form = ItemCreateForm()

    return render(request, "marketplace/item_create.html", {"form": form})
