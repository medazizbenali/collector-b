from django import forms
from .models import Item


class ItemCreateForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["title", "description", "category", "price_cents", "shipping_cents"]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "mt-2 w-full rounded-2xl bg-slate-950/40 border border-white/10 px-4 py-3 text-slate-100",
                "placeholder": "Ex: Carte Pokémon Dracaufeu",
            }),
            "description": forms.Textarea(attrs={
                "class": "mt-2 w-full rounded-2xl bg-slate-950/40 border border-white/10 px-4 py-3 text-slate-100",
                "rows": 5,
                "placeholder": "Décris l’objet, l’état, l’année, etc.",
            }),
            "category": forms.Select(attrs={
                "class": "mt-2 w-full rounded-2xl bg-slate-950/40 border border-white/10 px-4 py-3 text-slate-100",
            }),
            "price_cents": forms.NumberInput(attrs={
                "class": "mt-2 w-full rounded-2xl bg-slate-950/40 border border-white/10 px-4 py-3 text-slate-100",
                "placeholder": "ex: 1299",
                "min": 0,
            }),
            "shipping_cents": forms.NumberInput(attrs={
                "class": "mt-2 w-full rounded-2xl bg-slate-950/40 border border-white/10 px-4 py-3 text-slate-100",
                "placeholder": "ex: 300",
                "min": 0,
            }),
        }
