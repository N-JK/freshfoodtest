from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from seller.models import DeliveryBoy
from django.contrib.auth.models import User

class DeliveryBoyProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = DeliveryBoy
        fields = ['name', 'phone', 'email', 'address', 'profile_photo']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['username'].initial = user.username
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            
    def clean_username(self):
        username = self.cleaned_data.get('username')
        user_id = self.instance.user.id if self.instance and self.instance.user else None
        
        # Check if username exists but exclude current user
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
