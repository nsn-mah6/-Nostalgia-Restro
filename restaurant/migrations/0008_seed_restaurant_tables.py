from django.db import migrations


def seed_tables(apps, schema_editor):
    RestaurantTable = apps.get_model("restaurant", "RestaurantTable")
    for table_number in range(1, 11):
        RestaurantTable.objects.get_or_create(
            table_number=table_number,
            defaults={
                "name": f"Table {table_number}",
                "capacity": 4 if table_number <= 8 else 6,
                "location": "Main Dining",
                "is_available": True,
            },
        )


def remove_seed_tables(apps, schema_editor):
    RestaurantTable = apps.get_model("restaurant", "RestaurantTable")
    RestaurantTable.objects.filter(table_number__range=(1, 10), name__startswith="Table ").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("restaurant", "0007_restauranttable_alter_activitylog_action_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_tables, remove_seed_tables),
    ]
