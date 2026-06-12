from django.db import models
from django.contrib.auth.models import User
    
class CarCategory(models.Model):
    name    = models.CharField(max_length=20)

    def __str__(self):
        return self.name
    
class Profile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True, blank=True)
    phone = models.CharField(max_length=10)
    address = models.TextField(null=True, blank=True)
    profile = models.ImageField(upload_to='profile/',null=True, blank=True)
    is_renter = models.BooleanField(default=False)
    location = models.CharField(max_length=100, null=True, blank=True)
    languages = models.CharField(max_length=200,null=True,blank=True)
    work = models.CharField(max_length=100, null=True,blank=True)
    school = models.CharField(max_length=100,null=True,blank=True)
    about = models.TextField(null=True,blank=True)

    def __str__(self):
        return self.user.username

class Car(models.Model):

    FUEL_TYPE = (
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    )

    TRANSMISSION_TYPE = (
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    )

    owner    = models.ForeignKey(Profile,on_delete=models.CASCADE)
    brand = models.CharField(max_length=100, null=True, blank=True)
    category = models.ForeignKey(CarCategory,on_delete=models.CASCADE,null=True,blank=True)
    car_name = models.CharField(max_length=50,null=True,blank=True)
    model = models.CharField(max_length=30)
    year    = models.IntegerField()
    fuel    = models.CharField(max_length=20, choices=FUEL_TYPE)
    transmission = models.CharField(max_length=50,choices=TRANSMISSION_TYPE)
    seats        = models.IntegerField()
    location     = models.CharField(max_length=100, null=True, blank=True)
    availability = models.BooleanField(default=True)
    rent_per_day = models.FloatField()
    image        = models.ImageField(upload_to='cars/', null=True, blank=True)
    description  = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.car_name

class Location(models.Model):
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=40)
    pincode = models.IntegerField(null=True,blank=True)

    def __str__(self):
        return self.city

class Booking(models.Model):

    STATUS_OPTIONS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE)
    car	= models.ForeignKey('Car',on_delete=models.CASCADE)
    pickup_location	= models.ForeignKey(Location, on_delete=models.CASCADE, related_name='pickup_location')
    drop_location	= models.ForeignKey(Location, on_delete=models.CASCADE, related_name='drop_location')
    pickup_date	= models.DateField()
    return_date	= models.DateField()
    total_amount = models.FloatField()
    booking_status	= models.CharField(max_length=30,choices=STATUS_OPTIONS,default='pending')
    booked_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    
    PAYMENT_OPTIONS = (
        ('upi', 'UPT'),
        ('card', 'Card'),
        ('cash', 'Cash'),
    )

    PAYMENT_STATUS = (
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
)
 
    booking	= models.OneToOneField(Booking,on_delete=models.CASCADE)
    payment_method	= models.CharField(max_length=50,choices= PAYMENT_OPTIONS)
    transaction_id	= models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20,choices=PAYMENT_STATUS,default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)

class Review(models.Model):

    user = models.ForeignKey(User,on_delete=models.CASCADE)
    car	= models.ForeignKey(Car,on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    comment	= models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ChatBotQuery(models.Model):

    user = models.ForeignKey(User,on_delete=models.CASCADE)
    query	= models.TextField()
    response	= models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)