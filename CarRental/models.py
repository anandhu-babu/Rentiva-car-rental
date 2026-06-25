from django.db import models
from django.contrib.auth.models import User


class CarCategory(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


ROLE_CHOICES = (
    ('customer', 'Customer'),
    ('renter',   'Renter'),
)

VERIFICATION_STATUS = (
    ('pending',  'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)


class Profile(models.Model):

    user      = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone     = models.CharField(max_length=10)
    address   = models.TextField(null=True, blank=True)
    profile   = models.ImageField(upload_to='profile/', null=True, blank=True)
    is_renter = models.BooleanField(default=False)
    location  = models.CharField(max_length=100, null=True, blank=True)
    languages = models.CharField(max_length=200, null=True, blank=True)
    work      = models.CharField(max_length=100, null=True, blank=True)
    school    = models.CharField(max_length=100, null=True, blank=True)
    about     = models.TextField(null=True, blank=True)

    dob                    = models.DateField(null=True, blank=True)
    driving_license_number = models.CharField(max_length=50, null=True, blank=True)
    driving_license_file   = models.FileField(upload_to='licenses/', null=True, blank=True)

    government_id_file = models.FileField(upload_to='govt_ids/', null=True, blank=True)

    aadhaar_pan         = models.CharField(max_length=20,  null=True, blank=True)
    bank_account_holder = models.CharField(max_length=100, null=True, blank=True)
    bank_account_number = models.CharField(max_length=20,  null=True, blank=True)
    ifsc_code           = models.CharField(max_length=11,  null=True, blank=True)

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default='pending'
    )

    def save(self, *args, **kwargs):
        if self.is_renter and self.role == 'customer':
            self.role = 'renter'
        if self.role == 'renter':
            self.is_renter = True
        # Staff accounts are auto-approved so they don't appear in the KYC queue
        if self.user_id and self.user.is_staff:
            self.verification_status = 'approved'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username


class Car(models.Model):

    FUEL_TYPE = (
        ('petrol',   'Petrol'),
        ('diesel',   'Diesel'),
        ('electric', 'Electric'),
        ('hybrid',   'Hybrid'),
    )

    TRANSMISSION_TYPE = (
        ('manual',    'Manual'),
        ('automatic', 'Automatic'),
    )

    CAR_STATUS_CHOICES = (
        ('available',            'Available'),
        ('booked',               'Currently Booked'),
        ('maintenance',          'Under Maintenance'),
        ('verification_pending', 'Pending Verification'),
    )

    owner        = models.ForeignKey(Profile, on_delete=models.CASCADE)
    brand        = models.CharField(max_length=100, null=True, blank=True)
    category     = models.ForeignKey(CarCategory, on_delete=models.CASCADE, null=True, blank=True)
    car_name     = models.CharField(max_length=50, null=True, blank=True)
    model        = models.CharField(max_length=30)
    year         = models.IntegerField()
    fuel         = models.CharField(max_length=20, choices=FUEL_TYPE)
    transmission = models.CharField(max_length=50, choices=TRANSMISSION_TYPE)
    seats        = models.IntegerField()
    location     = models.CharField(max_length=100, null=True, blank=True)
    availability = models.BooleanField(default=True)
    rent_per_day = models.FloatField()
    image        = models.ImageField(upload_to='cars/', null=True, blank=True)
    description  = models.TextField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    registration_number = models.CharField(max_length=20, null=True, blank=True)
    variant             = models.CharField(max_length=50, null=True, blank=True)
    weekly_rent         = models.FloatField(null=True, blank=True)
    monthly_rent        = models.FloatField(null=True, blank=True)
    available_from      = models.DateField(null=True, blank=True)
    available_to        = models.DateField(null=True, blank=True)
    car_status          = models.CharField(
        max_length=30, choices=CAR_STATUS_CHOICES, default='verification_pending'
    )

    rc_book          = models.FileField(upload_to='vehicles/rc/',        null=True, blank=True)
    insurance_doc    = models.FileField(upload_to='vehicles/insurance/', null=True, blank=True)
    puc_certificate  = models.FileField(upload_to='vehicles/puc/',       null=True, blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default='pending'
    )

    self_pickup_available = models.BooleanField(default=True)
    delivery_available    = models.BooleanField(default=False)
    pickup_point_name     = models.CharField(max_length=200, null=True, blank=True,
                               help_text='Public landmark name, e.g. "Technopark Gate 1"')
    pickup_address        = models.TextField(null=True, blank=True)
    pickup_latitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_radius       = models.FloatField(null=True, blank=True, help_text='Delivery radius in km')
    delivery_charge       = models.FloatField(null=True, blank=True, help_text='Delivery charge in ₹')

    def __str__(self):
        return self.car_name or ''


class CarImage(models.Model):
    car        = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='cars/gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Image for {self.car}'


class Location(models.Model):
    city    = models.CharField(max_length=40)
    state   = models.CharField(max_length=40)
    pincode = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.city


class Booking(models.Model):

    STATUS_OPTIONS = (
        ('pending',                      'Pending'),
        ('approved',                     'Approved'),
        ('active',                       'Active'),
        ('advance_paid',                 'Advance Paid'),
        ('awaiting_renter_confirmation', 'Awaiting Renter Confirmation'),
        ('confirmed',                    'Confirmed'),
        ('rejected',                     'Rejected by Renter'),
        ('cancelled',                    'Cancelled'),
        ('completed',                    'Completed'),
        ('refunded',                     'Refunded'),
    )

    DELIVERY_METHOD = (
        ('self_pickup',   'Self Pickup'),
        ('home_delivery', 'Home Delivery'),
    )

    RENTAL_PLAN = (
        ('daily',   'Daily'),
        ('weekly',  'Weekly'),
        ('monthly', 'Monthly'),
    )

    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    car             = models.ForeignKey('Car', on_delete=models.CASCADE)
    pickup_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='pickup_location')
    drop_location   = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='drop_location')
    pickup_date     = models.DateField()
    return_date     = models.DateField()
    total_amount    = models.FloatField()
    advance_amount  = models.FloatField(default=0)
    remaining_amount = models.FloatField(default=0)
    booking_status  = models.CharField(max_length=40, choices=STATUS_OPTIONS, default='pending')
    booked_at       = models.DateTimeField(auto_now_add=True)
    renter_confirmation_deadline = models.DateTimeField(null=True, blank=True)
    delivery_method      = models.CharField(max_length=20, choices=DELIVERY_METHOD, default='self_pickup')
    delivery_address     = models.TextField(null=True, blank=True)
    pickup_instructions  = models.TextField(null=True, blank=True)
    rental_plan          = models.CharField(max_length=10, choices=RENTAL_PLAN, default='daily')


class Payment(models.Model):

    PAYMENT_OPTIONS = (
        ('upi',  'UPI'),
        ('card', 'Card'),
        ('cash', 'Cash'),
    )

    PAYMENT_STATUS = (
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    )

    booking        = models.OneToOneField(Booking, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_OPTIONS)
    transaction_id = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_date   = models.DateTimeField(auto_now_add=True)
    refund_status  = models.BooleanField(default=False)


class Review(models.Model):

    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    car        = models.ForeignKey(Car, on_delete=models.CASCADE)
    rating     = models.IntegerField(default=5)
    comment    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ChatBotQuery(models.Model):

    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    query      = models.TextField()
    response   = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Complaint(models.Model):

    COMPLAINT_TYPES = (
        ('vehicle_damage',      'Vehicle Damaged'),
        ('late_return',         'Late Return'),
        ('payment_issue',       'Payment Issue'),
        ('customer_misconduct', 'Customer Misconduct'),
        ('renter_misconduct',   'Renter Misconduct'),
        ('other',               'Other'),
    )

    STATUS_CHOICES = (
        ('open',      'Open'),
        ('resolved',  'Resolved'),
        ('rejected',  'Rejected'),
        ('escalated', 'Escalated'),
    )

    booking         = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    raised_by       = models.ForeignKey(User, on_delete=models.CASCADE)
    complaint_type  = models.CharField(max_length=30, choices=COMPLAINT_TYPES, default='other')
    description     = models.TextField()
    image           = models.ImageField(upload_to='complaints/', null=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at      = models.DateTimeField(auto_now_add=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'Complaint #{self.id} — {self.get_complaint_type_display()}'


class Notification(models.Model):

    NOTIFICATION_TYPES = (
        ('new_customer',        'New Customer Registered'),
        ('new_renter',          'New Renter Registered'),
        ('vehicle_pending',     'Vehicle Waiting Approval'),
        ('booking_cancelled',   'Booking Cancelled'),
        ('complaint_raised',    'Complaint Raised'),
        ('payment_failed',      'Payment Failed'),
        ('verification_update', 'Verification Update'),
        ('general',             'General'),
    )

    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='general')
    title        = models.CharField(max_length=200)
    message      = models.TextField()
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title


class UserNotification(models.Model):
    """Per-user notifications for customers and renters."""

    NOTIF_TYPES = (
        ('booking_submitted',  'Booking Submitted'),
        ('booking_confirmed',  'Booking Confirmed'),
        ('booking_rejected',   'Booking Rejected'),
        ('booking_cancelled',  'Booking Cancelled'),
        ('booking_completed',  'Booking Completed'),
        ('refund_issued',      'Refund Issued'),
        ('booking_request',    'New Booking Request'),
        ('vehicle_approved',   'Vehicle Approved'),
        ('vehicle_rejected',   'Vehicle Rejected'),
        ('kyc_approved',       'KYC Approved'),
        ('kyc_rejected',       'KYC Rejected'),
        ('general',            'General'),
    )

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    notif_type      = models.CharField(max_length=30, choices=NOTIF_TYPES, default='general')
    title           = models.CharField(max_length=200)
    message         = models.TextField()
    is_read         = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    related_booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.title}'


class AuditLog(models.Model):

    admin       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action      = models.CharField(max_length=255)
    target_type = models.CharField(max_length=50)
    target_id   = models.IntegerField(null=True, blank=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.admin} — {self.action}'
