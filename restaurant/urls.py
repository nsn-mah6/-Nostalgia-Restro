from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/stats/", views.dashboard_stats, name="dashboard_stats"),
    path("dashboard/top-selling-items/", views.top_selling_items, name="top_selling_items"),
    path("dashboard/transactions/", views.all_transactions, name="all_transactions"),
    path("dashboard/active-orders/", views.active_orders, name="active_orders"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="registration/password_reset_form.html", email_template_name="registration/password_reset_email.html", success_url="/password-reset/done/"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html", success_url="/reset/done/"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("profile/", views.profile_view, name="profile"),
    path("orders/", views.create_order, name="orders"),
    path("bookings/", views.bookings, name="bookings"),
    path("bookings/<int:booking_id>/edit/", views.booking_update, name="booking_update"),
    path("bookings/<int:booking_id>/cancel/", views.booking_cancel, name="booking_cancel"),
    path("tables/<int:table_id>/toggle/", views.table_toggle_available, name="table_toggle_available"),
    path("tables/<int:table_id>/delete/", views.table_delete, name="table_delete"),
    path("kitchen/", views.kitchen, name="kitchen"),
    path("inventory/", views.inventory, name="inventory"),
    path("payments/<int:order_id>/", views.process_payment, name="payment"),
    path("reports/", views.reports, name="reports"),
    path("reports/forecast/", views.revenue_forecast, name="revenue_forecast"),
    path("reports/forecast/export/", views.export_forecast_csv, name="export_forecast_csv"),
    path("staff/", views.staff_management, name="staff_management"),
    path("staff/create/", views.staff_create, name="staff_create"),
    path("staff/<int:user_id>/edit/", views.staff_update, name="staff_update"),
    path("staff/<int:user_id>/toggle/", views.staff_toggle_active, name="staff_toggle_active"),
]
