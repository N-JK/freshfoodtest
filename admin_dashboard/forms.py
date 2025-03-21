from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Supplier, Location, FoodCategory

class SupplierAdminForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    locations = forms.ModelMultipleChoiceField(
        queryset=Location.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text='Select one or more locations'
    )
    
    categories = forms.ModelMultipleChoiceField(
        queryset=FoodCategory.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text='Select one or more categories'
    )

    class Meta:
        model = Supplier
        fields = ['first_name', 'last_name', 'email', 'business_name', 'contact_number', 'address', 'locations', 'categories']
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business name'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact number',
                'pattern': '[0-9]{10,15}'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter complete address',
                'rows': 3
            })
        }

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if not contact_number:
            raise ValidationError('Contact number is required.')
        if not contact_number.isdigit():
            raise ValidationError('Contact number must contain only digits.')
        if len(contact_number) < 10 or len(contact_number) > 15:
            raise ValidationError('Contact number must be between 10 and 15 digits.')
        return contact_number

    def clean_business_name(self):
        business_name = self.cleaned_data.get('business_name')
        if not business_name:
            raise ValidationError('Business name is required.')
        if len(business_name.strip()) < 3:
            raise ValidationError('Business name must be at least 3 characters long.')
        return business_name.strip()

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if not address:
            raise ValidationError('Address is required.')
        if len(address.strip()) < 10:
            raise ValidationError('Address must be at least 10 characters long.')
        return address.strip()

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
