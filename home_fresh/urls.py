"""
URL configuration for home_fresh project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

urlpatterns = [
    # Admin URLs
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include(('admin_dashboard.urls', 'admin_dashboard'), namespace='admin_dashboard')),  # Admin dashboard URLs
    
    # Authentication URLs
    path('accounts/', include('allauth.urls')),  # django-allauth URLs
    path('api-auth/', include('rest_framework.urls')),
    
    # App URLs
    path('', include(('home.urls', 'home'), namespace='home')),  # Home app URLs
    path('seller/', include(('seller.urls', 'seller'), namespace='seller')),  # Seller app URLs
    path('buyer/', include(('buyer.urls', 'buyer'), namespace='buyer')),  # Buyer app URLs
    path('delivery/', include(('delivery.urls', 'delivery'), namespace='delivery')),  # Delivery app URLs
    
    # Password Reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='buyer/auth/password_reset.html',
        email_template_name='buyer/auth/password_reset_email.html',
        subject_template_name='buyer/auth/password_reset_subject.txt'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='buyer/auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='buyer/auth/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='buyer/auth/password_reset_complete.html'
    ), name='password_reset_complete'),
]

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve static and media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add a handler for 404 pages
handler404 = 'home.views.custom_404'
