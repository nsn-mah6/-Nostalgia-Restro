from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ActivityLog, CustomUser


@receiver(post_save, sender=CustomUser)
def sync_user_role_group(sender, instance, **kwargs):
    from django.contrib.auth.models import Group

    for group in instance.groups.all():
        if group.name in {"Admin", "Manager", "Waiter", "Cashier", "Kitchen Staff", "Inventory Staff"}:
            instance.groups.remove(group)

    role_name = instance.get_role_display()
    if not role_name:
        return

    group, _ = Group.objects.get_or_create(name=role_name)
    instance.groups.add(group)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        action="login",
        details="User logged in to the system.",
        ip_address=request.META.get("REMOTE_ADDR"),
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user is not None:
        ActivityLog.objects.create(
            user=user,
            action="logout",
            details="User logged out of the system.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
