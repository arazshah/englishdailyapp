from django.core.management.base import BaseCommand
from journal.models import JournalEntry
from journal.utils import load_polish_data_from_json
import os
import glob
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Converts JSON polish data to markdown files'

    def add_arguments(self, parser):
        parser.add_argument('--entry-id', type=int, help='Specific entry ID to convert')

    def handle(self, *args, **options):
        json_dir = os.path.join(settings.MEDIA_ROOT, 'polish_data')
        if not os.path.exists(json_dir):
            self.stdout.write(self.style.ERROR(f"Directory {json_dir} does not exist"))
            return
        
        entry_id = options.get('entry_id')
        
        if entry_id:
            # Convert specific entry
            self.stdout.write(f"Converting JSON data for entry {entry_id}")
            json_files = glob.glob(os.path.join(json_dir, f"{entry_id}_*.json"))
        else:
            # Convert all entries
            self.stdout.write(f"Converting all JSON data")
            json_files = glob.glob(os.path.join(json_dir, "*.json"))
        
        self.stdout.write(f"Found {len(json_files)} JSON files")
        
        converted = 0
        
        for json_file in json_files:
            try:
                # Load the JSON data
                data = load_polish_data_from_json(json_file)
                
                if not data:
                    self.stdout.write(self.style.ERROR(f"Failed to load data from {json_file}"))
                    continue
                
                # Get the entry ID from the data
                entry_id = data.get('entry_id')
                
                if not entry_id:
                    self.stdout.write(self.style.ERROR(f"No entry ID found in {json_file}"))
                    continue
                
                # Get the entry
                try:
                    entry = JournalEntry.objects.get(id=entry_id)
                except JournalEntry.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Entry {entry_id} not found"))
                    continue
                
                # Update the entry with the JSON data
                entry.polished_content = data.get('polished_content', '')
                entry.topic = data.get('topic', '')
                entry.evaluation = data.get('evaluation', '')
                entry.diff_html = data.get('diff_html', '')
                entry.metrics_data = data.get('metrics', {})
                entry.is_polished = True
                
                # Save the entry
                entry.save()
                
                # Save as markdown
                markdown_path = entry.save_as_markdown()
                
                if markdown_path:
                    converted += 1
                    self.stdout.write(self.style.SUCCESS(f"Converted {json_file} to {markdown_path}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to convert {json_file}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {json_file}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Converted {converted} out of {len(json_files)} JSON files to markdown")) 