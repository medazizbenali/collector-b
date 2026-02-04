from django.urls import path
from . import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("items/partial/", views.item_partial, name="item_partial"),
    path("items/<int:item_id>/", views.item_detail, name="item_detail"),
    path("items/create/", views.item_create, name="item_create"),
]
