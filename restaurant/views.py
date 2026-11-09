import csv
import io
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import F, Q, Sum
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, StaffForm
from .models import ActivityLog, CustomUser, InventoryItem, MenuItem, Order, OrderItem, Payment
from .utils import forecast_sales, get_revenue_forecast


def log_activity(user, action, details, request=None, target_model="", target_id=None):
    ip_address = None
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details,
        target_model=target_model,
        target_id=target_id,
        ip_address=ip_address,
    )


def role_required(*roles):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not request.user.is_active:
                return redirect("login")
            if roles and request.user.role not in roles:
                messages.warning(request, "You do not have permission to access that page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def role_dashboard_template(role):
    templates = {
        "admin": "restaurant/dashboard_admin.html",
        "manager": "restaurant/dashboard_manager.html",
        "waiter": "restaurant/dashboard_waiter.html",
        "cashier": "restaurant/dashboard_cashier.html",
        "kitchen_staff": "restaurant/dashboard_kitchen.html",
        "inventory_staff": "restaurant/dashboard_inventory.html",
    }
    return templates.get(role, "restaurant/dashboard.html")


@login_required
@role_required("admin", "manager", "waiter", "cashier", "kitchen_staff", "inventory_staff")
def dashboard(request):
    search_query = (request.GET.get("q") or "").strip()
    total_revenue = Payment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    pending_orders = Order.objects.filter(status="pending").count()
    total_orders = Order.objects.count()
    low_stock = InventoryItem.objects.filter(stock__lte=F("reorder_level")).count()
    recent_orders = Order.objects.prefetch_related("items__menu_item").order_by("-created_at")[:6]
    prediction = forecast_sales(7)
    template_name = role_dashboard_template(request.user.role)

    if search_query:
        recent_orders = (
            Order.objects.filter(
                Q(customer_name__icontains=search_query)
                | Q(items__menu_item__name__icontains=search_query)
            )
            .prefetch_related("items__menu_item")
            .order_by("-created_at")
            .distinct()[:6]
        )

    if request.user.role == "admin":
        sales_data = []
        today = timezone.now().date()
        for offset in range(7):
            day = today - timedelta(days=6 - offset)
            total = (
                Order.objects.filter(created_at__date=day).aggregate(total=Sum("total_amount"))["total"]
                or Decimal("0")
            )
            sales_data.append({"label": day.strftime("%a"), "amount": float(total)})

        max_sale = max((item["amount"] for item in sales_data), default=0) or 1
        chart_points = []
        for index, item in enumerate(sales_data):
            x = 40 + (index * 82)
            y = 210 - ((item["amount"] / max_sale) * 150)
            chart_points.append({"x": x, "y": y})

        chart_line = "M " + " L ".join(f"{point['x']},{point['y']}" for point in chart_points)
        chart_fill = "M 40,230 " + " ".join(f"L {point['x']},{point['y']}" for point in chart_points) + " L 600,230 Z"

        top_items = list(
            OrderItem.objects.values("menu_item__name")
            .annotate(total_qty=Sum("quantity"), total_revenue=Sum("subtotal"))
            .order_by("-total_qty")[:5]
        )
        for item in top_items:
            item["display_name"] = item["menu_item__name"]
            item["revenue"] = float(item["total_revenue"] or 0)
            item["quantity"] = int(item["total_qty"] or 0)

        if search_query:
            active_orders = list(
                Order.objects.filter(status__in=["pending", "preparing", "ready"], customer_name__icontains=search_query)
                .order_by("-created_at")[:4]
            )
            recent_payments = list(
                Payment.objects.filter(order__customer_name__icontains=search_query)
                .select_related("order")
                .order_by("-paid_at")[:4]
            )
        else:
            active_orders = list(Order.objects.filter(status__in=["pending", "preparing", "ready"]).order_by("-created_at")[:4])
            recent_payments = list(
                Payment.objects.select_related("order").order_by("-paid_at")[:4]
            )
        average_order_value = (total_revenue / total_orders) if total_orders else Decimal("0")
        unique_customers = Order.objects.exclude(customer_name="Walk-in Customer").values_list("customer_name", flat=True).distinct().count()

        return render(
            request,
            template_name,
            {
                "total_revenue": total_revenue,
                "pending_orders": pending_orders,
                "total_orders": total_orders,
                "low_stock": low_stock,
                "recent_orders": recent_orders,
                "prediction": prediction,
                "user": request.user,
                "dashboard_mode": "admin",
                "sales_data": sales_data,
                "chart_line": chart_line,
                "chart_fill": chart_fill,
                "chart_points": chart_points,
                "top_items": top_items,
                "active_orders": active_orders,
                "recent_payments": recent_payments,
                "average_order_value": average_order_value,
                "new_customers": unique_customers,
                "search_query": search_query,
            },
        )

    return render(
        request,
        template_name,
        {
            "total_revenue": total_revenue,
            "pending_orders": pending_orders,
            "total_orders": total_orders,
            "low_stock": low_stock,
            "recent_orders": recent_orders,
            "prediction": prediction,
            "user": request.user,
            "dashboard_mode": request.user.role,
            "search_query": search_query,
        },
    )


@login_required
@role_required("admin", "manager", "waiter", "cashier")
def create_order(request):
    menu_items = MenuItem.objects.filter(is_available=True).order_by("category", "name")
    error = None

    if request.method == "POST":
        customer_name = (request.POST.get("customer_name") or "Walk-in Customer").strip() or "Walk-in Customer"
        order_type = request.POST.get("order_type", "dine_in")
        notes = request.POST.get("notes", "")

        selected_items = []
        for menu_item in menu_items:
            quantity = int(request.POST.get(f"quantity_{menu_item.pk}", 0) or 0)
            if quantity > 0:
                selected_items.append((menu_item, quantity))

        if not selected_items:
            error = "Please select at least one menu item before placing the order."
        else:
            order = Order.objects.create(
                customer_name=customer_name,
                order_type=order_type,
                notes=notes,
            )

            total = Decimal("0")
            for menu_item, quantity in selected_items:
                for recipe in menu_item.recipe_items.all():
                    required = recipe.quantity_required * quantity
                    ingredient = recipe.ingredient
                    if ingredient.stock < required:
                        order.delete()
                        error = (
                            f"Not enough stock for {ingredient.name}. "
                            f"Needed {required} {ingredient.unit}, but only {ingredient.stock} available."
                        )
                        break
                if error:
                    break

                for recipe in menu_item.recipe_items.all():
                    ingredient = recipe.ingredient
                    ingredient.stock -= recipe.quantity_required * quantity
                    ingredient.save()

                subtotal = menu_item.price * quantity
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    unit_price=menu_item.price,
                    subtotal=subtotal,
                )
                total += subtotal

            if not error:
                order.total_amount = total
                order.save()
                log_activity(
                    request.user,
                    "order_created",
                    f"Created order #{order.pk} for {order.customer_name}.",
                    request=request,
                    target_model="Order",
                    target_id=order.pk,
                )
                return redirect("payment", order_id=order.pk)

    return render(
        request,
        "restaurant/orders.html",
        {"menu_items": menu_items, "error": error},
    )


@login_required
@role_required("admin", "manager", "kitchen_staff")
def kitchen(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        next_status = request.POST.get("status")
        if order_id and next_status:
            order = Order.objects.get(pk=order_id)
            allowed = ["pending", "preparing", "ready"]
            if next_status in allowed:
                order.status = next_status
                order.save(update_fields=["status"])
                log_activity(
                    request.user,
                    "order_updated",
                    f"Updated order #{order.pk} status to {next_status}.",
                    request=request,
                    target_model="Order",
                    target_id=order.pk,
                )
        return redirect("kitchen")

    orders = Order.objects.prefetch_related("items__menu_item").order_by("status", "-created_at")
    return render(request, "restaurant/kitchen.html", {"orders": orders})


@login_required
@role_required("admin", "manager", "inventory_staff")
def inventory(request):
    inventory = InventoryItem.objects.order_by("name")
    return render(request, "restaurant/inventory.html", {"inventory": inventory})


@login_required
@role_required("admin", "manager", "cashier")
def process_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    error = None

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "cash")
        amount = Decimal(request.POST.get("amount", order.total_amount) or order.total_amount)

        if amount < order.total_amount:
            error = "The payment amount must be at least the order total."
        else:
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    "payment_method": payment_method,
                    "amount": amount,
                },
            )
            log_activity(
                request.user,
                "payment_processed",
                f"Processed payment for order #{order.pk} using {payment_method}.",
                request=request,
                target_model="Payment",
                target_id=order.pk,
            )
            return redirect("reports")

    return render(
        request,
        "restaurant/payment.html",
        {"order": order, "error": error},
    )


@login_required
@role_required("admin", "manager", "cashier")
def reports(request):
    payment_records = Payment.objects.order_by("-paid_at")
    total_revenue = payment_records.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    if payment_records.exists():
        latest_date = payment_records.first().paid_at.date()
        start_date = latest_date - timedelta(days=6)
        sales_by_day = defaultdict(Decimal)
        for payment in payment_records:
            day = payment.paid_at.date()
            if start_date <= day <= latest_date:
                sales_by_day[day] += payment.amount
        daily_sales = [
            {"date": start_date + timedelta(days=offset), "total": sales_by_day.get(start_date + timedelta(days=offset), Decimal("0"))}
            for offset in range(7)
        ]
    else:
        daily_sales = []

    forecast_data = get_revenue_forecast(days=7)
    forecast = forecast_data["forecast"]
    forecast_summary = forecast_data["summary"]
    return render(
        request,
        "restaurant/reports.html",
        {
            "payments": payment_records[:10],
            "total_revenue": total_revenue,
            "daily_sales": daily_sales,
            "forecast": forecast,
            "forecast_summary": forecast_summary,
        },
    )


@login_required
@role_required("admin", "manager", "cashier")
def revenue_forecast(request):
    today = timezone.now().date()
    start_date_value = request.GET.get("start_date")
    end_date_value = request.GET.get("end_date")
    days_value = request.GET.get("days")

    try:
        end_date = date.fromisoformat(end_date_value) if end_date_value else today
    except ValueError:
        end_date = today

    try:
        start_date = date.fromisoformat(start_date_value) if start_date_value else end_date - timedelta(days=30)
    except ValueError:
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    try:
        forecast_days = int(days_value) if days_value else 7
    except ValueError:
        forecast_days = 7
    forecast_days = max(1, min(forecast_days, 30))

    forecast_data = get_revenue_forecast(days=forecast_days, end_date=end_date, history_days=max(30, (end_date - start_date).days + 1))
    chart_points = forecast_data["chart"]["combined"]
    history_points = forecast_data["chart"]["history"]
    forecast_points = forecast_data["chart"]["forecast"]
    history_payload = [{"label": item["label"], "value": float(item["value"])} for item in forecast_data["history"]]
    forecast_payload = [{"label": item["label"], "value": float(item["predicted_amount"])} for item in forecast_data["forecast"]]

    return render(
        request,
        "restaurant/revenue_forecast.html",
        {
            "summary": forecast_data["summary"],
            "forecast": forecast_data["forecast"],
            "history": forecast_data["history"],
            "model_name": forecast_data["model"],
            "chart_points": chart_points,
            "history_points": history_points,
            "forecast_points": forecast_points,
            "history_json": json.dumps(history_payload),
            "forecast_json": json.dumps(forecast_payload),
            "selected_start_date": start_date,
            "selected_end_date": end_date,
            "forecast_days": forecast_days,
            "preset_ranges": [7, 30, 90],
        },
    )


@login_required
@role_required("admin", "manager", "cashier")
def export_forecast_csv(request):
    today = timezone.now().date()
    end_date_value = request.GET.get("end_date")
    days_value = request.GET.get("days")

    try:
        end_date = date.fromisoformat(end_date_value) if end_date_value else today
    except ValueError:
        end_date = today

    try:
        forecast_days = int(days_value) if days_value else 7
    except ValueError:
        forecast_days = 7
    forecast_days = max(1, min(forecast_days, 30))

    forecast_data = get_revenue_forecast(days=forecast_days, end_date=end_date, history_days=90)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "predicted_amount", "confidence", "model"])
    for item in forecast_data["forecast"]:
        writer.writerow([item["date"].isoformat(), item["predicted_amount"], item["confidence"], forecast_data["model"]])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="revenue_forecast_{end_date.isoformat()}.csv"'
    return response


@login_required
@role_required("admin", "manager", "waiter", "cashier", "kitchen_staff", "inventory_staff")
def profile_view(request):
    profile_form = ProfileForm(request.POST or None, instance=request.user)
    password_form = PasswordChangeForm(request.user, request.POST or None)
    changed = False

    if request.method == "POST":
        if "profile_submit" in request.POST and profile_form.is_valid():
            profile_form.save()
            log_activity(
                request.user,
                "profile_updated",
                f"Updated personal profile for {request.user.get_full_name() or request.user.username}.",
                request=request,
                target_model="CustomUser",
                target_id=request.user.pk,
            )
            messages.success(request, "Your profile was updated successfully.")
            changed = True
        elif "password_submit" in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            log_activity(
                request.user,
                "password_reset",
                "Password changed safely from the profile page.",
                request=request,
                target_model="CustomUser",
                target_id=request.user.pk,
            )
            messages.success(request, "Your password was updated successfully.")
            changed = True

    if changed:
        profile_form = ProfileForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(
        request,
        "restaurant/profile.html",
        {"profile_form": profile_form, "password_form": password_form},
    )


@login_required
@role_required("admin", "manager")
def staff_management(request):
    staff_members = CustomUser.objects.all().order_by("username")
    activity_log = ActivityLog.objects.select_related("user").order_by("-created_at")[:20]
    return render(
        request,
        "restaurant/staff_management.html",
        {"staff_members": staff_members, "activity_log": activity_log},
    )


@login_required
@role_required("admin", "manager")
def staff_create(request):
    form = StaffForm(request.POST or None)
    redirect_target = request.GET.get("next") or request.POST.get("next") or "staff_management"
    if request.method == "POST" and form.is_valid():
        if not form.cleaned_data.get("password"):
            form.add_error("password", "Password is required for a new staff account.")
        else:
            staff = form.save()
            log_activity(
                request.user,
                "created_user",
                f"Created staff account for {staff.get_full_name() or staff.username}.",
                request=request,
                target_model="CustomUser",
                target_id=staff.pk,
            )
            return redirect(redirect_target)
    return render(request, "restaurant/staff_form.html", {"form": form, "title": "Create Staff Account"})


@login_required
@role_required("admin", "manager")
def staff_update(request, user_id):
    staff = get_object_or_404(CustomUser, pk=user_id)
    form = StaffForm(request.POST or None, instance=staff)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(
            request.user,
            "updated_user",
            f"Updated staff account for {staff.get_full_name() or staff.username}.",
            request=request,
            target_model="CustomUser",
            target_id=staff.pk,
        )
        return redirect("staff_management")
    return render(request, "restaurant/staff_form.html", {"form": form, "title": "Update Staff Account"})


@login_required
@role_required("admin", "manager")
def staff_toggle_active(request, user_id):
    staff = get_object_or_404(CustomUser, pk=user_id)
    if staff == request.user:
        return HttpResponseForbidden("You cannot deactivate your own account.")
    staff.is_active = not staff.is_active
    staff.save()
    log_activity(
        request.user,
        "deactivated_user" if not staff.is_active else "activated_user",
        f"{'Deactivated' if not staff.is_active else 'Activated'} staff account for {staff.get_full_name() or staff.username}.",
        request=request,
        target_model="CustomUser",
        target_id=staff.pk,
    )
    return redirect("staff_management")
