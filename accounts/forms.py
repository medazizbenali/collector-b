from django import forms
from .models import UserProfile


class ProfileInterestsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["interests"]
        widgets = {
            "interests": forms.CheckboxSelectMultiple()
        }
