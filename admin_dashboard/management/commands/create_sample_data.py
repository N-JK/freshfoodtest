from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from admin_dashboard.models import FoodCategory, Location, Supplier, Product
from decimal import Decimal

class Command(BaseCommand):
    help = 'Creates sample categories and products'

    def handle(self, *args, **kwargs):
        # Create categories if they don't exist
        categories_data = [
            {
                'name': 'Fruits',
                'description': 'Fresh fruits sourced directly from local farmers'
            },
            {
                'name': 'Vegetables',
                'description': 'Fresh vegetables sourced directly from local farmers'
            },
            {
                'name': 'Dairy',
                'description': 'Fresh dairy products'
            },
            {
                'name': 'Bakery',
                'description': 'Fresh bread and pastries'
            }
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = FoodCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))

        # Create a test location if it doesn't exist
        location, created = Location.objects.get_or_create(
            name='Test Location',
            defaults={
                'city': 'Test City',
                'state': 'Test State',
                'country': 'India',
                'pincode': '123456',
                'address': 'Test Address'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created location: {location.name}'))

        # Create a test supplier if it doesn't exist
        supplier_user, created = User.objects.get_or_create(
            username='supplier1',
            defaults={
                'email': 'supplier1@example.com',
                'is_active': True
            }
        )
        if created:
            supplier_user.set_password('password123')
            supplier_user.save()

        supplier, created = Supplier.objects.get_or_create(
            user=supplier_user,
            defaults={
                'business_name': 'Test Supplier',
                'contact_number': '1234567890',
                'address': 'Test Address',
                'location': location,
                'is_active': True
            }
        )
        if created:
            supplier.categories.set(categories.values())
            self.stdout.write(self.style.SUCCESS(f'Created supplier: {supplier.business_name}'))

        # Create sample products
        products_data = {
            'Fruits': [
                ('Apple', 'Fresh red apples', Decimal('80.00'), 100),
                ('Banana', 'Fresh yellow bananas', Decimal('40.00'), 150),
                ('Orange', 'Sweet oranges', Decimal('60.00'), 100),
                ('Mango', 'Sweet mangoes', Decimal('100.00'), 80),
            ],
            'Vegetables': [
                ('Tomato', 'Fresh red tomatoes', Decimal('40.00'), 200),
                ('Potato', 'Fresh potatoes', Decimal('30.00'), 300),
                ('Onion', 'Fresh onions', Decimal('35.00'), 250),
                ('Carrot', 'Fresh carrots', Decimal('45.00'), 150),
            ],
            'Dairy': [
                ('Milk', 'Fresh cow milk', Decimal('60.00'), 100),
                ('Curd', 'Fresh curd', Decimal('40.00'), 100),
                ('Butter', 'Fresh butter', Decimal('120.00'), 50),
                ('Cheese', 'Fresh cheese', Decimal('150.00'), 40),
            ],
            'Bakery': [
                ('Bread', 'Fresh bread', Decimal('40.00'), 50),
                ('Cake', 'Fresh cake', Decimal('300.00'), 20),
                ('Cookies', 'Fresh cookies', Decimal('100.00'), 100),
                ('Muffins', 'Fresh muffins', Decimal('80.00'), 60),
            ]
        }

        for category_name, products in products_data.items():
            category = categories[category_name]
            for name, description, price, stock in products:
                product, created = Product.objects.get_or_create(
                    name=name,
                    category=category,
                    supplier=supplier,
                    defaults={
                        'description': description,
                        'price': price,
                        'stock': stock,
                        'is_approved': True,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created product: {product.name} in {category.name}'))
