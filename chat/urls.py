from django.urls import path
from .views import my_conversations, conversation_detail, start_conversation

urlpatterns = [
    path("", my_conversations, name="my_conversations"),
    path("start/<int:item_id>/", start_conversation, name="start_conversation"),
    path("<int:conversation_id>/", conversation_detail, name="conversation_detail"),
]
