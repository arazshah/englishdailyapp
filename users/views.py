from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from django.http import JsonResponse
import json
from django.views.decorators.http import require_POST
from .models import Profile
from django.urls import get_resolver
from django.http import HttpResponse

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create a profile for the new user
            Profile.objects.create(user=user)
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    # Ensure the user has a profile
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)  # Create a profile if it doesn't exist

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('users:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    
    return render(request, 'users/profile.html', context)

@login_required
@require_POST
def upload_profile_image(request):
    if 'profile_image' in request.FILES:
        profile = request.user.profile
        profile.image = request.FILES['profile_image']
        profile.save()
        messages.success(request, 'Profile image updated successfully!')
    else:
        messages.error(request, 'No image file was provided.')
    
    return redirect('users:profile')

@login_required
@require_POST
def save_settings(request):
    try:
        data = json.loads(request.body)
        profile = request.user.profile
        
        # Update profile settings
        profile.email_notifications = data.get('email_notifications', True)
        profile.reminder_notifications = data.get('reminder_notifications', True)
        profile.theme_preference = data.get('theme_preference', 'system')
        profile.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def create_profile(request):
    if request.method == 'POST':
        p_form = ProfileUpdateForm(request.POST)
        if p_form.is_valid():
            profile = p_form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Your profile has been created!')
            return redirect('users:profile')
    else:
        p_form = ProfileUpdateForm()

    return render(request, 'users/create_profile.html', {'p_form': p_form})

def debug_urls(request):
    resolver = get_resolver()
    url_patterns = sorted([
        pattern.name for pattern in resolver.url_patterns if hasattr(pattern, 'name') and pattern.name
    ])
    return HttpResponse('<br>'.join(url_patterns)) 