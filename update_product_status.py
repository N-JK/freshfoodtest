import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fresh_food_final.settings')
django.setup()

from admin_dashboard.models import Product

# Update all existing products to 'approved' status
Product.objects.all().update(status='approved')

print("All products have been updated to 'approved' status")
