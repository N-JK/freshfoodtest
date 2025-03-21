# buyer/management/commands/cleanup_buyer_profiles.py
from django.core.management.base import BaseCommand
from django.db.models import Count
from buyer.models import BuyerProfile
from django.db import transaction

class Command(BaseCommand):
    help = 'Cleanup duplicate BuyerProfile instances'

    def handle(self, *args, **kwargs):
        # Find users with multiple profiles
        duplicate_users = (BuyerProfile.objects
            .values('user')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        for duplicate in duplicate_users:
            user_id = duplicate['user']
            profiles = BuyerProfile.objects.filter(user_id=user_id).order_by('created_at')
            
            try:
                with transaction.atomic():
                    # Keep the most recent profile
                    profiles_to_delete = profiles[:-1]
                    
                    self.stdout.write(self.style.WARNING(f'Cleaning up {profiles_to_delete.count()} duplicate profiles for user {user_id}'))
                    
                    # Delete duplicate profiles
                    profiles_to_delete.delete()
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error cleaning up profiles for user {user_id}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('Profile cleanup completed'))