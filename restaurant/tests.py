from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    ActivityLog,
    CustomUser,
    InventoryItem,
    MenuItem,
    Order,
    Payment,
    RestaurantTable,
    TableBooking,
)


class DashboardStatsTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="dashboard-admin",
            password="test-password",
            role="admin",
        )
        self.client.force_login(self.user)
        self.today = timezone.localdate()
        self.today_start = timezone.make_aware(datetime.combine(self.today, time.min))
        self.yesterday_start = self.today_start - timedelta(days=1)

    def create_paid_order(self, customer_name, amount, created_at):
        order = Order.objects.create(customer_name=customer_name, total_amount=amount)
        Order.objects.filter(pk=order.pk).update(created_at=created_at)
        Payment.objects.create(order=order, amount=amount, paid_at=created_at)

    def test_stats_endpoint_compares_today_with_yesterday(self):
        self.create_paid_order("Alex", Decimal("100.00"), self.yesterday_start + timedelta(hours=12))
        self.create_paid_order("Alex", Decimal("150.00"), self.today_start + timedelta(hours=10))
        self.create_paid_order("Blake", Decimal("50.00"), self.today_start + timedelta(hours=11))

        response = self.client.get(reverse("dashboard_stats"))

        self.assertEqual(response.status_code, 200)
        stats = response.json()
        self.assertEqual(stats["sales"]["value"], "200")
        self.assertEqual(stats["sales"]["label"], "↑ 100.0%")
        self.assertEqual(stats["orders"]["value"], "2")
        self.assertEqual(stats["orders"]["label"], "↑ 100.0%")
        self.assertEqual(stats["average_order_value"]["value"], "100")
        self.assertEqual(stats["average_order_value"]["label"], "→ 0.0%")
        self.assertEqual(stats["new_customers"]["value"], "1")
        self.assertEqual(stats["new_customers"]["label"], "→ 0.0%")

    def test_stats_endpoint_is_admin_only(self):
        self.user.role = "manager"
        self.user.save()

        response = self.client.get(reverse("dashboard_stats"))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_renders_live_stats(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-stat-value="sales"')
        self.assertContains(response, 'data-stats-url="/dashboard/stats/"')
        self.assertContains(response, f'href="{reverse("top_selling_items")}">View All</a>')
        self.assertContains(response, f'href="{reverse("active_orders")}">View All</a>')
        self.assertContains(response, f'href="{reverse("all_transactions")}">View All</a>')

    def test_dashboard_view_all_pages_are_separate(self):
        pages = (
            ("top_selling_items", "Top Selling Items"),
            ("active_orders", "Active Orders"),
            ("all_transactions", "All Transactions"),
        )
        for route_name, heading in pages:
            with self.subTest(page=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f"<h1>{heading}</h1>")

    def test_order_menu_displays_the_new_cuisine_catalog(self):
        response = self.client.get(reverse("orders"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MenuItem.objects.filter(category="starter").count(), 5)
        self.assertEqual(MenuItem.objects.filter(category="main").count(), 5)
        self.assertEqual(MenuItem.objects.filter(category="beverage").count(), 10)
        self.assertEqual(
            MenuItem.objects.filter(
                category__in=["indian", "nepali", "british", "italian", "fast_food", "dessert"]
            ).count(),
            50,
        )
        self.assertContains(response, "Indian Cuisine")
        self.assertContains(response, "Nepali Cuisine")
        self.assertContains(response, "British Cuisine")
        self.assertContains(response, "Italian Cuisine")
        self.assertContains(response, "Fast Food &amp; Starters")
        self.assertContains(response, "Desserts")
        self.assertContains(response, "Chicken Tikka Masala")
        self.assertContains(response, "Fish and Chips")
        self.assertContains(response, "Brownie with Ice Cream")
        self.assertContains(response, 'class="section order-menu"')
        self.assertContains(response, "£13.95")

    def test_dine_in_order_requires_and_saves_table_number(self):
        menu_item = MenuItem.objects.filter(is_available=True).first()
        missing_table = self.client.post(
            reverse("orders"),
            {
                "customer_name": "Table Guest",
                "order_type": "dine_in",
                "table_number": "",
                f"quantity_{menu_item.pk}": 1,
            },
        )
        self.assertContains(missing_table, "Please enter a valid table number")

        response = self.client.post(
            reverse("orders"),
            {
                "customer_name": "Table Guest",
                "order_type": "dine_in",
                "table_number": "12",
                f"quantity_{menu_item.pk}": 1,
            },
        )
        order = Order.objects.get(customer_name="Table Guest")
        self.assertEqual(order.table_number, 12)
        self.assertRedirects(response, reverse("payment", args=[order.pk]))

    def test_reports_has_targets_for_dashboard_links(self):
        response = self.client.get(reverse("reports"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="top-selling-items"')
        self.assertContains(response, 'id="recent-payments"')

    def test_admin_can_add_inventory_item(self):
        response = self.client.post(
            reverse("inventory"),
            {"name": "Olive Oil", "stock": 12, "reorder_level": 4, "unit": "litres"},
        )

        self.assertRedirects(response, reverse("inventory"))
        self.assertTrue(
            InventoryItem.objects.filter(
                name="Olive Oil",
                stock=12,
                reorder_level=4,
                unit="litres",
            ).exists()
        )

    def test_inventory_staff_cannot_add_inventory_item(self):
        self.user.role = "inventory_staff"
        self.user.save()

        response = self.client.post(
            reverse("inventory"),
            {"name": "Olive Oil", "stock": 12, "reorder_level": 4, "unit": "litres"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(InventoryItem.objects.filter(name="Olive Oil").exists())

    def test_booking_page_has_available_table_options_and_no_activity_panel(self):
        RestaurantTable.objects.create(table_number=21, name="Garden Table", capacity=6)
        RestaurantTable.objects.create(table_number=22, name="Patio Table", capacity=2, is_available=False)

        response = self.client.get(reverse("bookings"))

        self.assertContains(response, "Select a table")
        table_queryset = response.context["booking_form"].fields["table"].queryset
        self.assertTrue(table_queryset.filter(table_number=21).exists())
        self.assertFalse(table_queryset.filter(table_number=22).exists())
        self.assertNotContains(response, "Reservation Activity Log")

    def test_table_can_be_deleted_only_without_reservation_history(self):
        deletable = RestaurantTable.objects.create(table_number=31, capacity=2)
        response = self.client.post(reverse("table_delete", args=[deletable.pk]))
        self.assertRedirects(response, reverse("bookings"))
        self.assertFalse(RestaurantTable.objects.filter(pk=deletable.pk).exists())
        self.assertTrue(ActivityLog.objects.filter(action="table_updated", details__contains="Deleted table 31").exists())

        protected = RestaurantTable.objects.create(table_number=32, capacity=2)
        TableBooking.objects.create(
            customer_name="Reserved Guest",
            phone="555-0102",
            table=protected,
            party_size=2,
            booking_date=timezone.localdate() + timedelta(days=1),
            booking_time="18:00",
        )
        response = self.client.post(reverse("table_delete", args=[protected.pk]))
        self.assertRedirects(response, reverse("bookings"))
        self.assertTrue(RestaurantTable.objects.filter(pk=protected.pk).exists())
        self.assertContains(self.client.get(reverse("bookings")), "cannot be deleted")

    def test_booking_creation_conflict_update_cancel_and_activity_log(self):
        table, _ = RestaurantTable.objects.get_or_create(
            table_number=5,
            defaults={"name": "Table 5", "capacity": 4},
        )
        booking_date = timezone.localdate() + timedelta(days=1)

        create_response = self.client.post(
            reverse("bookings"),
            {
                "create_booking": "1",
                "booking-customer_name": "Jordan",
                "booking-phone": "555-0100",
                "booking-email": "jordan@example.com",
                "booking-table": table.pk,
                "booking-party_size": 3,
                "booking-booking_date": booking_date.isoformat(),
                "booking-booking_time": "18:30",
                "booking-status": "confirmed",
                "booking-notes": "Window seat",
            },
        )
        self.assertRedirects(create_response, reverse("bookings"))
        booking = TableBooking.objects.get(customer_name="Jordan")
        self.assertEqual(booking.table, table)
        self.assertTrue(ActivityLog.objects.filter(action="booking_created", target_id=booking.pk).exists())

        conflict_response = self.client.post(
            reverse("bookings"),
            {
                "create_booking": "1",
                "booking-customer_name": "Sam",
                "booking-phone": "555-0101",
                "booking-email": "",
                "booking-table": table.pk,
                "booking-party_size": 2,
                "booking-booking_date": booking_date.isoformat(),
                "booking-booking_time": "18:30",
                "booking-status": "pending",
                "booking-notes": "",
            },
        )
        self.assertContains(conflict_response, "already has a booking")
        self.assertFalse(TableBooking.objects.filter(customer_name="Sam").exists())

        update_response = self.client.post(
            reverse("booking_update", args=[booking.pk]),
            {
                "booking-customer_name": "Jordan Lee",
                "booking-phone": "555-0100",
                "booking-email": "jordan@example.com",
                "booking-table": table.pk,
                "booking-party_size": 4,
                "booking-booking_date": booking_date.isoformat(),
                "booking-booking_time": "19:00",
                "booking-status": "seated",
                "booking-notes": "Window seat",
            },
        )
        self.assertRedirects(update_response, reverse("bookings"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "seated")
        self.assertEqual(booking.customer_name, "Jordan Lee")

        cancel_response = self.client.post(reverse("booking_cancel", args=[booking.pk]))
        self.assertRedirects(cancel_response, reverse("bookings"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")
        self.assertTrue(ActivityLog.objects.filter(action="booking_cancelled", target_id=booking.pk).exists())
