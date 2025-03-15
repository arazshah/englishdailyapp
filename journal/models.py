import os
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

class JournalEntry(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_polished = models.BooleanField(default=False)
    polished_content = models.TextField(blank=True, null=True)
    polish_date = models.DateTimeField(blank=True, null=True)
    evaluation = models.TextField(blank=True, null=True)
    topic = models.CharField(max_length=100, blank=True, null=True)
    diff_html = models.TextField(blank=True, null=True)
    metrics_data = models.JSONField(blank=True, null=True)
    markdown_path = models.CharField(max_length=255, blank=True, null=True)
    tags = models.ManyToManyField('Tag', blank=True)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('journal-detail', kwargs={'pk': self.pk})
    
    def save_as_markdown(self):
        """Save the entry as a markdown file and store the path."""
        from journal.markdown_utils import save_entry_as_markdown
        self.markdown_path = save_entry_as_markdown(self)
        self.save(update_fields=['markdown_path'])
        return self.markdown_path
    
    def load_from_markdown(self):
        """Load entry data from the associated markdown file."""
        if not self.markdown_path or not os.path.exists(self.markdown_path):
            return False
            
        from journal.markdown_utils import load_entry_from_markdown
        entry_data = load_entry_from_markdown(self.markdown_path)
        
        if entry_data:
            self.content = entry_data['content']
            self.polished_content = entry_data['polished_content']
            self.topic = entry_data['topic']
            self.evaluation = entry_data['evaluation']
            self.diff_html = entry_data['diff_html']
            self.metrics_data = entry_data['metrics']
            self.is_polished = entry_data['is_polished']
            return True
            
        return False
    
    class Meta:
        verbose_name_plural = "Journal Entries" 