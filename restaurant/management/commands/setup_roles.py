from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from restaurant.models import CustomUser, InventoryItem, MenuItem, Order, OrderItem, Payment, RecipeItem


ROLE_PERMISSIONS = {
    "Admin": [
        "add_customuser", "change_customuser", "delete_customuser", "view_customuser",
        "add_inventoryitem", "change_inventoryitem", "delete_inventoryitem", "view_inventoryitem",
        "add_menuitem", "change_menuitem", "delete_menuitem", "view_menuitem",
        "add_order", "change_order", "delete_order", "view_order",
        "add_orderitem", "change_orderitem", "delete_orderitem", "view_orderitem",
        "add_payment", "change_payment", "delete_payment", "view_payment",
        "add_recipeitem", "change_recipeitem", "delete_recipeitem", "view_recipeitem",
    ],
    "Manager": [
        "view_customuser", "change_customuser",
        "view_inventoryitem", "change_inventoryitem",
        "view_menuitem", "change_menuitem",
        "view_order", "change_order",
        "view_payment", "change_payment",
        "view_recipeitem",
    ],
    "Waiter": [
        "view_menuitem", "view_order",
        "add_order", "change_order",
    ],
    "Cashier": [
        "view_order", "change_order",
        "view_payment", "add_payment", "change_payment",
    ],
    "Kitchen Staff": [
        "view_order", "change_order",
        "view_menuitem",
    ],
    "Inventory Staff": [
        "view_inventoryitem", "change_inventoryitem",
        "view_menuitem",
    ],
}


class Command(BaseCommand):
    help = "Creates role-based permission groups for the restaurant staff system."

    def handle(self, *args, **options):
        for role_name, permission_codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            permissions = Permission.objects.filter(codename__in=permission_codenames)
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"Configured group: {role_name}"))

        if not CustomUser.objects.filter(username="admin").exists():
            CustomUser.objects.create_superuser(
                username="admin",
                email="admin@restaurant.local",
                password="admin123",
                role="admin",
            )
            self.stdout.write(self.style.SUCCESS("Created default admin account: admin / admin123"))
