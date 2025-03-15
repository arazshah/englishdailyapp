from django.db import models
from django.contrib.auth.models import User
from PIL import Image

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    email_notifications = models.BooleanField(default=True)
    reminder_notifications = models.BooleanField(default=True)
    theme_preference = models.CharField(max_length=10, default='system', 
                                       choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System Default')])
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize profile image if needed
        if self.image:
            try:
                img = Image.open(self.image.path)
                
                # Check if image needs resizing
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.image.path)
            except Exception as e:
                # Handle the case where the image file might not be accessible
                print(f"Error processing image: {e}") 