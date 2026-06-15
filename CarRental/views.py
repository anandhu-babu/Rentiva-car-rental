import json
from datetime import date
from html import escape as _esc

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Sum, Q
from django.http import JsonResponse
from huggingface_hub import InferenceClient

from .models import Profile, Car, CarCategory, Booking, Location, Review
from .forms import CarForm, BrandOption, BRAND_CHOICES

def _brand_list():
    """Return BrandOption list from BRAND_CHOICES (excluding the blank entry)."""
    return [BrandOption(name) for val, name in BRAND_CHOICES if val]


def _brand_list_from_db():
    """Return BrandOption list built from distinct brand values already in the DB."""
    names = (
        Car.objects.exclude(brand='').exclude(brand=None)
        .values_list('brand', flat=True)
        .distinct()
        .order_by('brand')
    )
    return [BrandOption(n) for n in names]


def homefn(request):
    cars = Car.objects.filter(availability=True).order_by('-created_at')[:4]
    return render(request, 'home.html', {'cars': cars})

def registerfn(request):
    if request.method == 'POST':
        fname = request.POST['first_name']
        lname = request.POST['last_name']
        em    = request.POST['email']
        pass1 = request.POST['password1']
        pass2 = request.POST['password2']
        phn   = request.POST['phone']

        if pass1 != pass2:
            messages.error(request, 'Passwords do not match.')
            return redirect('/register/')

        if User.objects.filter(email=em).exists():
            messages.error(request, 'Email already registered.')
            return redirect('/register/')

        if Profile.objects.filter(phone=phn).exists():
            messages.error(request, 'Phone number already registered.')
            return redirect('/register/')

        user = User.objects.create_user(
            username=em, email=em, password=pass1,
            first_name=fname, last_name=lname,
        )
        Profile.objects.create(user=user, phone=phn)
        messages.success(request, 'Account created! Please log in.')
        return redirect('/login/')

    return render(request, 'register.html')


def loginfn(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(username=email,password=password)

        if user:
            auth.login(request, user)
            if user.profile.is_renter:
                return redirect('/dashboard/renter/')
            return redirect('/dashboard/customer/')

        messages.error(request, 'Invalid email or password.')
        return redirect('/login/')
    return render(request, 'login.html')


def logoutfn(request):
    messages.get_messages(request).used = True
    auth.logout(request)
    return redirect('/')


def carListfn(request):
    cars = Car.objects.filter(availability=True)

    search = request.GET.get('search')
    brand = request.GET.get('brand')
    fuel = request.GET.get('fuel')
    transmission = request.GET.get('transmission')
    max_price = request.GET.get('max_price')
    location = request.GET.get('location')

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


def carDetailsfn(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    reviews = Review.objects.filter(car=car).order_by('-created_at')
    other_cars  = Car.objects.filter(availability=True).exclude(id=car_id)[:4]
    avg_rating  = reviews.aggregate(avg=Avg('rating'))['avg']
    review_count = reviews.count()

    context = {
        'car': car,
        'reviews': reviews,
        'other_cars': other_cars,
        'avg_rating': avg_rating,
        'review_count': review_count,
    }
    return render(request, 'cars/car_details.html', context)

#Dashboard

@login_required
def becomeRenterfn(request):
    return redirect('/add-car/')

@login_required
def customerDashboardfn(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')
    return render(request, 'dashboard/user_dashboard.html', {
        'bookings': bookings,
        'today': date.today(),
    })


@login_required
def cancelBookingfn(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if request.method == 'POST':
        if booking.pickup_date > date.today() and booking.booking_status in ('pending', 'approved'):
            booking.booking_status = 'cancelled'
            booking.save()
            messages.success(request, 'Booking cancelled successfully.')
        else:
            messages.error(request, 'This booking cannot be cancelled.')
    return redirect('/dashboard/customer/')

@login_required
def approveBookingfn(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user.profile)
    booking.booking_status = 'approved'
    booking.save()

    messages.success(request, 'Booking approved successfully.')
    return redirect('/dashboard/renter/')


@login_required
def rejectBookingfn(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user.profile)
    booking.booking_status = 'cancelled'
    booking.save()

    messages.success(request, 'Booking rejected.')
    return redirect('/dashboard/renter/')


@login_required
def completeBookingfn(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user.profile)
    booking.booking_status = 'completed'
    booking.save()

    messages.success(request, 'Booking marked as completed.')
    return redirect('/dashboard/renter/')

@login_required
def renterDashboardfn(request):

    if not request.user.profile.is_renter:
        return redirect('/dashboard/customer/')

    profile = request.user.profile
    cars = Car.objects.filter(owner=profile)
    car_ids = cars.values_list('id', flat=True)
    recent_bookings = Booking.objects.filter(car__in=car_ids).order_by('-booked_at')[:20]
    total_revenue = (Booking.objects.filter(car__in=car_ids,booking_status='completed').aggregate(total=Sum('total_amount'))['total'] or 0 )

    active_bookings = Booking.objects.filter(car__in=car_ids,booking_status__in=('pending', 'approved')).count()

    for car in cars:
        car.booking_count = Booking.objects.filter(car=car).count()

    return render(request,'dashboard/renter_dashboard.html',{
            'cars': cars,
            'stats': {
                'total_cars': cars.count(),
                'active_bookings': active_bookings,
                'total_revenue': total_revenue,
            },
            'recent_bookings': recent_bookings,
        }
    )

#CRUD Operations

@login_required
def addCarfn(request):

    categories = CarCategory.objects.all()
    brands = _brand_list()
    locations = Location.objects.all()

    if request.method == 'POST':
        form = CarForm(request.POST,request.FILES)

        if form.is_valid():
            d = form.cleaned_data
            car = Car(
                owner=request.user.profile,
                car_name=d['car_name'],
                brand=d.get('brand', ''),
                category=d.get('category'),
                model=d['model'],
                year=d['year'],
                fuel=d['fuel'],
                transmission=d['transmission'],
                seats=d['seats'],
                availability=d.get('availability', True),
                rent_per_day=d['rent_per_day'],
                description=d.get('description', ''),
                location=d.get('location', ''),
            )

            if d.get('image'):
                car.image = d['image']
            car.save()

            profile = request.user.profile
            if not profile.is_renter:
                profile.is_renter = True
                profile.save()

            messages.success(request,f'"{car.car_name}" listed successfully!')
            return redirect('/dashboard/renter/')
        messages.error(request,'Please fix the errors below.')

    else:
        form = CarForm()
    return render(request,'cars/add_car.html',{
            'form': form,
            'categories': categories,
            'brands': brands,
            'locations': locations,
        }
    )

@login_required
def editCarfn(request, car_id):
    profile = request.user.profile
    car     = get_object_or_404(Car, id=car_id, owner=profile)
    categories = CarCategory.objects.all()
    brands     = _brand_list()

    if request.method == 'POST':
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            car.car_name     = d['car_name']
            car.brand        = d.get('brand', car.brand)
            car.model        = d['model']
            car.year         = d['year']
            car.fuel         = d['fuel']
            car.transmission = d['transmission']
            car.seats        = d['seats']
            car.availability = d.get('availability', False)
            car.rent_per_day = d['rent_per_day']
            car.description  = d.get('description', '')
            car.location     = d.get('location', '')
            if d.get('category'):
                car.category = d['category']
            if d.get('image'):
                car.image = d['image']
            car.save()
            messages.success(request, f'"{car.car_name}" updated successfully!')
            return redirect('/dashboard/renter/')

        messages.error(request, 'Please fix the errors below.')
    else:

        initial = {
            'car_name':     car.car_name,
            'brand':        car.brand,
            'category':     car.category,
            'model':        car.model,
            'year':         car.year,
            'fuel':         car.fuel,
            'transmission': car.transmission,
            'seats':        car.seats,
            'availability': car.availability,
            'rent_per_day': car.rent_per_day,
            'description':  car.description,
            'location':     car.location,
        }
        form = CarForm(initial=initial)

    return render(request, 'cars/edit_car.html', {
        'form': form,
        'car': car,
        'categories': categories,
        'brands': brands,
    })


@login_required
def deleteCarfn(request, car_id):
    profile = request.user.profile
    car     = get_object_or_404(Car, id=car_id, owner=profile)
    if request.method == 'POST':
        name = car.car_name
        car.delete()
        messages.success(request, f'"{name}" has been deleted.')
    return redirect('/dashboard/renter/')

@login_required
def bookingfn(request, car_id):
    car = get_object_or_404(Car, id=car_id,availability=True)
    locations = Location.objects.all()

    if request.method == 'POST':
        pickup_location_id = request.POST.get('pickup_location')
        drop_location_id   = request.POST.get('drop_location')
        pickup_date_str    = request.POST.get('pickup_date')
        return_date_str    = request.POST.get('return_date')

        if not all([pickup_location_id, drop_location_id, pickup_date_str, return_date_str]):
            messages.error(request, 'All fields are required.')
            return render(request, 'bookings/booking.html', {'car': car, 'locations': locations})

        try:
            pickup_date = date.fromisoformat(pickup_date_str)
            return_date = date.fromisoformat(return_date_str)
        except ValueError:
            messages.error(request, 'Invalid dates provided.')
            return render(request, 'bookings/booking.html', {'car': car, 'locations': locations})

        if pickup_date < date.today():
            messages.error(request, 'Pickup date cannot be in the past.')
            return render(request, 'bookings/booking.html', {'car': car, 'locations': locations})

        if return_date <= pickup_date:
            messages.error(request, 'Return date must be after pickup date.')
            return render(request, 'bookings/booking.html', {'car': car, 'locations': locations})

        overlapping = Booking.objects.filter(
            car=car,
            booking_status__in=('pending', 'approved'),
            pickup_date__lt=return_date,
            return_date__gt=pickup_date,
        ).exists()

        if overlapping:
            messages.error(request, 'This car is already booked for the selected dates. Please choose different dates.')
            return render(request, 'bookings/booking.html', {'car': car, 'locations': locations})

        days         = (return_date - pickup_date).days
        total_amount = days * car.rent_per_day

        pickup_location = get_object_or_404(Location, id=pickup_location_id)
        drop_location   = get_object_or_404(Location, id=drop_location_id)

        Booking.objects.create(
            user            = request.user,
            car             = car,
            pickup_location = pickup_location,
            drop_location   = drop_location,
            pickup_date     = pickup_date,
            return_date     = return_date,
            total_amount    = total_amount,
            booking_status  = 'pending',
        )

        messages.success(request, f'Booking confirmed for {days} day(s)! Total: ₹{total_amount:,.0f}. The renter will approve shortly.')
        return redirect('/dashboard/customer/')

    return render(request, 'bookings/booking.html', {'car': car, 'locations': locations})


def paymentfn(request):
    return render(request, 'bookings/payment.html')


@login_required
def removeProfilePhotofn(request):
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
def editDashboardfn(request):
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

import os
client = InferenceClient(api_key=os.getenv("HF_TOKEN"))

#AI Integration
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
        msg = data.get('message', '').strip()
        msg_lower = msg.lower()
    except Exception:
        return JsonResponse({'reply': 'Invalid request.'})

    if not msg:
        return JsonResponse({'reply': 'Please type a message.'})

    # Greetings
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
                '<li>Become a Renter</li>'
                '<li>Support</li>'
                '</ul>'
            )
        })

    # Luxury Cars
    elif any(word in msg_lower for word in ['luxury', 'bmw', 'audi', 'premium']):
        cars = Car.objects.filter(availability=True, rent_per_day__gte=5000)[:5]
        reply = "<strong>Luxury Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a> - ₹{car.rent_per_day}/day<br>'
        return JsonResponse({'reply': reply})

    # SUVs
    elif any(word in msg_lower for word in ['suv', 'family car', '7 seater']):
        cars = Car.objects.filter(availability=True, seats__gte=6)[:5]
        reply = "<strong>SUV & Family Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a><br>'
        return JsonResponse({'reply': reply})

    # Budget Cars
    elif any(word in msg_lower for word in ['budget', 'cheap', 'affordable', 'under 2000']):
        cars = Car.objects.filter(availability=True, rent_per_day__lte=2000).order_by('rent_per_day')[:5]
        reply = "<strong>Budget Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a> - ₹{car.rent_per_day}/day<br>'
        return JsonResponse({'reply': reply})

    # Available Cars
    elif any(word in msg_lower for word in ['available', 'show cars', 'find cars', 'available cars']):
        cars = Car.objects.filter(availability=True).order_by('-created_at')[:5]
        reply = "<strong>Available Cars</strong><br><br>"
        for car in cars:
            reply += f'• <a href="/cars/{car.id}/">{_esc(car.car_name)}</a><br>'
        return JsonResponse({'reply': reply})

    # Booking Help
    elif any(word in msg_lower for word in ['booking', 'book car', 'rent car', 'booking help']):
        return JsonResponse({
            'reply': (
                '<strong>Booking Process</strong><br><br>'
                '1. Browse Cars<br>'
                '2. Open Car Details<br>'
                '3. Click Rent Now<br>'
                '4. Select Pickup & Return Dates<br>'
                '5. Confirm Booking'
            )
        })

    # My Bookings
    elif any(word in msg_lower for word in ['my booking', 'my bookings', 'booking status']):
        if not request.user.is_authenticated:
            return JsonResponse({'reply': 'Please login to view your bookings.'})
        bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')[:5]
        if not bookings.exists():
            return JsonResponse({'reply': 'No bookings found.'})
        reply = "<strong>Your Bookings</strong><br><br>"
        for booking in bookings:
            reply += f'• {_esc(booking.car.car_name)} ({booking.booking_status.title()})<br>'
        return JsonResponse({'reply': reply})

    # Become Renter
    elif any(word in msg_lower for word in ['renter', 'list car', 'earn', 'become renter']):
        return JsonResponse({
            'reply': (
                '<strong>Become a Renter</strong><br><br>'
                '1. Login<br>'
                '2. Open Dashboard<br>'
                '3. Add Your Car<br>'
                '4. Start Receiving Bookings'
            )
        })

    # Support
    elif any(word in msg_lower for word in ['support', 'contact', 'help']):
        return JsonResponse({
            'reply': (
                '<strong>Support</strong><br><br>'
                'Email: rentivacars@gmail.com<br>'
                'Phone: +91 9876543210'
            )
        })

    # AI Fallback
    else:
        ai_reply = ask_ai(msg)
        return JsonResponse({
            'reply': f'<strong>Rentiva AI</strong><br><br>{ai_reply}'
        })

# REST API views 

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import CarSerializer, BookingSerializer, ReviewSerializer, LocationSerializer


@api_view(['GET'])
def apiCarListfn(request):
    cars = Car.objects.filter(availability=True).order_by('-created_at')
    serializer = CarSerializer(cars, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def apiCarDetailsfn(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    reviews = Review.objects.filter(car=car).order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']

    return Response({
        'car': CarSerializer(car).data,
        'reviews': ReviewSerializer(reviews, many=True).data,
        'avg_rating': avg_rating,
        'review_count': reviews.count(),
    })


@api_view(['GET'])
def apiSearchCarfn(request):
    cars = Car.objects.filter(availability=True)

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

    serializer = CarSerializer(cars, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apiAddCarfn(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return Response({'error': 'User profile not found. Please complete your profile first.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = CarSerializer(data=request.data)
    if serializer.is_valid():
        car = serializer.save(owner=profile)
        if not profile.is_renter:
            profile.is_renter = True
            profile.save()
        return Response(CarSerializer(car).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def apiBookingfn(request, car_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)

    car = get_object_or_404(Car, id=car_id, availability=True)

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
        booking_status__in=('pending', 'approved'),
        pickup_date__lt=return_date,
        return_date__gt=pickup_date,
    ).exists()

    if overlapping:
        return Response({'error': 'Car already booked for these dates.'}, status=status.HTTP_400_BAD_REQUEST)

    days         = (return_date - pickup_date).days
    total_amount = days * car.rent_per_day

    pickup_location = get_object_or_404(Location, id=pickup_location_id)
    drop_location   = get_object_or_404(Location, id=drop_location_id)

    booking = Booking.objects.create(
        user            = request.user,
        car             = car,
        pickup_location = pickup_location,
        drop_location   = drop_location,
        pickup_date     = pickup_date,
        return_date     = return_date,
        total_amount    = total_amount,
        booking_status  = 'pending',
    )

    return Response({
        'message': f'Booking confirmed for {days} day(s)! Total: ₹{total_amount:,.0f}',
        'booking': BookingSerializer(booking).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def apiMyBookingsfn(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)

    bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')
    serializer = BookingSerializer(bookings, many=True)
    return Response(serializer.data)
