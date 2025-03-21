from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings

class Command(BaseCommand):
    help = 'Updates the domain of the default site'

    def handle(self, *args, **options):
        site = Site.objects.get(id=settings.SITE_ID)
        site.domain = 'localhost:8000'
        site.name = 'Home Fresh'
        site.save()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully updated site domain to "%s"' % site.domain)
        )
