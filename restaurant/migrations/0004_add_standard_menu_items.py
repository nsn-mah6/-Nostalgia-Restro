from django.db import migrations


MENU_ITEMS = [
    ("Tomato Soup", "starter", "5.50", "Warm soup made with fresh tomato and herbs."),
    ("Vegetable Spring Rolls", "starter", "6.50", "Crispy vegetable spring rolls with dipping sauce."),
    ("Garlic Bread", "starter", "5.95", "Toasted bread with garlic butter and herbs."),
    ("Chicken Tikka Starter", "starter", "7.95", "Marinated chicken tikka served as a starter."),
    ("Onion Bhaji", "starter", "5.95", "Crisp spiced onion fritters."),
    ("Veg Fried Rice", "main", "9.00", "Vegetarian fried rice with vegetables and soy sauce."),
    ("Chicken Curry and Rice", "main", "12.95", "Chicken curry served with steamed rice."),
    ("Lamb Curry and Rice", "main", "14.95", "Slow-cooked lamb curry served with rice."),
    ("Grilled Chicken with Chips", "main", "14.95", "Grilled chicken breast served with chips."),
    ("Vegetable Curry", "main", "11.95", "Seasonal vegetables in a gently spiced curry sauce."),
    ("Cappuccino", "beverage", "4.50", "Freshly brewed cappuccino with milk foam."),
    ("Latte", "beverage", "4.50", "Espresso topped with steamed milk."),
    ("Americano", "beverage", "3.50", "Espresso served with hot water."),
    ("Flat White", "beverage", "4.25", "Double espresso with velvety steamed milk."),
    ("Espresso", "beverage", "2.75", "A single shot of freshly brewed espresso."),
    ("English Breakfast Tea", "beverage", "2.95", "Traditional English breakfast tea."),
    ("Masala Chai", "beverage", "3.75", "Indian spiced tea brewed with milk."),
    ("Hot Chocolate", "beverage", "4.25", "Hot chocolate topped with steamed milk."),
    ("Fresh Lemonade", "beverage", "3.95", "Refreshing house-made lemon drink."),
    ("Mango Lassi", "beverage", "4.50", "Chilled yoghurt drink blended with mango."),
]


def add_standard_menu_items(apps, schema_editor):
    menu_item_model = apps.get_model("restaurant", "MenuItem")
    for name, category, price, description in MENU_ITEMS:
        menu_item_model.objects.get_or_create(
            name=name,
            defaults={
                "category": category,
                "price": price,
                "description": description,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0003_alter_menuitem_category"),
    ]

    operations = [
        migrations.RunPython(add_standard_menu_items, migrations.RunPython.noop),
    ]
