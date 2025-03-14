from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse

class JournalEntry(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    polished_content = models.TextField(blank=True, null=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_polished = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('journal-detail', kwargs={'pk': self.pk})
    
    class Meta:
        verbose_name_plural = "Journal Entries" 