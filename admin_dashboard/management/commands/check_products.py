from django.core.management.base import BaseCommand
from admin_dashboard.models import Product

class Command(BaseCommand):
    help = 'Check the status of products in the database'

    def handle(self, *args, **kwargs):
        # Get all products
        all_products = Product.objects.all()
        active_products = Product.objects.filter(is_active=True)
        inactive_products = Product.objects.filter(is_active=False)
        
        # Get pending products
        pending_products = Product.objects.filter(
            is_approved=False,
            is_active=True,
            supplier__is_active=True
        )
        
        # Get approved products
        approved_products = Product.objects.filter(
            is_approved=True,
            is_active=True,
            supplier__is_active=True
        )
        
        # Print summary
        self.stdout.write("\n=== Product Status Summary ===")
        self.stdout.write(f"Total products: {all_products.count()}")
        self.stdout.write(f"Active products: {active_products.count()}")
        self.stdout.write(f"Inactive products: {inactive_products.count()}")
        self.stdout.write(f"Pending approval: {pending_products.count()}")
        self.stdout.write(f"Approved products: {approved_products.count()}\n")
        
        # Print pending products
        if pending_products.exists():
            self.stdout.write("\n=== Pending Products ===")
            for product in pending_products:
                self.stdout.write(
                    f"- {product.name} (ID: {product.id})\n"
                    f"  Supplier: {product.supplier.business_name}\n"
                    f"  Category: {product.category.name}\n"
                    f"  Created: {product.created_at}\n"
                )
        else:
            self.stdout.write("\nNo pending products found.")
