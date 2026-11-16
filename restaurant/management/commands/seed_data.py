from django.core.management.base import BaseCommand

from restaurant.models import InventoryItem, MenuItem, RecipeItem


class Command(BaseCommand):
    help = "Populate starter menu and inventory data for the restaurant management system"

    def handle(self, *args, **options):
        inventory = {
            "rice": {"stock": 50, "unit": "kg", "reorder": 20},
            "chicken": {"stock": 40, "unit": "kg", "reorder": 15},
            "tomato": {"stock": 30, "unit": "kg", "reorder": 10},
            "onion": {"stock": 25, "unit": "kg", "reorder": 8},
            "milk": {"stock": 28, "unit": "litres", "reorder": 12},
            "flour": {"stock": 35, "unit": "kg", "reorder": 10},
            "coffee": {"stock": 20, "unit": "packs", "reorder": 6},
            "sugar": {"stock": 18, "unit": "kg", "reorder": 6},
        }

        created_inventory = {}
        for name, data in inventory.items():
            ingredient, _ = InventoryItem.objects.get_or_create(
                name=name,
                defaults={"stock": data["stock"], "unit": data["unit"], "reorder_level": data["reorder"]},
            )
            created_inventory[name] = ingredient

        menu_items = [
            ("Chicken Biryani", "main", 12.50, "Classic rice dish with spiced chicken."),
            ("Veg Fried Rice", "main", 9.00, "Vegetarian fried rice with vegetables and soy sauce."),
            ("Tomato Soup", "starter", 5.50, "Warm soup made with fresh tomato and herbs."),
            ("Vegetable Spring Rolls", "starter", 6.50, "Crispy vegetable spring rolls with dipping sauce."),
            ("Garlic Bread", "starter", 5.95, "Toasted bread with garlic butter and herbs."),
            ("Chicken Tikka Starter", "starter", 7.95, "Marinated chicken tikka served as a starter."),
            ("Onion Bhaji", "starter", 5.95, "Crisp spiced onion fritters."),
            ("Chicken Curry and Rice", "main", 12.95, "Chicken curry served with steamed rice."),
            ("Lamb Curry and Rice", "main", 14.95, "Slow-cooked lamb curry served with rice."),
            ("Grilled Chicken with Chips", "main", 14.95, "Grilled chicken breast served with chips."),
            ("Vegetable Curry", "main", 11.95, "Seasonal vegetables in a gently spiced curry sauce."),
            ("Chocolate Cake", "dessert", 6.00, "Rich chocolate dessert served fresh."),
            ("Cappuccino", "beverage", 4.50, "Freshly brewed cappuccino with milk foam."),
            ("Latte", "beverage", 4.50, "Espresso topped with steamed milk."),
            ("Americano", "beverage", 3.50, "Espresso served with hot water."),
            ("Flat White", "beverage", 4.25, "Double espresso with velvety steamed milk."),
            ("Espresso", "beverage", 2.75, "A single shot of freshly brewed espresso."),
            ("English Breakfast Tea", "beverage", 2.95, "Traditional English breakfast tea."),
            ("Masala Chai", "beverage", 3.75, "Indian spiced tea brewed with milk."),
            ("Hot Chocolate", "beverage", 4.25, "Hot chocolate topped with steamed milk."),
            ("Fresh Lemonade", "beverage", 3.95, "Refreshing house-made lemon drink."),
            ("Mango Lassi", "beverage", 4.50, "Chilled yoghurt drink blended with mango."),
        ]

        for name, category, price, description in menu_items:
            menu_item, _ = MenuItem.objects.get_or_create(
                name=name,
                defaults={"category": category, "price": price, "description": description},
            )

            if name == "Chicken Biryani":
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["rice"], quantity_required=0.5)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["chicken"], quantity_required=0.4)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["tomato"], quantity_required=0.3)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["onion"], quantity_required=0.2)
            elif name == "Veg Fried Rice":
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["rice"], quantity_required=0.5)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["tomato"], quantity_required=0.2)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["onion"], quantity_required=0.2)
            elif name == "Tomato Soup":
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["tomato"], quantity_required=0.6)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["onion"], quantity_required=0.2)
            elif name == "Chocolate Cake":
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["milk"], quantity_required=0.2)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["flour"], quantity_required=0.3)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["sugar"], quantity_required=0.1)
            elif name == "Cappuccino":
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["milk"], quantity_required=0.3)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["coffee"], quantity_required=0.1)
                RecipeItem.objects.get_or_create(menu_item=menu_item, ingredient=created_inventory["sugar"], quantity_required=0.05)

        self.stdout.write(self.style.SUCCESS("Starter restaurant data created successfully."))
