from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
    path('save-settings/', views.save_settings, name='save_settings'),
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='users/password_change.html',
             success_url='/users/profile/'
         ), 
         name='password_change'),
    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='users/password_change_done.html'
         ), 
         name='password_change_done'),
] 