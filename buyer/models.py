from django.db import models
from django.contrib.auth.models import User
from admin_dashboard.models import Product
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    profile_picture = models.ImageField(upload_to='buyer_profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sign_up_method = models.CharField(max_length=10, choices=[('google', 'Google'), ('form', 'Form')], default='form')

    def __str__(self):
        return self.user.username
    class Meta:
        # Ensure only one profile per user
        unique_together = ('user',)

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username}'s wishlist - {self.product.name}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        unique_together = ('user', 'product')

    def get_total(self):
        return self.quantity * self.product.price

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay')
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    )
    ORDER_STATUS_CHOICES = (
        ('pending', 'Payment'),
        ('confirmed', 'Order Confirmation'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    delivery_boy = models.ForeignKey('seller.DeliveryBoy', on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Order #{self.id} by {self.user.username}'
    
    def get_total_items(self):
        return self.order_items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def get_status_badge_class(self):
        status_classes = {
            'pending': 'bg-warning',
            'confirmed': 'bg-primary',
            'out_for_delivery': 'bg-info',
            'delivered': 'bg-success',
            'cancelled': 'bg-danger'
        }
        return status_classes.get(self.order_status, 'bg-secondary')

    def get_payment_status_badge_class(self):
        status_classes = {
            'pending': 'bg-warning',
            'paid': 'bg-success',
            'failed': 'bg-danger',
            'refunded': 'bg-info'
        }
        return status_classes.get(self.payment_status, 'bg-secondary')
        
    def can_cancel(self):
        """Check if order can be cancelled based on time and status"""
        if self.order_status in ['out_for_delivery', 'delivered', 'cancelled']:
            return False
            
        # Check if order is within 1 hour
        time_difference = timezone.now() - self.created_at
        return time_difference <= timedelta(hours=1)
        
    def cancel_order(self):
        """Cancel the order and restore product stock"""
        if not self.can_cancel():
            raise ValueError("This order cannot be cancelled")
            
        # Restore product stock
        for item in self.order_items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
            
        # Update order status
        self.order_status = 'cancelled'
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total(self):
        return self.quantity * self.price

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username}'s review for {self.product.name}"
