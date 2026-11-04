from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class StaffForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone_number", "role", "is_active"]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number"]
