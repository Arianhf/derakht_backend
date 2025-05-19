# core/management/commands/init_feature_flags.py
from django.core.management.base import BaseCommand
from core.models import FeatureFlag


class Command(BaseCommand):
    help = 'Initialize default feature flags'

    def handle(self, *args, **options):
        DEFAULT_FLAGS = [
            {"name": "story_creation", "enabled": False, "description": "Story creation feature"},
            {"name": "illustrate_story", "enabled": False, "description": "Story illustration feature"},
            {"name": "complete_story", "enabled": False, "description": "Story completion feature"},
            {"name": "admin_dashboard", "enabled": False, "description": "Admin dashboard access"},
        ]

        for flag_data in DEFAULT_FLAGS:
            flag, created = FeatureFlag.objects.get_or_create(
                name=flag_data["name"],
                defaults={
                    "enabled": flag_data["enabled"],
                    "description": flag_data["description"]
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created flag: {flag.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Flag already exists: {flag.name}'))