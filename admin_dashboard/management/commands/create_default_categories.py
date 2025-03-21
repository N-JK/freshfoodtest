from django.core.management.base import BaseCommand
from admin_dashboard.models import FoodCategory

class Command(BaseCommand):
    help = 'Creates default food categories if none exist'

    def handle(self, *args, **kwargs):
        if FoodCategory.objects.exists():
            self.stdout.write(self.style.SUCCESS('Categories already exist'))
            return

        categories = [
            {
                'name': 'Fruits & Vegetables',
                'description': 'Fresh fruits and vegetables sourced directly from local farmers'
            },
            {
                'name': 'Dairy & Eggs',
                'description': 'Fresh dairy products and farm eggs'
            },
            {
                'name': 'Meat & Seafood',
                'description': 'Fresh meat and seafood products'
            },
            {
                'name': 'Bakery',
                'description': 'Fresh bread, cakes, and pastries'
            },
            {
                'name': 'Groceries',
                'description': 'Essential grocery items and pantry staples'
            },
            {
                'name': 'Beverages',
                'description': 'Fresh juices, soft drinks, and other beverages'
            },
            {
                'name': 'Snacks',
                'description': 'Healthy snacks and munchies'
            }
        ]

        for category_data in categories:
            FoodCategory.objects.create(**category_data)
            self.stdout.write(self.style.SUCCESS(f'Created category: {category_data["name"]}')
