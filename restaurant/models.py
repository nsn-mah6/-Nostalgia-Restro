from django.contrib.auth.models import Group
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("waiter", "Waiter"),
        ("cashier", "Cashier"),
        ("kitchen_staff", "Kitchen Staff"),
        ("inventory_staff", "Inventory Staff"),
    ]

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="waiter")
    phone_number = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_role_group()

    def _sync_role_group(self):
        role_group_name = self.get_role_display()
        if not role_group_name:
            return

        for group in self.groups.all():
            if group.name in {choice[1] for choice in self.ROLE_CHOICES}:
                self.groups.remove(group)

        group, _ = Group.objects.get_or_create(name=role_group_name)
        self.groups.add(group)


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("password_reset", "Password Reset"),
        ("profile_updated", "Profile Updated"),
        ("created_user", "Created User"),
        ("updated_user", "Updated User"),
        ("deactivated_user", "Deactivated User"),
        ("activated_user", "Activated User"),
        ("order_created", "Order Created"),
        ("order_updated", "Order Updated"),
        ("payment_processed", "Payment Processed"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=40, choices=ACTION_CHOICES, default="login")
    details = models.TextField(blank=True)
    target_model = models.CharField(max_length=100, blank=True, default="")
    target_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.get_action_display()}"


class InventoryItem(models.Model):
    name = models.CharField(max_length=100)
    stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    unit = models.CharField(max_length=30, default="units")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.stock} {self.unit})"


class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ("starter", "Starter"),
        ("main", "Main Course"),
        ("dessert", "Dessert"),
        ("beverage", "Beverage"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="main")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} - ${self.price}"


class RecipeItem(models.Model):
    menu_item = models.ForeignKey(MenuItem, related_name="recipe_items", on_delete=models.CASCADE)
    ingredient = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity_required = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.menu_item.name} needs {self.quantity_required} {self.ingredient.unit} of {self.ingredient.name}"


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ("dine_in", "Dine In"),
        ("takeaway", "Takeaway"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("ready", "Ready"),
    ]

    customer_name = models.CharField(max_length=120, default="Walk-in Customer")
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default="dine_in")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"


class Payment(models.Model):
    METHOD_CHOICES = [
        ("cash", "Cash"),
        ("qr", "QR Payment"),
        ("card", "Card"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.order} paid by {self.payment_method}"
