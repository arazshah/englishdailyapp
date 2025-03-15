from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from journal.models import JournalEntry
from journal.markdown_utils import load_entry_from_markdown
import os
import glob
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports journal entries from markdown files'

    def add_arguments(self, parser):
        parser.add_argument('--directory', type=str, help='Directory containing markdown files')
        parser.add_argument('--user', type=int, help='User ID to assign entries to')

    def handle(self, *args, **options):
        directory = options.get('directory')
        if not directory:
            directory = os.path.join(settings.MEDIA_ROOT, 'markdown_entries')
        
        user_id = options.get('user')
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.stdout.write(f"Using user: {user.username}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
                return
        
        if not os.path.exists(directory):
            self.stdout.write(self.style.ERROR(f"Directory {directory} does not exist"))
            return
        
        markdown_files = glob.glob(os.path.join(directory, '*.md'))
        self.stdout.write(f"Found {len(markdown_files)} markdown files")
        
        imported = 0
        updated = 0
        
        for file_path in markdown_files:
            try:
                entry_data = load_entry_from_markdown(file_path)
                
                if not entry_data:
                    self.stdout.write(self.style.ERROR(f"Failed to load data from {file_path}"))
                    continue
                
                # Check if entry exists
                entry_id = entry_data.get('id')
                if entry_id:
                    try:
                        entry = JournalEntry.objects.get(id=entry_id)
                        # Update existing entry
                        entry.title = entry_data.get('title', entry.title)
                        entry.content = entry_data.get('content', entry.content)
                        entry.polished_content = entry_data.get('polished_content', entry.polished_content)
                        entry.topic = entry_data.get('topic', entry.topic)
                        entry.evaluation = entry_data.get('evaluation', entry.evaluation)
                        entry.diff_html = entry_data.get('diff_html', entry.diff_html)
                        entry.metrics_data = entry_data.get('metrics', entry.metrics_data)
                        entry.is_polished = entry_data.get('is_polished', entry.is_polished)
                        entry.markdown_path = file_path
                        entry.save()
                        updated += 1
                        self.stdout.write(f"Updated entry {entry.id}: {entry.title}")
                    except JournalEntry.DoesNotExist:
                        # Create new entry
                        if not user and entry_data.get('author_id'):
                            try:
                                user = User.objects.get(id=entry_data.get('author_id'))
                            except User.DoesNotExist:
                                self.stdout.write(self.style.ERROR(f"User with ID {entry_data.get('author_id')} not found"))
                                continue
                        
                        if not user:
                            self.stdout.write(self.style.ERROR(f"No user specified for new entry from {file_path}"))
                            continue
                        
                        entry = JournalEntry(
                            id=entry_id,
                            title=entry_data.get('title', 'Imported Entry'),
                            content=entry_data.get('content', ''),
                            polished_content=entry_data.get('polished_content', ''),
                            topic=entry_data.get('topic', ''),
                            evaluation=entry_data.get('evaluation', ''),
                            diff_html=entry_data.get('diff_html', ''),
                            metrics_data=entry_data.get('metrics', {}),
                            is_polished=entry_data.get('is_polished', False),
                            author=user,
                            markdown_path=file_path
                        )
                        
                        # Handle date_posted
                        if entry_data.get('date_posted'):
                            try:
                                entry.date_posted = datetime.fromisoformat(entry_data.get('date_posted'))
                            except (ValueError, TypeError):
                                pass
                        
                        entry.save()
                        imported += 1
                        self.stdout.write(f"Imported new entry: {entry.title}")
                else:
                    self.stdout.write(self.style.ERROR(f"No entry ID found in {file_path}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {file_path}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Imported {imported} new entries and updated {updated} existing entries")) 