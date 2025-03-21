from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from django.template.response import TemplateResponse
from .models import Product, FoodCategory, Supplier, CustomerProfile, Location, DeliveryLocation, RestockRequest
from .forms import SupplierAdminForm

class SupplierInline(admin.StackedInline):
    model = Supplier
    can_delete = False
    verbose_name_plural = 'Supplier'

class CustomUserAdmin(UserAdmin):
    inlines = (SupplierInline, )

# Unregister the default User admin and register with our custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'supplier', 'price', 'stock', 'is_featured']
    list_filter = ['category', 'supplier', 'is_featured']
    search_fields = ['name', 'description', 'supplier__business_name']
    list_editable = ['is_featured']
    actions = ['make_featured', 'remove_featured']
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image'

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"{queryset.count()} products marked as featured.")
    make_featured.short_description = "Mark selected products as featured"

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f"{queryset.count()} products removed from featured.")
    remove_featured.short_description = "Remove selected products from featured"

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'supplier', 'description', 'image')
        }),
        ('Pricing and Stock', {
            'fields': ('price', 'unit', 'stock', 'threshold')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active', 'is_featured')
        }),
    )

@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ('name',)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'pincode']
    search_fields = ['name', 'pincode']
    ordering = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    form = SupplierAdminForm
    list_display = ('business_name', 'user', 'contact_number', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('business_name', 'user__username', 'contact_number')
    filter_horizontal = ('locations', 'categories')
    ordering = ('business_name',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['make_active', 'make_inactive', 'delete_selected']
    
    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories.short_description = 'Categories'

    def get_locations(self, obj):
        return ", ".join([l.name for l in obj.locations.all()])
    get_locations.short_description = 'Locations'

    def actions_buttons(self, obj):
        edit_url = reverse('admin:admin_dashboard_supplier_change', args=[obj.pk])
        delete_url = reverse('admin:admin_dashboard_supplier_delete', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">Edit</a>&nbsp;'
            '<a class="button" style="background: #ba2121; color: white;" href="{}">Delete</a>',
            edit_url, delete_url
        )
    actions_buttons.short_description = 'Actions'
    actions_buttons.allow_tags = True

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} suppliers have been marked as active.')
    make_active.short_description = "Mark selected suppliers as active"

    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} suppliers have been marked as inactive.')
    make_inactive.short_description = "Mark selected suppliers as inactive"

    def delete_model(self, request, obj):
        try:
            user = obj.user
            obj.delete()
            messages.success(request, f'Supplier "{obj.business_name}" has been successfully deleted.')
        except Exception as e:
            messages.error(request, f'Error deleting supplier: {str(e)}')
            raise

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
            action = "updated" if change else "created"
            messages.success(request, f'Supplier "{obj.business_name}" has been successfully {action}.')
        except Exception as e:
            messages.error(request, f'Error saving supplier: {str(e)}')
            raise

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'business_name', 'contact_number', 'address')
        }),
        ('Associations', {
            'fields': ('locations', 'categories')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'location', 'is_active']
    list_filter = ['is_active', 'location']
    search_fields = ['user__username', 'phone']

@admin.register(DeliveryLocation)
class DeliveryLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'pincode')
    search_fields = ('name', 'pincode')
    ordering = ('name',)

@admin.register(RestockRequest)
class RestockRequestAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'status', 'requested_at')
    list_filter = ('status', 'product__supplier')
    search_fields = ('product__name', 'notes')
    ordering = ('-requested_at',)
    readonly_fields = ('requested_at', 'updated_at')
