from django.core.management.base import BaseCommand
from journal.models import JournalEntry
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Converts all journal entries to markdown format'

    def handle(self, *args, **options):
        entries = JournalEntry.objects.filter(is_polished=True)
        total = entries.count()
        converted = 0
        
        self.stdout.write(f"Found {total} polished entries to convert to markdown")
        
        for entry in entries:
            try:
                if not entry.markdown_path:
                    path = entry.save_as_markdown()
                    if path:
                        converted += 1
                        self.stdout.write(self.style.SUCCESS(f"Converted entry {entry.id}: {entry.title}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to convert entry {entry.id}: {entry.title}"))
                else:
                    self.stdout.write(f"Entry {entry.id} already has a markdown path: {entry.markdown_path}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error converting entry {entry.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Converted {converted} out of {total} entries to markdown format")) 