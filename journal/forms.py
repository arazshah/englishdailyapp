from django import forms
from .models import JournalEntry, Tag

class JournalEntryForm(forms.ModelForm):
    tags = forms.CharField(required=False, 
                          widget=forms.TextInput(attrs={'class': 'form-control', 
                                                       'placeholder': 'Add tags (comma separated)'}))
    
    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'tags']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(JournalEntryForm, self).__init__(*args, **kwargs)
        
        if self.instance.pk:
            self.initial['tags'] = ', '.join([tag.name for tag in self.instance.tags.all()])
    
    def save(self, commit=True):
        instance = super(JournalEntryForm, self).save(commit=False)
        
        if commit:
            instance.save()
            
            # Clear existing tags
            instance.tags.clear()
            
            # Add new tags
            tag_names = [name.strip() for name in self.cleaned_data['tags'].split(',') if name.strip()]
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(name=tag_name, user=self.user)
                instance.tags.add(tag)
                
        return instance 