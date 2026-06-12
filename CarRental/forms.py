from django import forms
from .models import Car, CarCategory


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
    car_name     = forms.CharField(max_length=50)
    brand        = forms.ChoiceField(choices=BRAND_CHOICES, required=False)
    category     = forms.ModelChoiceField(queryset=CarCategory.objects.all(), required=False)
    model        = forms.CharField(max_length=30)
    year         = forms.IntegerField(min_value=2000, max_value=2030)
    fuel         = forms.ChoiceField(choices=Car.FUEL_TYPE)
    transmission = forms.ChoiceField(choices=Car.TRANSMISSION_TYPE)
    seats        = forms.IntegerField(min_value=1, max_value=12)
    availability = forms.BooleanField(required=False)
    rent_per_day = forms.FloatField(min_value=100)
    image        = forms.ImageField(required=False)
    description  = forms.CharField(required=False, widget=forms.Textarea)
    location     = forms.CharField(max_length=100, required=False)

class BrandOption:
    def __init__(self, name):
        self.id   = name
        self.name = name
