from django.contrib import admin

from .models import ActivityLog, CustomUser, InventoryItem, MenuItem, Order, OrderItem, Payment, RecipeItem

admin.site.register(CustomUser)
admin.site.register(ActivityLog)
admin.site.register(InventoryItem)
admin.site.register(MenuItem)
admin.site.register(RecipeItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
