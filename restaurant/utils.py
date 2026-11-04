from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Payment


def forecast_sales(days=7):
    """Estimate the next few days of sales using recent trends."""
    start_date = timezone.now().date() - timedelta(days=90)
    payments = Payment.objects.filter(paid_at__date__gte=start_date).order_by("paid_at")

    daily_totals = defaultdict(Decimal)
    for payment in payments:
        daily_totals[payment.paid_at.date()] += payment.amount

    values = [float(daily_totals.get(day, Decimal("0"))) for day in sorted(daily_totals)]
    if not values:
        return [0.0 for _ in range(days)]

    recent_values = values[-7:] if len(values) >= 7 else values
    average = sum(recent_values) / len(recent_values)
    trend = (recent_values[-1] - recent_values[0]) / max(len(recent_values) - 1, 1)

    return [round(max(0.0, average + trend * step), 2) for step in range(1, days + 1)]
