from django.core.management.base import BaseCommand
from stories.models import Story, StoryPart


class Command(BaseCommand):
    help = 'Delete all stories and story parts from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        # Count existing records
        story_count = Story.objects.count()
        story_part_count = StoryPart.objects.count()

        if story_count == 0 and story_part_count == 0:
            self.stdout.write(self.style.WARNING('No stories or story parts found.'))
            return

        self.stdout.write(
            self.style.WARNING(
                f'Found {story_count} stories and {story_part_count} story parts.'
            )
        )

        # Confirmation prompt unless --no-confirm is used
        if not options['no_confirm']:
            confirm = input('Are you sure you want to delete all stories and story parts? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        # Delete all story parts first (optional, since CASCADE will handle it)
        story_parts_deleted, _ = StoryPart.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {story_parts_deleted} story parts.')
        )

        # Delete all stories (this will also cascade delete related story parts)
        stories_deleted, _ = Story.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {stories_deleted} stories.')
        )

        self.stdout.write(
            self.style.SUCCESS('All stories and story parts have been deleted successfully!')
        )
