import re
from datetime import date

from django import forms
from django.contrib.auth.models import User

from .models import Car, CarCategory, Profile


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


class CarForm(forms.Form):
    car_name            = forms.CharField(max_length=50)
    brand               = forms.ChoiceField(choices=BRAND_CHOICES, required=False)
    category            = forms.ModelChoiceField(queryset=CarCategory.objects.all(), required=False)
    model               = forms.CharField(max_length=30)
    year                = forms.IntegerField(min_value=2000, max_value=2030)
    fuel                = forms.ChoiceField(choices=Car.FUEL_TYPE)
    transmission        = forms.ChoiceField(choices=Car.TRANSMISSION_TYPE)
    seats               = forms.IntegerField(min_value=1, max_value=12)
    availability        = forms.BooleanField(required=False)
    rent_per_day        = forms.FloatField(min_value=100)
    image               = forms.ImageField(required=False)
    description         = forms.CharField(required=False, widget=forms.Textarea)
    location            = forms.CharField(max_length=100, required=False)
    registration_number = forms.CharField(max_length=20, required=False, label='Registration Number')
    variant             = forms.CharField(max_length=50, required=False, label='Variant')
    weekly_rent         = forms.FloatField(required=False, min_value=0, label='Weekly Rent (₹)')
    monthly_rent        = forms.FloatField(required=False, min_value=0, label='Monthly Rent (₹)')
    available_from      = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Available From')
    available_to        = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Available To')
    rc_book             = forms.FileField(required=False, label='RC Book')
    insurance_doc       = forms.FileField(required=False, label='Insurance Document')
    puc_certificate     = forms.FileField(required=False, label='PUC Certificate')

    self_pickup_available = forms.BooleanField(required=False, label='Self Pickup Available')
    delivery_available    = forms.BooleanField(required=False, label='Home Delivery Available')
    pickup_point_name     = forms.CharField(max_length=200, required=False, label='Pickup Point Name',
                              help_text='Public landmark name shown to customers, e.g. "Technopark Gate 1"')
    pickup_address        = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}), label='Pickup Address (Private — revealed after booking approval)')
    pickup_latitude       = forms.DecimalField(required=False, max_digits=9, decimal_places=6, label='Latitude')
    pickup_longitude      = forms.DecimalField(required=False, max_digits=9, decimal_places=6, label='Longitude')
    delivery_radius       = forms.FloatField(required=False, min_value=0, label='Delivery Radius (km)')
    delivery_charge       = forms.FloatField(required=False, min_value=0, label='Delivery Charge (₹)')


class BrandOption:
    def __init__(self, name):
        self.id   = name
        self.name = name


_ALLOWED_DOC_EXT   = {'jpg', 'jpeg', 'png', 'pdf'}
_ALLOWED_PHOTO_EXT = {'jpg', 'jpeg', 'png'}
_MAX_DOC_BYTES     = 5 * 1024 * 1024   # 5 MB
_MAX_PHOTO_BYTES   = 2 * 1024 * 1024   # 2 MB


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
    first_name             = forms.CharField(max_length=50,  label='First Name')
    last_name              = forms.CharField(max_length=50,  label='Last Name')
    email                  = forms.EmailField(label='Email Address')
    phone                  = forms.CharField(max_length=10,  label='Phone Number')
    password1              = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2              = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    dob                    = forms.DateField(
                               widget=forms.DateInput(attrs={'type': 'date'}),
                               label='Date of Birth',
                             )
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
    first_name             = forms.CharField(max_length=50,  label='First Name')
    last_name              = forms.CharField(max_length=50,  label='Last Name')
    email                  = forms.EmailField(label='Email Address')
    phone                  = forms.CharField(max_length=10,  label='Phone Number')
    password1              = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2              = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    address                = forms.CharField(
                               widget=forms.Textarea(attrs={'rows': 3}),
                               label='Full Address',
                             )
    dob                    = forms.DateField(
                               widget=forms.DateInput(attrs={'type': 'date'}),
                               label='Date of Birth',
                             )
    driving_license_number = forms.CharField(max_length=50, label='Driving Licence Number')
    driving_license_file   = forms.FileField(label='Driving Licence Upload')
    government_id_file     = forms.FileField(label='Government ID (Aadhaar / PAN / Passport)')
    aadhaar_pan            = forms.CharField(max_length=20, required=False,
                               label='Aadhaar / PAN Number (Optional)')
    bank_account_holder    = forms.CharField(max_length=100, label='Account Holder Name')
    bank_account_number    = forms.CharField(max_length=20,  label='Bank Account Number')
    ifsc_code              = forms.CharField(max_length=11,  label='IFSC Code')
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
