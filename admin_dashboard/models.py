from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
import json

class FoodCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Food Categories'

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=6)
    address = models.TextField(default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Clean pincode
        if self.pincode:
            self.pincode = self.pincode.strip()
            if not self.pincode.isdigit() or len(self.pincode) != 6:
                raise ValidationError({'pincode': 'Pincode must be a 6-digit number'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.city}"

    class Meta:
        ordering = ['name']
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

class Supplier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    address = models.TextField()
    locations = models.ManyToManyField(Location, related_name='suppliers', blank=True)
    categories = models.ManyToManyField(FoodCategory, related_name='suppliers', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Validate contact number
        if not self.contact_number.isdigit():
            raise ValidationError({'contact_number': 'Contact number must contain only digits'})
        if len(self.contact_number) < 10 or len(self.contact_number) > 15:
            raise ValidationError({'contact_number': 'Contact number must be between 10 and 15 digits'})
        
        # Validate business name
        if len(self.business_name.strip()) < 3:
            raise ValidationError({'business_name': 'Business name must be at least 3 characters long'})
        
        # Validate address
        if len(self.address.strip()) < 10:
            raise ValidationError({'address': 'Address must be at least 10 characters long'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.business_name} ({self.user.username})"

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['business_name']

class Product(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('pc', 'Piece'),
        ('pack', 'Pack'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    threshold = models.IntegerField(default=10, help_text="Stock level at which to trigger restock request")
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def needs_restock(self):
        """Check if product needs restocking"""
        return self.stock <= self.threshold

    def save(self, *args, **kwargs):
        # Check if this is a new product
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Only check for restock if this is an existing product being updated
        if not is_new:
            # Signal handler will handle the restock request creation
            pass

class RestockRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Restock Request for {self.product.name} - {self.quantity} units"

    def complete_restock(self):
        if self.status == 'approved':
            self.product.stock += self.quantity
            self.product.save()
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()

    class Meta:
        ordering = ['-requested_at']

class DeliveryLocation(models.Model):
    name = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.pincode}"

    class Meta:
        verbose_name = "Delivery Location"
        verbose_name_plural = "Delivery Locations"

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15)
    address = models.TextField()
    location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        # Validate phone
        if not self.phone.isdigit():
            raise ValidationError({'phone': 'Phone number must contain only digits'})
        if len(self.phone) < 10 or len(self.phone) > 15:
            raise ValidationError({'phone': 'Phone number must be between 10 and 15 digits'})

        # Validate address
        if len(self.address.strip()) < 10:
            raise ValidationError({'address': 'Address must be at least 10 characters long'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"

@receiver(post_save, sender=Product)
def create_restock_request(sender, instance, **kwargs):
    """
    Signal to automatically create a restock request when product stock falls below threshold
    """
    if instance.stock <= instance.threshold:
        # Check if there's already a pending restock request
        existing_request = RestockRequest.objects.filter(
            product=instance,
            status='pending'
        ).exists()
        
        if not existing_request:
            # Calculate quantity needed (2x threshold - current stock)
            quantity_needed = (instance.threshold * 2) - instance.stock
            
            RestockRequest.objects.create(
                product=instance,
                quantity=quantity_needed,
                status='pending',
                notes='Automatic restock request - Stock below threshold'
            )
