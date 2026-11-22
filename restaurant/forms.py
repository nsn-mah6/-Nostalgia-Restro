from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import InventoryItem, RestaurantTable, TableBooking

User = get_user_model()


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "stock", "reorder_level", "unit"]


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
        fields = ["first_name", "last_name", "email", "phone_number", "profile_picture"]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class RestaurantTableForm(forms.ModelForm):
    class Meta:
        model = RestaurantTable
        fields = ["table_number", "name", "capacity", "location", "is_available"]
        widgets = {
            "table_number": forms.NumberInput(attrs={"min": 1}),
            "capacity": forms.NumberInput(attrs={"min": 1}),
        }


class TableBookingForm(forms.ModelForm):
    class Meta:
        model = TableBooking
        fields = [
            "customer_name",
            "phone",
            "email",
            "table",
            "party_size",
            "booking_date",
            "booking_time",
            "status",
            "notes",
        ]
        widgets = {
            "booking_date": forms.DateInput(attrs={"type": "date"}),
            "booking_time": forms.TimeInput(attrs={"type": "time"}),
            "party_size": forms.NumberInput(attrs={"min": 1}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        table_field = self.fields["table"]
        table_field.empty_label = "Select a table"
        if self.instance.pk and self.instance.table_id:
            table_field.queryset = RestaurantTable.objects.filter(
                Q(is_available=True) | Q(pk=self.instance.table_id)
            ).order_by("table_number")
        else:
            table_field.queryset = RestaurantTable.objects.filter(is_available=True).order_by("table_number")

    def clean(self):
        cleaned = super().clean()
        table = cleaned.get("table")
        booking_date = cleaned.get("booking_date")
        booking_time = cleaned.get("booking_time")
        party_size = cleaned.get("party_size")

        if table and party_size and party_size > table.capacity:
            raise ValidationError(f"{table} does not have enough seats for this party.")

        is_current_table = (
            self.instance.pk
            and self.instance.table_id
            and table
            and table.pk == self.instance.table_id
        )
        if table and not table.is_available and not is_current_table:
            raise ValidationError(f"{table} is currently unavailable.")

        if table and booking_date and booking_time:
            conflicts = TableBooking.objects.filter(
                table=table,
                booking_date=booking_date,
                booking_time=booking_time,
            ).exclude(status="cancelled")
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise ValidationError("This table already has a booking at that date and time.")

        return cleaned
