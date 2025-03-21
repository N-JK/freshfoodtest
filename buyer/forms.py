from django import forms
from .models import BuyerProfile, Address, Review
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model


class BuyerProfileForm(forms.ModelForm):
    class Meta:
        model = BuyerProfile
        fields = ['phone_number', 'address', 'profile_picture']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'phone_number', 'address_line1', 'address_line2', 'city', 'state', 'pincode']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House/Flat No., Street Name'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Landmark (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PIN Code'}),
        }
        
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        if len(phone) < 10:
            raise forms.ValidationError('Please enter a valid phone number with at least 10 digits.')
        return phone
        
    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        # Remove any non-digit characters
        pincode = ''.join(filter(str.isdigit, pincode))
        if len(pincode) != 6:
            raise forms.ValidationError('Please enter a valid 6-digit PIN code.')
        return pincode

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }




User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        users = User.objects.filter(email__iexact=email)
        
        if not users.exists():
            return email
            
        # Check if any user has Google signup method
        for user in users:
            try:
                if user.buyerprofile.sign_up_method == 'google':
                    raise forms.ValidationError(
                        "Password management is handled through Google. Please use Google to manage your password."
                    )
            except BuyerProfile.DoesNotExist:
                continue
                
        return email
    

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.user.buyerprofile.sign_up_method == 'form':
            password = cleaned_data.get('password')
            if not password:
                raise forms.ValidationError("Password is required to delete your account.")
            if not self.user.check_password(password):
                raise forms.ValidationError("Incorrect password.")
        return cleaned_data