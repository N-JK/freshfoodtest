from django.contrib import admin
from .models import BuyerProfile, Address, Wishlist, Cart, Order, OrderItem, Review

# Register BuyerProfile
@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'sign_up_method', 'created_at', 'updated_at')
    list_filter = ('sign_up_method', 'created_at')
    search_fields = ('user__username', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')

