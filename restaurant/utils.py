from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Payment


def _get_daily_revenue(history_days=90, end_date=None):
    """Aggregate payment totals by calendar day for a recent sales window."""
    if end_date is None:
        end_date = timezone.now().date()
    start_date = end_date - timedelta(days=history_days)
    payments = Payment.objects.filter(paid_at__date__gte=start_date, paid_at__date__lte=end_date).order_by("paid_at")

    daily_totals = defaultdict(Decimal)
    for payment in payments:
        daily_totals[payment.paid_at.date()] += payment.amount

    ordered_dates = [start_date + timedelta(days=offset) for offset in range(history_days + 1)]
    revenue_by_day = {day: float(daily_totals.get(day, Decimal("0"))) for day in ordered_dates}
    return revenue_by_day


def _chart_points(series, width=620, height=240, padding=30):
    values = [float(point["value"]) for point in series]
    if not values:
        return []
    max_value = max(values) if max(values) > 0 else 1
    points = []
    for index, point in enumerate(series):
        x = padding + (index * (width - (padding * 2)) / max(len(series) - 1, 1))
        y = height - padding - ((float(point["value"]) / max_value) * (height - (padding * 2)))
        points.append({**point, "x": x, "y": y})
    return points


def _build_series_path(points):
    if not points:
        return ""
    return " ".join(f"{point['x']},{point['y']}" for point in points)


def _build_forecast_for_window(days=7, start_date=None, end_date=None, history_days=90):
    if end_date is None:
        end_date = timezone.now().date()
    if start_date is None:
        start_date = end_date - timedelta(days=history_days)

    revenue_by_day = _get_daily_revenue(history_days=max(history_days, 30), end_date=end_date)
    ordered_days = sorted(revenue_by_day)
    values = [revenue_by_day[day] for day in ordered_days]

    if not values or sum(values) == 0:
        forecast_items = []
        for offset in range(1, days + 1):
            date = end_date + timedelta(days=offset)
            forecast_items.append({
                "date": date,
                "label": date.strftime("%a, %d %b"),
                "actual_amount": 0.0,
                "predicted_amount": 0.0,
                "confidence": 0.0,
            })
        return {
            "model": "Weighted weekday seasonal regression",
            "forecast": forecast_items,
            "history": [{"date": day, "label": day.strftime("%a, %d %b"), "value": revenue_by_day[day]} for day in ordered_days],
            "summary": {
                "next_7_day_total": 0.0,
                "average_daily_revenue": 0.0,
                "confidence_score": 0.0,
                "trend_percent": 0.0,
                "mape": 0.0,
                "mae": 0.0,
            },
            "chart": {"history": [], "forecast": []},
        }

    x_values = list(range(len(values)))
    mean_x = sum(x_values) / len(x_values)
    mean_y = sum(values) / len(values)
    denominator = sum((value - mean_x) ** 2 for value in x_values)

    slope = 0.0 if denominator == 0 else sum((x_value - mean_x) * (y_value - mean_y) for x_value, y_value in zip(x_values, values)) / denominator
    intercept = mean_y - (slope * mean_x)

    seasonal_by_weekday = defaultdict(list)
    for day, value in zip(ordered_days, values):
        seasonal_by_weekday[day.weekday()].append(value)

    weekday_baseline = {
        weekday: (sum(amounts) / len(amounts)) if amounts else mean_y
        for weekday, amounts in seasonal_by_weekday.items()
    }

    recent_window = values[-7:]
    recent_average = sum(recent_window) / len(recent_window)
    forecast_items = []
    total_predicted = 0.0
    for offset in range(1, days + 1):
        target_date = end_date + timedelta(days=offset)
        raw_prediction = intercept + slope * (len(values) + offset)
        weekday_bias = weekday_baseline.get(target_date.weekday(), mean_y)
        weekly_weight = 1.0 + (0.12 if target_date.weekday() >= 5 else 0.0)
        recency_adjustment = (recent_average * 0.35) + (weekday_bias * 0.65)
        predicted_amount = max(0.0, raw_prediction * 0.55 + recency_adjustment * 0.45) * weekly_weight

        deviation_from_recent = abs(predicted_amount - recent_average) / max(recent_average, 1.0)
        confidence = max(52.0, min(96.0, 92.0 - (deviation_from_recent * 100.0)))

        forecast_items.append({
            "date": target_date,
            "label": target_date.strftime("%a, %d %b"),
            "actual_amount": 0.0,
            "predicted_amount": round(predicted_amount, 2),
            "confidence": round(confidence, 1),
        })
        total_predicted += predicted_amount

    history_data = [{"date": day, "label": day.strftime("%a, %d %b"), "value": round(revenue_by_day[day], 2)} for day in ordered_days]
    average_daily_revenue = total_predicted / days if days else 0.0
    previous_average = sum(values[-14:]) / min(len(values[-14:]), 14) if values else 0.0
    trend_percent = ((average_daily_revenue - previous_average) / previous_average * 100) if previous_average else 0.0

    accuracy_metrics = _calculate_accuracy_metrics(values)
    forecast_summary = {
        "next_7_day_total": round(total_predicted, 2),
        "average_daily_revenue": round(average_daily_revenue, 2),
        "confidence_score": round(sum(item["confidence"] for item in forecast_items) / len(forecast_items), 2),
        "trend_percent": round(trend_percent, 2),
        "mape": round(accuracy_metrics["mape"], 2),
        "mae": round(accuracy_metrics["mae"], 2),
    }

    history_series = [{"label": item["label"], "value": item["value"], "series": "actual"} for item in history_data]
    forecast_series = [{"label": item["label"], "value": item["predicted_amount"], "series": "forecast"} for item in forecast_items]
    combined_series = history_series + forecast_series

    return {
        "model": "Weighted weekday seasonal regression",
        "forecast": forecast_items,
        "history": history_data,
        "summary": forecast_summary,
        "chart": {
            "history": _chart_points(history_series),
            "forecast": _chart_points(forecast_series),
            "combined": _chart_points(combined_series),
        },
    }


def _calculate_accuracy_metrics(values):
    if not values or len(values) < 8:
        return {"mape": 0.0, "mae": 0.0}

    predictions = []
    actuals = []
    for index in range(7, len(values)):
        window = values[:index]
        if len(window) < 5:
            continue

        x_values = list(range(len(window)))
        mean_x = sum(x_values) / len(x_values)
        mean_y = sum(window) / len(window)
        denominator = sum((x_value - mean_x) ** 2 for x_value in x_values)

        slope = 0.0 if denominator == 0 else sum(
            (x_value - mean_x) * (y_value - mean_y) for x_value, y_value in zip(x_values, window)
        ) / denominator
        intercept = mean_y - (slope * mean_x)
        prediction = intercept + slope * len(window)
        actual = values[index]

        if actual == 0:
            continue
        predictions.append(prediction)
        actuals.append(actual)

    if not actuals:
        return {"mape": 0.0, "mae": 0.0}

    absolute_errors = [abs(prediction - actual) for prediction, actual in zip(predictions, actuals)]
    mape = (sum(abs(prediction - actual) / abs(actual) for prediction, actual in zip(predictions, actuals)) / len(actuals)) * 100
    mae = sum(absolute_errors) / len(absolute_errors)
    return {"mape": mape, "mae": mae}


def get_revenue_forecast(days=7, start_date=None, end_date=None, history_days=90):
    """Create a lightweight ML-style revenue forecast using linear trend + weekday seasonality."""
    return _build_forecast_for_window(days=days, start_date=start_date, end_date=end_date, history_days=history_days)


def forecast_sales(days=7, end_date=None):
    """Compatibility wrapper used by existing dashboard templates."""
    forecast_data = get_revenue_forecast(days=days, end_date=end_date)
    return [round(item["predicted_amount"], 2) for item in forecast_data["forecast"]]
