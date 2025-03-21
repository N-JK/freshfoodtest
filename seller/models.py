from django.db import models
from django.contrib.auth.models import User
from admin_dashboard.models import Product, RestockRequest, Location
from django.core.exceptions import ValidationError

# Create your models here.

class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    supplier = models.OneToOneField('admin_dashboard.Supplier', on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    profile_picture = models.ImageField(upload_to='seller_profiles/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.supplier.business_name}"

class SellerNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('restock_request', 'Restock Request'),
        ('product_approval', 'Product Approval'),
        ('low_stock', 'Low Stock Alert'),
        ('other', 'Other')
    ]

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    related_restock_request = models.ForeignKey(RestockRequest, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.seller.user.get_full_name()}"

class SellerAnalytics(models.Model):
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    total_products = models.IntegerField(default=0)
    active_products = models.IntegerField(default=0)
    pending_approvals = models.IntegerField(default=0)
    low_stock_items = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('seller', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"Analytics for {self.seller.user.get_full_name()} on {self.date}"

class DeliveryBoy(models.Model):
    AVAILABILITY_STATUS = [
        ('available', 'Available'),
        ('on_delivery', 'On Delivery'),
        ('offline', 'Offline')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='delivery_boys')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    id_proof = models.ImageField(upload_to='delivery_boys/id_proofs/')
    profile_photo = models.ImageField(upload_to='delivery_boys/profiles/')
    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)
    assigned_location = models.ForeignKey(Location, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS, default='available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.assigned_location.name}"

    def save(self, *args, **kwargs):
        # Ensure delivery boy is assigned to a location where seller operates
        if not self.seller.supplier.locations.filter(id=self.assigned_location.id).exists():
            raise ValidationError("Delivery boy can only be assigned to seller's operating locations")
        super().save(*args, **kwargs)
