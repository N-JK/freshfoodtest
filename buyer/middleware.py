from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
# buyer/middleware.py

class PincodeVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path.startswith('/buyer/'):
            # Skip middleware for these URLs
            exempt_urls = [
                reverse('buyer:verify_location'),
                reverse('buyer:clear_location_modal'),
                reverse('buyer:logout'),
            ]
            
            if request.path not in exempt_urls:
                # Check if user has verified pincode
                can_shop = request.session.get('can_shop', False)
                delivery_pincode = request.session.get('delivery_pincode')
                
                if not can_shop or not delivery_pincode:
                    request.session['show_location_modal'] = True
                    messages.warning(request, 'Please verify your delivery pincode to continue shopping.')
                    return redirect('home:home')  # Ensure 'home:home' is correct

        response = self.get_response(request)
        return response