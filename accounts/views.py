from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import UserProfile
from .forms import ProfileInterestsForm
from marketplace.models import Item
from django.db.models import Q


@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileInterestsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
    else:
        form = ProfileInterestsForm(instance=profile)

    # ✅ Recommandations V1 (centres d’intérêt)
    reco_v1 = Item.objects.filter(
        category__in=profile.interests.all(),
        status="APPROVED",
        is_sold=False
    ).distinct()[:6]

    # ✅ Recommandations V2 (centres + parcours)
    viewed_items = request.user.item_views.values_list("item__category", flat=True)

    reco_v2 = Item.objects.filter(
        Q(category__in=profile.interests.all()) |
        Q(category__in=viewed_items),
        status="APPROVED",
        is_sold=False
    ).distinct()[:6]

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "reco_v1": reco_v1,
            "reco_v2": reco_v2,
        }
    )
