from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "buyer", "seller", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("buyer__username", "seller__username", "item__title")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "is_hidden", "created_at")
    list_filter = ("is_hidden", "created_at")
    search_fields = ("sender__username", "content")
    actions = ["hide_messages", "unhide_messages"]

    def hide_messages(self, request, queryset):
        queryset.update(is_hidden=True)

    def unhide_messages(self, request, queryset):
        queryset.update(is_hidden=False)
