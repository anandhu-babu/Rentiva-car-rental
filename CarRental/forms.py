import re
from datetime import date

from django import forms
from django.contrib.auth.models import User

from .models import Car, Profile


BRAND_CHOICES = [
    ('', 'Select Brand'),
    ('Audi', 'Audi'),
    ('BMW', 'BMW'),
    ('Ford', 'Ford'),
    ('Honda', 'Honda'),
    ('Hyundai', 'Hyundai'),
    ('Jaguar', 'Jaguar'),
    ('Jeep', 'Jeep'),
    ('Kia', 'Kia'),
    ('Mahindra', 'Mahindra'),
    ('Mercedes-Benz', 'Mercedes-Benz'),
    ('Nissan', 'Nissan'),
    ('Maruti Suzuki', 'Maruti Suzuki'),
    ('Tata', 'Tata'),
    ('Toyota', 'Toyota'),
    ('Volkswagen', 'Volkswagen'),
    ('Other', 'Other'),
]


class CarForm(forms.ModelForm):
    brand           = forms.ChoiceField(choices=BRAND_CHOICES, required=False)
    year            = forms.IntegerField(min_value=2000, max_value=2030)
    seats           = forms.IntegerField(min_value=1, max_value=12)
    rent_per_day    = forms.FloatField(min_value=100)
    weekly_rent     = forms.FloatField(required=False, min_value=0)
    monthly_rent    = forms.FloatField(required=False, min_value=0)
    delivery_radius = forms.FloatField(required=False, min_value=0)
    delivery_charge = forms.FloatField(required=False, min_value=0)

    class Meta:
        model = Car
        exclude = ['owner', 'car_status', 'verification_status', 'created_at']
        widgets = {
            'available_from': forms.DateInput(attrs={'type': 'date'}),
            'available_to':   forms.DateInput(attrs={'type': 'date'}),
        }


class BrandOption:
    def __init__(self, name):
        self.id   = name
        self.name = name


_ALLOWED_DOC_EXT   = {'jpg', 'jpeg', 'png', 'pdf'}
_ALLOWED_PHOTO_EXT = {'jpg', 'jpeg', 'png'}
_MAX_DOC_BYTES     = 5 * 1024 * 1024
_MAX_PHOTO_BYTES   = 2 * 1024 * 1024


def _ext(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def _validate_doc(f, field_label='Document'):
    if f:
        if _ext(f.name) not in _ALLOWED_DOC_EXT:
            raise forms.ValidationError(f'{field_label}: Only JPG, JPEG, PNG, and PDF files are allowed.')
        if f.size > _MAX_DOC_BYTES:
            raise forms.ValidationError(f'{field_label}: File size must be under 5 MB.')
    return f


class CustomerRegistrationForm(forms.Form):
    first_name             = forms.CharField(max_length=50)
    last_name              = forms.CharField(max_length=50)
    email                  = forms.EmailField(label='Email Address')
    phone                  = forms.CharField(max_length=10, label='Phone Number')
    password1              = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2              = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    dob                    = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='Date of Birth')
    driving_license_number = forms.CharField(max_length=50, label='Driving Licence Number')
    driving_license_file   = forms.FileField(label='Driving Licence Upload')
    government_id_file     = forms.FileField(label='Government ID (Aadhaar / PAN / Passport)')

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not phone.isdigit() or len(phone) != 10:
            raise forms.ValidationError('Enter a valid 10-digit phone number.')
        if Profile.objects.filter(phone=phone).exists():
            raise forms.ValidationError('This phone number is already registered.')
        return phone

    def clean_dob(self):
        dob = self.cleaned_data['dob']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise forms.ValidationError('You must be at least 18 years old to register.')
        return dob

    def clean_driving_license_file(self):
        return _validate_doc(self.cleaned_data.get('driving_license_file'), 'Driving Licence')

    def clean_government_id_file(self):
        return _validate_doc(self.cleaned_data.get('government_id_file'), 'Government ID')

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1', '')
        p2 = cleaned.get('password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned


class RenterRegistrationForm(forms.Form):
    first_name             = forms.CharField(max_length=50)
    last_name              = forms.CharField(max_length=50)
    email                  = forms.EmailField(label='Email Address')
    phone                  = forms.CharField(max_length=10, label='Phone Number')
    password1              = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2              = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    address                = forms.CharField(widget=forms.Textarea, label='Full Address')
    dob                    = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='Date of Birth')
    driving_license_number = forms.CharField(max_length=50, label='Driving Licence Number')
    driving_license_file   = forms.FileField(label='Driving Licence Upload')
    government_id_file     = forms.FileField(label='Government ID (Aadhaar / PAN / Passport)')
    aadhaar_pan            = forms.CharField(max_length=20, required=False, label='Aadhaar / PAN Number (Optional)')
    bank_account_holder    = forms.CharField(max_length=100, label='Account Holder Name')
    bank_account_number    = forms.CharField(max_length=20, label='Bank Account Number')
    ifsc_code              = forms.CharField(max_length=11, label='IFSC Code')
    profile_photo          = forms.ImageField(label='Profile Photo')

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not phone.isdigit() or len(phone) != 10:
            raise forms.ValidationError('Enter a valid 10-digit phone number.')
        if Profile.objects.filter(phone=phone).exists():
            raise forms.ValidationError('This phone number is already registered.')
        return phone

    def clean_dob(self):
        dob = self.cleaned_data['dob']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise forms.ValidationError('You must be at least 18 years old to register.')
        return dob

    def clean_driving_license_file(self):
        return _validate_doc(self.cleaned_data.get('driving_license_file'), 'Driving Licence')

    def clean_government_id_file(self):
        return _validate_doc(self.cleaned_data.get('government_id_file'), 'Government ID')

    def clean_ifsc_code(self):
        ifsc = self.cleaned_data.get('ifsc_code', '').upper().strip()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
            raise forms.ValidationError('Enter a valid IFSC code (e.g., SBIN0001234).')
        return ifsc

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            if _ext(photo.name) not in _ALLOWED_PHOTO_EXT:
                raise forms.ValidationError('Only JPG, JPEG, and PNG images are allowed.')
            if photo.size > _MAX_PHOTO_BYTES:
                raise forms.ValidationError('Profile photo must be under 2 MB.')
        return photo

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1', '')
        p2 = cleaned.get('password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned
