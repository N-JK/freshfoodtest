# adapters.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import User
from .models import BuyerProfile

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Check if the user already exists
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                if user:
                    # If the user exists and is linked to a Google account, log them in
                    if sociallogin.is_existing:
                        return
                    # If the user exists but is not linked to a Google account, prompt login
                    else:
                        messages.info(request, 'An account with this email already exists. Please log in using your existing credentials.')
                        return redirect(reverse('account_login'))
            except User.DoesNotExist:
                pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Ensure a BuyerProfile is created for the user
        buyer_profile, created = BuyerProfile.objects.get_or_create(user=user)
        if created:
            buyer_profile.sign_up_method = 'google'
            buyer_profile.save()
        return user