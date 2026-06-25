import json
import os
from datetime import date, timedelta
from html import escape as _esc

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Sum, Q
from django.http import JsonResponse
from django.utils import timezone
from huggingface_hub import InferenceClient
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (Profile, Car, CarCategory, Booking, Location, Review,
                     Notification, UserNotification)
from .forms import (CarForm, BrandOption, BRAND_CHOICES,
                    CustomerRegistrationForm, RenterRegistrationForm)
from .serializers import CarSerializer, BookingSerializer, ReviewSerializer, LocationSerializer


def _brand_list():
    return [BrandOption(name) for val, name in BRAND_CHOICES if val]


def _brand_list_from_db():
    names = (
        Car.objects.exclude(brand='').exclude(brand=None)
        .values_list('brand', flat=True)
        .distinct()
        .order_by('brand')
    )
    return [BrandOption(n) for n in names]


def _resolve_plan(plan_key, car):
    if plan_key == 'weekly' and car.weekly_rent:
        return 'weekly', car.weekly_rent, 'Weekly'
    if plan_key == 'monthly' and car.monthly_rent:
        return 'monthly', car.monthly_rent, 'Monthly'
    return 'daily', car.rent_per_day, 'Daily'


def home(request):
    cars = Car.objects.filter(availability=True, verification_status='approved').order_by('-created_at')[:4]
    return render(request, 'home.html', {'cars': cars})


def register(request):
    return render(request, 'register.html')


def customer_register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            user = User.objects.create_user(
                username=d['email'].lower(),
                email=d['email'].lower(),
                password=d['password1'],
                first_name=d['first_name'].strip(),
                last_name=d['last_name'].strip(),
            )
            Profile.objects.create(
                user=user,
                role='customer',
                phone=d['phone'],
                dob=d['dob'],
                driving_license_number=d['driving_license_number'].strip(),
                driving_license_file=d['driving_license_file'],
                government_id_file=d['government_id_file'],
                verification_status='pending',
            )
            Notification.objects.create(
                notification_type='new_customer',
                title='New Customer Registration',
                message=f'{d["first_name"].strip()} {d["last_name"].strip()} ({d["email"].lower()}) has registered as a customer and submitted KYC documents for verification.',
                related_user=user,
            )
            messages.success(
                request,
                'Registration successful! Your account is pending admin verification. '
                'You will be able to book cars once your KYC is approved.'
            )
            return redirect('/login/')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'registration/customer_register.html', {'form': form})


def renter_register(request):
    if request.method == 'POST':
        form = RenterRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            user = User.objects.create_user(
                username=d['email'].lower(),
                email=d['email'].lower(),
                password=d['password1'],
                first_name=d['first_name'].strip(),
                last_name=d['last_name'].strip(),
            )
            Profile.objects.create(
                user=user,
                role='renter',
                is_renter=True,
                phone=d['phone'],
                address=d['address'].strip(),
                dob=d['dob'],
                driving_license_number=d['driving_license_number'].strip(),
                driving_license_file=d['driving_license_file'],
                government_id_file=d['government_id_file'],
                aadhaar_pan=d.get('aadhaar_pan', '').strip(),
                bank_account_holder=d['bank_account_holder'].strip(),
                bank_account_number=d['bank_account_number'].strip(),
                ifsc_code=d['ifsc_code'],
                profile=d['profile_photo'],
                verification_status='pending',
            )
            Notification.objects.create(
                notification_type='new_renter',
                title='New Renter Registration',
                message=f'{d["first_name"].strip()} {d["last_name"].strip()} ({d["email"].lower()}) has registered as a renter and submitted KYC documents for verification.',
                related_user=user,
            )
            messages.success(
                request,
                'Registration successful! Your renter account is pending admin verification. '
                'You will be able to list vehicles once your KYC is approved.'
            )
            return redirect('/login/')
    else:
        form = RenterRegistrationForm()
    return render(request, 'registration/renter_register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        email    = request.POST['email'].strip().lower()
        password = request.POST['password']

        user = auth.authenticate(username=email, password=password)

        if user is None:
            try:
                lookup = User.objects.get(email__iexact=email)
                user   = auth.authenticate(username=lookup.username, password=password)
            except User.DoesNotExist:
                pass

        if user is not None:
            if user.is_staff:
                messages.error(request, 'Admin accounts must sign in via the Admin Panel.')
                return redirect('/login/')
            auth.login(request, user)
            try:
                p = user.profile
                if p.verification_status == 'pending':
                    messages.info(
                        request,
                        'Your account is pending KYC verification. '
                        'You can browse cars but booking is restricted until approved.'
                    )
                elif p.verification_status == 'rejected':
                    messages.warning(
                        request,
                        'Your KYC verification was rejected. Please contact support.'
                    )
                if p.role == 'renter' or p.is_renter:
                    return redirect('/dashboard/renter/')
            except Exception:
                pass
            return redirect('/dashboard/customer/')

        messages.error(request, 'Invalid email or password.')
        return redirect('/login/')
    return render(request, 'login.html')


def logout_view(request):
    messages.get_messages(request).used = True
    auth.logout(request)
    return redirect('/')


def car_list(request):
    cars = Car.objects.filter(availability=True, verification_status='approved')

    search       = request.GET.get('search')
    brand        = request.GET.get('brand')
    fuel         = request.GET.get('fuel')
    transmission = request.GET.get('transmission')
    max_price    = request.GET.get('max_price')
    location     = request.GET.get('location')

    if search:
        cars = cars.filter(
            Q(car_name__icontains=search) |
            Q(brand__icontains=search)
        )
    if brand:
        cars = cars.filter(brand__iexact=brand)
    if fuel:
        cars = cars.filter(fuel=fuel)
    if transmission:
        cars = cars.filter(transmission=transmission)
    if max_price:
        cars = cars.filter(rent_per_day__lte=max_price)
    if location:
        cars = cars.filter(location__icontains=location)

    return render(request, 'cars/car_list.html', {
        'cars': cars,
        'brands': _brand_list_from_db(),
        'fuel_choices': Car.FUEL_TYPE,
        'transmission_choices': Car.TRANSMISSION_TYPE,
        'filters': {
            'search': search or '',
            'brand': brand or '',
            'fuel': fuel or '',
            'transmission': transmission or '',
            'max_price': max_price or '10000',
            'location': location or '',
        }
    })


def car_details(request, car_id):
    car          = get_object_or_404(Car, id=car_id)
    reviews      = Review.objects.filter(car=car).order_by('-created_at')
    other_cars   = Car.objects.filter(availability=True, verification_status='approved').exclude(id=car_id)[:4]
    avg_rating   = reviews.aggregate(avg=Avg('rating'))['avg']
    review_count = reviews.count()

    daily   = car.rent_per_day or 0
    weekly  = car.weekly_rent  or round(daily * 0.84)
    monthly = car.monthly_rent or round(daily * 0.54)

    return render(request, 'cars/car_details.html', {
        'car': car,
        'reviews': reviews,
        'other_cars': other_cars,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'price_daily':   int(daily),
        'price_weekly':  int(weekly),
        'price_monthly': int(monthly),
    })


@login_required
def customer_dashboard(request):
    bookings      = Booking.objects.filter(user=request.user).order_by('-booked_at')
    unread_count  = UserNotification.objects.filter(user=request.user, is_read=False).count()
    notifications = UserNotification.objects.filter(user=request.user)[:10]
    return render(request, 'dashboard/user_dashboard.html', {
        'bookings': bookings,
        'today': date.today(),
        'unread_count': unread_count,
        'notifications': notifications,
    })


@login_required
def renter_dashboard(request):
    if not (request.user.profile.role == 'renter' or request.user.profile.is_renter):
        return redirect('/dashboard/customer/')

    profile = request.user.profile
    cars    = Car.objects.filter(owner=profile)
    car_ids = cars.values_list('id', flat=True)

    recent_bookings = Booking.objects.filter(car__in=car_ids).order_by('-booked_at')[:20]

    pending_confirmations = Booking.objects.filter(
        car__in=car_ids,
        booking_status='awaiting_renter_confirmation',
    ).select_related('user', 'car').order_by('renter_confirmation_deadline')

    total_revenue = (
        Booking.objects.filter(car__in=car_ids, booking_status='completed')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )
    active_bookings = Booking.objects.filter(
        car__in=car_ids,
        booking_status__in=('awaiting_renter_confirmation', 'confirmed', 'pending', 'approved')
    ).count()

    for car in cars:
        car.booking_count = Booking.objects.filter(car=car).count()

    unread_count  = UserNotification.objects.filter(user=request.user, is_read=False).count()
    notifications = UserNotification.objects.filter(user=request.user)[:10]

    return render(request, 'dashboard/renter_dashboard.html', {
        'cars': cars,
        'stats': {
            'total_cars': cars.count(),
            'active_bookings': active_bookings,
            'total_revenue': total_revenue,
        },
        'recent_bookings': recent_bookings,
        'pending_confirmations': pending_confirmations,
        'unread_count': unread_count,
        'notifications': notifications,
    })


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if request.method == 'POST':
        cancellable = ('pending', 'approved', 'awaiting_renter_confirmation', 'confirmed')
        if booking.pickup_date > date.today() and booking.booking_status in cancellable:
            booking.booking_status = 'cancelled'
            booking.save()

            if booking.car.car_status == 'booked':
                booking.car.car_status = 'available'
                booking.car.availability = True
                booking.car.save()

            try:
                renter_user = booking.car.owner.user
                UserNotification.objects.create(
                    user=renter_user,
                    notif_type='booking_cancelled',
                    title='Booking Cancelled',
                    message=f'{request.user.get_full_name()} has cancelled the booking for {booking.car.car_name} (#{booking.id}).',
                    related_booking=booking,
                )
            except Exception:
                pass

            messages.success(request, 'Booking cancelled successfully.')
        else:
            messages.error(request, 'This booking cannot be cancelled.')
    return redirect('/dashboard/customer/')


@login_required
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user.profile)
    booking.booking_status = 'approved'
    booking.save()
    messages.success(request, 'Booking approved successfully.')
    return redirect('/dashboard/renter/')


@login_required
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user.profile)
    booking.booking_status = 'cancelled'
    booking.save()
    messages.success(request, 'Booking rejected.')
    return redirect('/dashboard/renter/')


@login_required
def complete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user.profile)
    booking.booking_status = 'completed'
    booking.save()

    booking.car.car_status = 'available'
    booking.car.availability = True
    booking.car.save()

    UserNotification.objects.create(
        user=booking.user,
        notif_type='booking_completed',
        title='Booking Completed',
        message=f'Your rental of {booking.car.car_name} has been marked as completed. Thank you for choosing Rentiva!',
        related_booking=booking,
    )

    messages.success(request, 'Booking marked as completed.')
    return redirect('/dashboard/renter/')


@login_required
def renter_confirm_booking(request, booking_id):
    """Renter accepts or rejects a booking awaiting confirmation."""
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        car__owner=request.user.profile,
        booking_status='awaiting_renter_confirmation',
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'confirm':
            booking.booking_status = 'confirmed'
            instructions = request.POST.get('pickup_instructions', '').strip()
            if instructions:
                booking.pickup_instructions = instructions
            booking.save()

            booking.car.car_status = 'booked'
            booking.car.availability = False
            booking.car.save()

            UserNotification.objects.create(
                user=booking.user,
                notif_type='booking_confirmed',
                title='Booking Confirmed!',
                message=(
                    f'Great news! Your booking for {booking.car.car_name} '
                    f'from {booking.pickup_date.strftime("%d %b %Y")} to '
                    f'{booking.return_date.strftime("%d %b %Y")} has been confirmed. '
                    f'Total: ₹{booking.total_amount:,.0f}.'
                ),
                related_booking=booking,
            )
            messages.success(request, f'Booking #{booking.id} confirmed.')

        elif action == 'reject':
            booking.booking_status = 'rejected'
            booking.save()

            UserNotification.objects.create(
                user=booking.user,
                notif_type='booking_rejected',
                title='Booking Rejected',
                message=(
                    f'Your booking for {booking.car.car_name} was not confirmed by the renter. '
                    f'Your advance payment of ₹{booking.advance_amount:,.0f} will be refunded '
                    f'within 5–7 business days.'
                ),
                related_booking=booking,
            )
            messages.success(request, f'Booking #{booking.id} rejected. Customer has been notified.')

        return redirect('/dashboard/renter/')

    return render(request, 'bookings/renter_confirm.html', {'booking': booking})


@login_required
def add_car(request):
    profile = request.user.profile

    if not (profile.role == 'renter' or profile.is_renter):
        messages.error(request, 'Only renters can list vehicles.')
        return redirect('/dashboard/customer/')

    if not request.user.is_staff and profile.verification_status != 'approved':
        messages.warning(
            request,
            'Your KYC is pending admin verification. '
            'You can list a vehicle once your account is approved.'
        )
        return redirect('/dashboard/renter/')

    categories = CarCategory.objects.all()
    brands     = _brand_list()
    locations  = Location.objects.all()

    if request.method == 'POST':
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            car = Car(
                owner=profile,
                car_name=d['car_name'],
                brand=d.get('brand', ''),
                category=d.get('category'),
                model=d['model'],
                year=d['year'],
                fuel=d['fuel'],
                transmission=d['transmission'],
                seats=d['seats'],
                availability=False,
                rent_per_day=d['rent_per_day'],
                description=d.get('description', ''),
                location=d.get('location', ''),
                registration_number=d.get('registration_number', ''),
                variant=d.get('variant', ''),
                weekly_rent=d.get('weekly_rent'),
                monthly_rent=d.get('monthly_rent'),
                available_from=d.get('available_from'),
                available_to=d.get('available_to'),
                car_status='verification_pending',
                verification_status='pending',
                self_pickup_available=d.get('self_pickup_available', False),
                delivery_available=d.get('delivery_available', False),
                pickup_point_name=d.get('pickup_point_name', ''),
                pickup_address=d.get('pickup_address', ''),
                pickup_latitude=d.get('pickup_latitude'),
                pickup_longitude=d.get('pickup_longitude'),
                delivery_radius=d.get('delivery_radius'),
                delivery_charge=d.get('delivery_charge'),
            )
            if d.get('image'):
                car.image = d['image']
            if d.get('rc_book'):
                car.rc_book = d['rc_book']
            if d.get('insurance_doc'):
                car.insurance_doc = d['insurance_doc']
            if d.get('puc_certificate'):
                car.puc_certificate = d['puc_certificate']
            car.save()

            Notification.objects.create(
                notification_type='vehicle_pending',
                title='New Vehicle Awaiting Verification',
                message=f'{profile.user.get_full_name()} has listed "{car.car_name}" and it is awaiting document verification.',
                related_user=profile.user,
            )

            messages.success(
                request,
                f'"{car.car_name}" submitted for verification! '
                f'It will appear in listings once admin approves it.'
            )
            return redirect('/dashboard/renter/')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = CarForm()

    return render(request, 'cars/add_car.html', {
        'form': form,
        'categories': categories,
        'brands': brands,
        'locations': locations,
    })


@login_required
def edit_car(request, car_id):
    profile    = request.user.profile
    car        = get_object_or_404(Car, id=car_id, owner=profile)
    categories = CarCategory.objects.all()
    brands     = _brand_list()

    if request.method == 'POST':
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            car.car_name              = d['car_name']
            car.brand                 = d.get('brand', car.brand)
            car.model                 = d['model']
            car.year                  = d['year']
            car.fuel                  = d['fuel']
            car.transmission          = d['transmission']
            car.seats                 = d['seats']
            car.availability          = d.get('availability', False)
            car.rent_per_day          = d['rent_per_day']
            car.description           = d.get('description', '')
            car.location              = d.get('location', '')
            car.registration_number   = d.get('registration_number', car.registration_number)
            car.variant               = d.get('variant', car.variant)
            car.weekly_rent           = d.get('weekly_rent') or car.weekly_rent
            car.monthly_rent          = d.get('monthly_rent') or car.monthly_rent
            car.available_from        = d.get('available_from') or car.available_from
            car.available_to          = d.get('available_to') or car.available_to
            car.self_pickup_available = d.get('self_pickup_available', False)
            car.delivery_available    = d.get('delivery_available', False)
            car.pickup_point_name     = d.get('pickup_point_name', car.pickup_point_name)
            car.pickup_address        = d.get('pickup_address', car.pickup_address)
            car.pickup_latitude       = d.get('pickup_latitude') or car.pickup_latitude
            car.pickup_longitude      = d.get('pickup_longitude') or car.pickup_longitude
            car.delivery_radius       = d.get('delivery_radius') or car.delivery_radius
            car.delivery_charge       = d.get('delivery_charge') or car.delivery_charge
            if d.get('category'):
                car.category = d['category']
            if d.get('image'):
                car.image = d['image']
            if d.get('rc_book'):
                car.rc_book = d['rc_book']
            if d.get('insurance_doc'):
                car.insurance_doc = d['insurance_doc']
            if d.get('puc_certificate'):
                car.puc_certificate = d['puc_certificate']
            car.save()
            messages.success(request, f'"{car.car_name}" updated successfully!')
            return redirect('/dashboard/renter/')
        messages.error(request, 'Please fix the errors below.')
    else:
        initial = {
            'car_name':               car.car_name,
            'brand':                  car.brand,
            'category':               car.category,
            'model':                  car.model,
            'year':                   car.year,
            'fuel':                   car.fuel,
            'transmission':           car.transmission,
            'seats':                  car.seats,
            'availability':           car.availability,
            'rent_per_day':           car.rent_per_day,
            'description':            car.description,
            'location':               car.location,
            'registration_number':    car.registration_number,
            'variant':                car.variant,
            'weekly_rent':            car.weekly_rent,
            'monthly_rent':           car.monthly_rent,
            'available_from':         car.available_from,
            'available_to':           car.available_to,
            'self_pickup_available':  car.self_pickup_available,
            'delivery_available':     car.delivery_available,
            'pickup_point_name':      car.pickup_point_name,
            'pickup_address':         car.pickup_address,
            'pickup_latitude':        car.pickup_latitude,
            'pickup_longitude':       car.pickup_longitude,
            'delivery_radius':        car.delivery_radius,
            'delivery_charge':        car.delivery_charge,
        }
        form = CarForm(initial=initial)

    return render(request, 'cars/edit_car.html', {
        'form': form,
        'car': car,
        'categories': categories,
        'brands': brands,
    })


@login_required
def delete_car(request, car_id):
    profile = request.user.profile
    car     = get_object_or_404(Car, id=car_id, owner=profile)
    if request.method == 'POST':
        name = car.car_name
        car.delete()
        messages.success(request, f'"{name}" has been deleted.')
    return redirect('/dashboard/renter/')


@login_required
def booking(request, car_id):
    car = get_object_or_404(Car, id=car_id, availability=True, verification_status='approved')

    try:
        profile = request.user.profile
        if not request.user.is_staff and profile.verification_status != 'approved':
            messages.warning(
                request,
                'Your account must be KYC-verified before you can make bookings. '
                'Please wait for admin approval.'
            )
            return redirect('/dashboard/customer/')
    except Profile.DoesNotExist:
        if request.user.is_staff:
            return redirect('/admin-panel/')
        messages.error(request, 'Please complete your profile first.')
        return redirect('/dashboard/customer/')

    if request.method == 'POST':
        delivery_method  = request.POST.get('delivery_method', 'self_pickup')
        delivery_address = request.POST.get('delivery_address', '').strip()
        pickup_date_str  = request.POST.get('pickup_date')
        return_date_str  = request.POST.get('return_date')
        plan_key         = request.POST.get('plan', 'daily')

        plan, price_per_day, plan_label = _resolve_plan(plan_key, car)
        ctx = {'car': car, 'plan': plan, 'price_per_day': price_per_day, 'plan_label': plan_label}

        if delivery_method == 'self_pickup' and not car.self_pickup_available:
            messages.error(request, 'Self pickup is not available for this vehicle.')
            return render(request, 'bookings/booking.html', ctx)
        if delivery_method == 'home_delivery' and not car.delivery_available:
            messages.error(request, 'Home delivery is not available for this vehicle.')
            return render(request, 'bookings/booking.html', ctx)
        if delivery_method == 'home_delivery' and not delivery_address:
            messages.error(request, 'Please enter your delivery address.')
            return render(request, 'bookings/booking.html', ctx)

        if not all([pickup_date_str, return_date_str]):
            messages.error(request, 'Please select pickup and return dates.')
            return render(request, 'bookings/booking.html', ctx)

        try:
            pickup_date = date.fromisoformat(pickup_date_str)
            return_date = date.fromisoformat(return_date_str)
        except ValueError:
            messages.error(request, 'Invalid dates provided.')
            return render(request, 'bookings/booking.html', ctx)

        if pickup_date < date.today():
            messages.error(request, 'Pickup date cannot be in the past.')
            return render(request, 'bookings/booking.html', ctx)

        if return_date <= pickup_date:
            messages.error(request, 'Return date must be after pickup date.')
            return render(request, 'bookings/booking.html', ctx)

        overlapping = Booking.objects.filter(
            car=car,
            booking_status__in=('awaiting_renter_confirmation', 'confirmed', 'pending', 'approved', 'active'),
            pickup_date__lt=return_date,
            return_date__gt=pickup_date,
        ).exists()

        if overlapping:
            messages.error(request, 'This car is already booked for the selected dates. Please choose different dates.')
            return render(request, 'bookings/booking.html', ctx)

        days         = (return_date - pickup_date).days
        base_amount  = days * price_per_day
        delivery_fee = (car.delivery_charge or 0) if delivery_method == 'home_delivery' else 0
        total_amount     = base_amount + delivery_fee
        advance_amount   = round(total_amount * 0.30, 2)
        remaining_amount = round(total_amount - advance_amount, 2)

        new_booking = Booking.objects.create(
            user=request.user,
            car=car,
            pickup_date=pickup_date,
            return_date=return_date,
            total_amount=total_amount,
            advance_amount=advance_amount,
            remaining_amount=remaining_amount,
            booking_status='awaiting_renter_confirmation',
            renter_confirmation_deadline=timezone.now() + timedelta(hours=24),
            delivery_method=delivery_method,
            delivery_address=delivery_address if delivery_method == 'home_delivery' else '',
            rental_plan=plan,
        )

        method_label = 'Self Pickup' if delivery_method == 'self_pickup' else 'Home Delivery'

        UserNotification.objects.create(
            user=request.user,
            notif_type='booking_submitted',
            title='Booking Request Sent',
            message=(
                f'Your booking request for {car.car_name} ({days} day{"s" if days > 1 else ""}, '
                f'{plan_label} plan, {method_label}) has been sent to the renter. '
                f'Advance paid: ₹{advance_amount:,.0f}. '
                f'You will be notified once the renter confirms (within 24 hours).'
            ),
            related_booking=new_booking,
        )

        try:
            UserNotification.objects.create(
                user=car.owner.user,
                notif_type='booking_request',
                title='New Booking Request',
                message=(
                    f'{request.user.get_full_name() or request.user.username} has requested to book '
                    f'{car.car_name} from {pickup_date.strftime("%d %b %Y")} to '
                    f'{return_date.strftime("%d %b %Y")} via {method_label}. '
                    f'Please confirm or reject within 24 hours.'
                ),
                related_booking=new_booking,
            )
        except Exception:
            pass

        Notification.objects.create(
            notification_type='general',
            title='New Booking Created',
            message=(
                f'Booking #{new_booking.id} for {car.car_name} by '
                f'{request.user.get_full_name() or request.user.username} ({method_label}).'
            ),
            related_user=request.user,
        )

        return redirect(f'/booking/confirmation/{new_booking.id}/')

    plan_key = request.GET.get('plan', 'daily')
    plan, price_per_day, plan_label = _resolve_plan(plan_key, car)
    return render(request, 'bookings/booking.html', {
        'car': car,
        'plan': plan,
        'price_per_day': price_per_day,
        'plan_label': plan_label,
    })


@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'bookings/booking_confirmation.html', {'booking': booking})


@login_required
def payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'bookings/payment.html', {'booking': booking})


@login_required
def remove_profile_photo(request):
    if request.method == 'POST':
        profile = request.user.profile
        if profile.profile:
            storage, path = profile.profile.storage, profile.profile.name
            profile.profile = None
            profile.save()
            if storage.exists(path):
                storage.delete(path)
            messages.success(request, 'Profile photo removed.')
    return redirect('/edit-profile/')


@login_required
def edit_profile(request):
    profile = request.user.profile

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name).strip()
        request.user.last_name  = request.POST.get('last_name',  request.user.last_name).strip()
        request.user.save()

        profile.location  = request.POST.get('location',  '').strip()
        profile.languages = request.POST.get('languages', '').strip()
        profile.work      = request.POST.get('work',      '').strip()
        profile.school    = request.POST.get('school',    '').strip()
        profile.about     = request.POST.get('about',     '').strip()
        profile.phone     = request.POST.get('phone',     profile.phone).strip()

        if request.FILES.get('profile_photo'):
            profile.profile = request.FILES['profile_photo']

        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('/dashboard/customer/')

    return render(request, 'dashboard/edit_dashboard.html')


client = InferenceClient(api_key=os.getenv("HF_TOKEN"))


def ask_ai(question):
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Rentiva AI Assistant.\n\n"
                        "You help users with:\n"
                        "* Car rentals\n"
                        "* Vehicle recommendations\n"
                        "* Car comparisons\n"
                        "* Travel suggestions\n"
                        "* Booking guidance\n\n"
                        "Keep answers short and helpful."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception:
        return "Sorry, I'm unable to answer right now."


def chatbot_query(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'})

    try:
        data = json.loads(request.body)
        msg  = data.get('message', '').strip()
        msg_lower = msg.lower()
    except Exception:
        return JsonResponse({'reply': 'Invalid request.'})

    if not msg:
        return JsonResponse({'reply': 'Please type a message.'})

    if any(word in msg_lower for word in ['hello', 'hi', 'hey']):
        return JsonResponse({
            'reply': (
                '<strong>Welcome to Rentiva</strong><br><br>'
                'I can help you with:<ul>'
                '<li>Luxury Cars</li>'
                '<li>SUV Cars</li>'
                '<li>Budget Cars</li>'
                '<li>Available Cars</li>'
                '<li>Booking Help</li>'
                '<li>My Bookings</li>'
                '<li>Support</li>'
                '</ul>'
            )
        })

    elif any(word in msg_lower for word in ['luxury', 'bmw', 'audi', 'premium']):
        cars  = Car.objects.filter(availability=True, verification_status='approved', rent_per_day__gte=5000)[:5]
        reply = "<strong>Luxury Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a> - ₹{car.rent_per_day}/day<br>'
        return JsonResponse({'reply': reply})

    elif any(word in msg_lower for word in ['suv', 'family car', '7 seater']):
        cars  = Car.objects.filter(availability=True, verification_status='approved', seats__gte=6)[:5]
        reply = "<strong>SUV & Family Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a><br>'
        return JsonResponse({'reply': reply})

    elif any(word in msg_lower for word in ['budget', 'cheap', 'affordable', 'under 2000']):
        cars  = Car.objects.filter(availability=True, verification_status='approved', rent_per_day__lte=2000).order_by('rent_per_day')[:5]
        reply = "<strong>Budget Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a> - ₹{car.rent_per_day}/day<br>'
        return JsonResponse({'reply': reply})

    elif any(word in msg_lower for word in ['available', 'show cars', 'find cars', 'available cars']):
        cars  = Car.objects.filter(availability=True, verification_status='approved').order_by('-created_at')[:5]
        reply = "<strong>Available Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a><br>'
        return JsonResponse({'reply': reply})

    elif any(word in msg_lower for word in ['booking', 'book car', 'rent car', 'booking help']):
        return JsonResponse({
            'reply': (
                '<strong>Booking Process</strong><br><br>'
                '1. Get KYC verified (admin approval)<br>'
                '2. Browse Cars<br>'
                '3. Open Car Details<br>'
                '4. Click Rent Now<br>'
                '5. Select Dates & Pay 30% Advance<br>'
                '6. Renter Confirms within 24 hours'
            )
        })

    elif any(word in msg_lower for word in ['my booking', 'my bookings', 'booking status']):
        if not request.user.is_authenticated:
            return JsonResponse({'reply': 'Please login to view your bookings.'})
        bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')[:5]
        if not bookings.exists():
            return JsonResponse({'reply': 'No bookings found.'})
        reply = "<strong>Your Bookings</strong><br><br>"
        for b in bookings:
            reply += f'• {_esc(b.car.car_name)} ({b.get_booking_status_display()})<br>'
        return JsonResponse({'reply': reply})

    elif any(word in msg_lower for word in ['renter', 'list car', 'earn', 'become renter']):
        return JsonResponse({
            'reply': (
                '<strong>Become a Renter</strong><br><br>'
                '1. Register as a Renter<br>'
                '2. Submit KYC documents<br>'
                '3. Wait for admin approval<br>'
                '4. List your vehicles<br>'
                '5. Start receiving bookings'
            )
        })

    elif any(word in msg_lower for word in ['support', 'contact', 'help']):
        return JsonResponse({
            'reply': (
                '<strong>Support</strong><br><br>'
                'Email: rentivacars@gmail.com<br>'
                'Phone: +91 9876543210'
            )
        })

    else:
        ai_reply = ask_ai(msg)
        return JsonResponse({'reply': f'<strong>Rentiva AI</strong><br><br>{ai_reply}'})


@api_view(['GET'])
def api_car_list(request):
    cars = Car.objects.filter(availability=True, verification_status='approved').order_by('-created_at')
    return Response(CarSerializer(cars, many=True).data)


@api_view(['GET'])
def api_car_details(request, car_id):
    car     = get_object_or_404(Car, id=car_id)
    reviews = Review.objects.filter(car=car).order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    return Response({
        'car': CarSerializer(car).data,
        'reviews': ReviewSerializer(reviews, many=True).data,
        'avg_rating': avg_rating,
        'review_count': reviews.count(),
    })


@api_view(['GET'])
def api_search_cars(request):
    cars = Car.objects.filter(availability=True, verification_status='approved')

    search       = request.GET.get('search')
    brand        = request.GET.get('brand')
    fuel         = request.GET.get('fuel')
    transmission = request.GET.get('transmission')
    max_price    = request.GET.get('max_price')
    location     = request.GET.get('location')

    if search:
        cars = cars.filter(Q(car_name__icontains=search) | Q(brand__icontains=search))
    if brand:
        cars = cars.filter(brand__iexact=brand)
    if fuel:
        cars = cars.filter(fuel=fuel)
    if transmission:
        cars = cars.filter(transmission=transmission)
    if max_price:
        cars = cars.filter(rent_per_day__lte=max_price)
    if location:
        cars = cars.filter(location__icontains=location)

    return Response(CarSerializer(cars, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_add_car(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return Response({'error': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = CarSerializer(data=request.data)
    if serializer.is_valid():
        car = serializer.save(owner=profile)
        return Response(CarSerializer(car).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def api_booking(request, car_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)

    car = get_object_or_404(Car, id=car_id, availability=True, verification_status='approved')

    if request.method == 'GET':
        locations = Location.objects.all()
        return Response({
            'car': CarSerializer(car).data,
            'locations': LocationSerializer(locations, many=True).data,
        })

    pickup_location_id = request.data.get('pickup_location')
    drop_location_id   = request.data.get('drop_location')
    pickup_date_str    = request.data.get('pickup_date')
    return_date_str    = request.data.get('return_date')

    if not all([pickup_location_id, drop_location_id, pickup_date_str, return_date_str]):
        return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pickup_date = date.fromisoformat(pickup_date_str)
        return_date = date.fromisoformat(return_date_str)
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    if pickup_date < date.today():
        return Response({'error': 'Pickup date cannot be in the past.'}, status=status.HTTP_400_BAD_REQUEST)

    if return_date <= pickup_date:
        return Response({'error': 'Return date must be after pickup date.'}, status=status.HTTP_400_BAD_REQUEST)

    overlapping = Booking.objects.filter(
        car=car,
        booking_status__in=('awaiting_renter_confirmation', 'confirmed', 'pending', 'approved', 'active'),
        pickup_date__lt=return_date,
        return_date__gt=pickup_date,
    ).exists()

    if overlapping:
        return Response({'error': 'Car already booked for these dates.'}, status=status.HTTP_400_BAD_REQUEST)

    days             = (return_date - pickup_date).days
    total_amount     = days * car.rent_per_day
    advance_amount   = round(total_amount * 0.30, 2)
    remaining_amount = round(total_amount - advance_amount, 2)

    pickup_location = get_object_or_404(Location, id=pickup_location_id)
    drop_location   = get_object_or_404(Location, id=drop_location_id)

    new_booking = Booking.objects.create(
        user=request.user,
        car=car,
        pickup_location=pickup_location,
        drop_location=drop_location,
        pickup_date=pickup_date,
        return_date=return_date,
        total_amount=total_amount,
        advance_amount=advance_amount,
        remaining_amount=remaining_amount,
        booking_status='awaiting_renter_confirmation',
        renter_confirmation_deadline=timezone.now() + timedelta(hours=24),
    )

    return Response({
        'message': f'Booking created for {days} day(s)! Total: ₹{total_amount:,.0f}. Awaiting renter confirmation.',
        'booking': BookingSerializer(new_booking).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def api_my_bookings(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)
    bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')
    return Response(BookingSerializer(bookings, many=True).data)
