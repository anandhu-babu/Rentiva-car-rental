import json
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (AuditLog, Booking, Car, CarCategory, Complaint,
                     Notification, Payment, Profile, Review, UserNotification)


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, 'admin_user', None):
            return redirect('/admin-panel/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _ctx(extra=None):
    base = {'unread_notifications': Notification.objects.filter(is_read=False).count()}
    if extra:
        base.update(extra)
    return base


def _log(request, action, target_type, target_id=None):
    ip_raw = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR', '')
    ip = ip_raw.split(',')[0].strip() or None
    AuditLog.objects.create(
        admin=getattr(request, 'admin_user', None),
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip,
    )


def admin_login(request):
    if request.session.get('admin_user_id'):
        return redirect('/admin-panel/')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember_me', '')

        try:
            user_obj = User.objects.get(email__iexact=email)
            user     = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None and user.is_staff:
            request.session['admin_user_id'] = user.pk
            if not remember:
                request.session.set_expiry(0)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('/admin-panel/')

        messages.error(request, 'Invalid credentials or admin access required.')

    return render(request, 'admin_panel/login.html')


def admin_logout(request):
    request.session.pop('admin_user_id', None)
    return redirect('/admin-panel/login/')


@admin_required
def admin_dashboard(request):
    today = date.today()

    customers_count       = Profile.objects.filter(role='customer').count()
    renters_count         = Profile.objects.filter(role='renter').count()
    vehicles_count        = Car.objects.count()
    active_bookings       = Booking.objects.filter(booking_status__in=['pending', 'approved']).count()
    pending_verifications = (
        Profile.objects.filter(
            verification_status='pending',
            role__in=['customer', 'renter'],
        ).count() +
        Car.objects.filter(verification_status='pending').count()
    )
    today_revenue = (
        Payment.objects.filter(payment_status='paid', payment_date__date=today)
        .aggregate(t=Sum('booking__total_amount'))['t'] or 0
    )
    total_revenue = (
        Booking.objects.filter(booking_status='completed')
        .aggregate(t=Sum('total_amount'))['t'] or 0
    )
    open_complaints = Complaint.objects.filter(status='open').count()

    recent_notifications = Notification.objects.order_by('-created_at')[:8]
    recent_bookings      = Booking.objects.select_related('user', 'car').order_by('-booked_at')[:6]

    months_data = []
    for i in range(5, -1, -1):
        d = (today.replace(day=1) - timedelta(days=i * 30))
        rev = (
            Booking.objects.filter(
                booking_status='completed',
                booked_at__year=d.year,
                booked_at__month=d.month,
            ).aggregate(t=Sum('total_amount'))['t'] or 0
        )
        months_data.append({'month': d.strftime('%b'), 'revenue': float(rev)})

    booking_stats = {
        s: Booking.objects.filter(booking_status=s).count()
        for s in ['pending', 'approved', 'active', 'completed', 'cancelled']
    }

    cats = list(CarCategory.objects.annotate(cnt=Count('car')).order_by('-cnt')[:6])
    if cats and any(c.cnt > 0 for c in cats):
        vehicle_by_category = [{'name': c.name, 'count': c.cnt} for c in cats]
    else:
        vehicle_by_category = [
            {'name': fuel.capitalize(), 'count': Car.objects.filter(fuel=fuel).count()}
            for fuel in ['petrol', 'diesel', 'electric', 'hybrid']
        ]

    payment_stats = {
        s: Payment.objects.filter(payment_status=s).count()
        for s in ['paid', 'pending', 'refunded', 'failed']
    }

    loc_qs = list(
        Booking.objects.filter(pickup_location__isnull=False)
        .values('pickup_location__city')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )
    max_loc = max((l['count'] for l in loc_qs), default=1)
    location_stats = [
        {
            'city':  l['pickup_location__city'],
            'count': l['count'],
            'pct':   int(l['count'] / max_loc * 100),
        }
        for l in loc_qs
    ]

    pending_vehicles  = Car.objects.filter(verification_status='pending').select_related('owner__user')[:5]
    pending_customers = (
        Profile.objects
        .filter(role='customer', verification_status='pending')
        .exclude(user__is_staff=True)
        .select_related('user')[:4]
    )
    pending_renters = (
        Profile.objects
        .filter(role='renter', verification_status='pending')
        .exclude(user__is_staff=True)
        .select_related('user')[:4]
    )
    recent_complaints = (
        Complaint.objects
        .select_related('raised_by', 'booking__car')
        .filter(status__in=['open', 'escalated'])
        .order_by('-created_at')[:5]
    )

    return render(request, 'admin_panel/dashboard.html', _ctx({
        'stats': {
            'customers':             customers_count,
            'renters':               renters_count,
            'vehicles':              vehicles_count,
            'active_bookings':       active_bookings,
            'pending_verifications': pending_verifications,
            'today_revenue':         today_revenue,
            'total_revenue':         total_revenue,
            'open_complaints':       open_complaints,
        },
        'recent_notifications': recent_notifications,
        'recent_bookings':      recent_bookings,
        'months_data':          json.dumps(months_data),
        'booking_stats':        json.dumps(booking_stats),
        'vehicle_by_category':  json.dumps(vehicle_by_category),
        'payment_stats':        json.dumps(payment_stats),
        'location_stats':       location_stats,
        'pending_vehicles':     pending_vehicles,
        'pending_customers':    pending_customers,
        'pending_renters':      pending_renters,
        'recent_complaints':    recent_complaints,
    }))


@admin_required
def admin_customers(request):
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    qs     = User.objects.filter(profile__role='customer').select_related('profile').order_by('-date_joined')
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) |
            Q(email__icontains=search) | Q(profile__phone__icontains=search)
        )
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'suspended':
        qs = qs.filter(is_active=False)
    return render(request, 'admin_panel/users/customers.html', _ctx({
        'customers': qs, 'search': search, 'status_filter': status,
    }))


@admin_required
def admin_renters(request):
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    qs     = User.objects.filter(profile__role='renter').select_related('profile').order_by('-date_joined')
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'suspended':
        qs = qs.filter(is_active=False)
    for renter in qs:
        renter.vehicle_count = Car.objects.filter(owner=renter.profile).count()
    return render(request, 'admin_panel/users/renters.html', _ctx({
        'renters': qs, 'search': search, 'status_filter': status,
    }))


@admin_required
def admin_suspend_user(request, user_id):
    if request.method == 'POST':
        u = get_object_or_404(User, id=user_id)
        u.is_active = False
        u.save()
        _log(request, f'Suspended user: {u.email}', 'User', user_id)
        messages.success(request, f'User {u.email} suspended.')
    return redirect(request.META.get('HTTP_REFERER', '/admin-panel/users/customers/'))


@admin_required
def admin_activate_user(request, user_id):
    if request.method == 'POST':
        u = get_object_or_404(User, id=user_id)
        u.is_active = True
        u.save()
        _log(request, f'Activated user: {u.email}', 'User', user_id)
        messages.success(request, f'User {u.email} activated.')
    return redirect(request.META.get('HTTP_REFERER', '/admin-panel/users/customers/'))


@admin_required
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        u = get_object_or_404(User, id=user_id)
        email = u.email
        u.delete()
        _log(request, f'Deleted user: {email}', 'User', user_id)
        messages.success(request, f'User {email} permanently deleted.')
    return redirect(request.META.get('HTTP_REFERER', '/admin-panel/users/customers/'))


@admin_required
def admin_vehicles(request):
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    qs = Car.objects.select_related('owner__user', 'category').order_by('-created_at')
    if search:
        qs = qs.filter(
            Q(car_name__icontains=search) | Q(brand__icontains=search) |
            Q(owner__user__first_name__icontains=search) | Q(owner__user__email__icontains=search)
        )
    if status:
        qs = qs.filter(verification_status=status)
    return render(request, 'admin_panel/vehicles.html', _ctx({
        'vehicles': qs, 'search': search, 'status_filter': status,
    }))


@admin_required
def admin_approve_vehicle(request, car_id):
    if request.method == 'POST':
        car = get_object_or_404(Car, id=car_id)
        car.verification_status = 'approved'
        car.availability = True
        car.save()
        _log(request, f'Approved vehicle: {car.car_name}', 'Car', car_id)
        messages.success(request, f'Vehicle "{car.car_name}" approved.')
    return redirect('/admin-panel/vehicles/')


@admin_required
def admin_reject_vehicle(request, car_id):
    if request.method == 'POST':
        car = get_object_or_404(Car, id=car_id)
        car.verification_status = 'rejected'
        car.availability = False
        car.save()
        _log(request, f'Rejected vehicle: {car.car_name}', 'Car', car_id)
        messages.success(request, f'Vehicle "{car.car_name}" rejected.')
    return redirect('/admin-panel/vehicles/')


@admin_required
def admin_bookings(request):
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    qs = Booking.objects.select_related('user', 'car', 'pickup_location', 'drop_location').order_by('-booked_at')
    if status:
        qs = qs.filter(booking_status=status)
    if search:
        qs = qs.filter(
            Q(user__email__icontains=search) | Q(user__first_name__icontains=search) |
            Q(car__car_name__icontains=search)
        )
    return render(request, 'admin_panel/bookings.html', _ctx({
        'bookings': qs, 'status_filter': status, 'search': search,
        'status_choices': Booking.STATUS_OPTIONS,
    }))


@admin_required
def admin_cancel_booking(request, booking_id):
    if request.method == 'POST':
        b = get_object_or_404(Booking, id=booking_id)
        b.booking_status = 'cancelled'
        b.save()
        _log(request, f'Admin cancelled booking #{booking_id}', 'Booking', booking_id)
        messages.success(request, f'Booking #{booking_id} cancelled.')
    return redirect('/admin-panel/bookings/')


@admin_required
def admin_complete_booking(request, booking_id):
    if request.method == 'POST':
        b = get_object_or_404(Booking, id=booking_id)
        b.booking_status = 'completed'
        b.save()
        _log(request, f'Admin completed booking #{booking_id}', 'Booking', booking_id)
        messages.success(request, f'Booking #{booking_id} marked as completed.')
    return redirect('/admin-panel/bookings/')


@admin_required
def admin_verify_customers(request):
    status = request.GET.get('status', 'pending')
    qs = (
        Profile.objects
        .filter(role='customer', verification_status=status)
        .exclude(user__is_staff=True)
        .select_related('user')
    )
    return render(request, 'admin_panel/verification/customers.html', _ctx({
        'profiles': qs, 'status_filter': status,
    }))


@admin_required
def admin_approve_customer_kyc(request, profile_id):
    if request.method == 'POST':
        p = get_object_or_404(Profile, id=profile_id, role='customer')
        p.verification_status = 'approved'
        p.save()
        Notification.objects.create(
            notification_type='verification_update',
            title='Customer KYC Approved',
            message=f'{p.user.get_full_name()} ({p.user.email}) KYC approved.',
            related_user=p.user,
        )
        UserNotification.objects.create(
            user=p.user,
            notif_type='kyc_approved',
            title='KYC Verified — Account Activated!',
            message='Your identity documents have been verified. You can now browse and book cars on Rentiva.',
        )
        _log(request, f'Approved customer KYC: {p.user.email}', 'Profile', profile_id)
        messages.success(request, f'KYC approved for {p.user.get_full_name()}.')
    return redirect('/admin-panel/verification/customers/')


@admin_required
def admin_reject_customer_kyc(request, profile_id):
    if request.method == 'POST':
        p = get_object_or_404(Profile, id=profile_id, role='customer')
        p.verification_status = 'rejected'
        p.save()
        UserNotification.objects.create(
            user=p.user,
            notif_type='kyc_rejected',
            title='KYC Verification Rejected',
            message='Your KYC documents could not be verified. Please contact support at rentivacars@gmail.com for assistance.',
        )
        _log(request, f'Rejected customer KYC: {p.user.email}', 'Profile', profile_id)
        messages.success(request, f'KYC rejected for {p.user.get_full_name()}.')
    return redirect('/admin-panel/verification/customers/')


@admin_required
def admin_verify_renters(request):
    status = request.GET.get('status', 'pending')
    qs = (
        Profile.objects
        .filter(role='renter', verification_status=status)
        .exclude(user__is_staff=True)
        .select_related('user')
    )
    return render(request, 'admin_panel/verification/renters.html', _ctx({
        'profiles': qs, 'status_filter': status,
    }))


@admin_required
def admin_approve_renter_kyc(request, profile_id):
    if request.method == 'POST':
        p = get_object_or_404(Profile, id=profile_id, role='renter')
        p.verification_status = 'approved'
        p.save()
        Notification.objects.create(
            notification_type='verification_update',
            title='Renter KYC Approved',
            message=f'{p.user.get_full_name()} ({p.user.email}) renter KYC approved.',
            related_user=p.user,
        )
        UserNotification.objects.create(
            user=p.user,
            notif_type='kyc_approved',
            title='Renter KYC Verified — Start Listing!',
            message='Congratulations! Your renter account is fully verified. You can now list vehicles and start receiving bookings on Rentiva.',
        )
        _log(request, f'Approved renter KYC: {p.user.email}', 'Profile', profile_id)
        messages.success(request, f'Renter KYC approved for {p.user.get_full_name()}.')
    return redirect('/admin-panel/verification/renters/')


@admin_required
def admin_reject_renter_kyc(request, profile_id):
    if request.method == 'POST':
        p = get_object_or_404(Profile, id=profile_id, role='renter')
        p.verification_status = 'rejected'
        p.save()
        UserNotification.objects.create(
            user=p.user,
            notif_type='kyc_rejected',
            title='Renter KYC Rejected',
            message='Your renter KYC documents could not be verified. Please contact support at rentivacars@gmail.com for assistance.',
        )
        _log(request, f'Rejected renter KYC: {p.user.email}', 'Profile', profile_id)
        messages.success(request, f'Renter KYC rejected for {p.user.get_full_name()}.')
    return redirect('/admin-panel/verification/renters/')


@admin_required
def admin_verify_vehicles(request):
    status = request.GET.get('status', 'pending')
    qs = Car.objects.filter(verification_status=status).select_related('owner__user')
    return render(request, 'admin_panel/verification/vehicles.html', _ctx({
        'vehicles': qs, 'status_filter': status,
    }))


@admin_required
def admin_approve_vehicle_docs(request, car_id):
    if request.method == 'POST':
        car = get_object_or_404(Car, id=car_id)
        car.verification_status = 'approved'
        car.availability = True
        car.car_status = 'available'
        car.save()
        UserNotification.objects.create(
            user=car.owner.user,
            notif_type='vehicle_approved',
            title=f'Vehicle Approved — "{car.car_name}" is Now Live!',
            message=f'Your vehicle "{car.car_name}" has been verified and is now visible to customers on Rentiva.',
        )
        _log(request, f'Approved vehicle docs: {car.car_name}', 'Car', car_id)
        messages.success(request, f'Vehicle "{car.car_name}" documents approved.')
    return redirect('/admin-panel/verification/vehicles/')


@admin_required
def admin_reject_vehicle_docs(request, car_id):
    if request.method == 'POST':
        car = get_object_or_404(Car, id=car_id)
        car.verification_status = 'rejected'
        car.availability = False
        car.car_status = 'verification_pending'
        car.save()
        UserNotification.objects.create(
            user=car.owner.user,
            notif_type='vehicle_rejected',
            title=f'Vehicle "{car.car_name}" — Verification Failed',
            message=f'Your vehicle "{car.car_name}" documents could not be verified. Please contact support or re-submit with correct documents.',
        )
        _log(request, f'Rejected vehicle docs: {car.car_name}', 'Car', car_id)
        messages.success(request, f'Vehicle "{car.car_name}" documents rejected.')
    return redirect('/admin-panel/verification/vehicles/')


@admin_required
def admin_payments(request):
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    qs = Payment.objects.select_related('booking__user', 'booking__car').order_by('-payment_date')
    if status:
        qs = qs.filter(payment_status=status)
    if search:
        qs = qs.filter(
            Q(transaction_id__icontains=search) |
            Q(booking__user__email__icontains=search) |
            Q(booking__user__first_name__icontains=search)
        )
    total_paid   = Payment.objects.filter(payment_status='paid').aggregate(t=Sum('booking__total_amount'))['t'] or 0
    total_refund = Payment.objects.filter(payment_status='refunded').aggregate(t=Sum('booking__total_amount'))['t'] or 0
    return render(request, 'admin_panel/payments.html', _ctx({
        'payments': qs, 'status_filter': status, 'search': search,
        'total_paid': total_paid, 'total_refund': total_refund,
    }))


@admin_required
def admin_refund_payment(request, payment_id):
    if request.method == 'POST':
        pmt = get_object_or_404(Payment, id=payment_id)
        pmt.payment_status = 'refunded'
        pmt.refund_status  = True
        pmt.save()
        _log(request, f'Issued refund for payment #{payment_id} (txn: {pmt.transaction_id})', 'Payment', payment_id)
        messages.success(request, f'Refund issued for transaction {pmt.transaction_id}.')
    return redirect('/admin-panel/payments/')


@admin_required
def admin_complaints(request):
    status = request.GET.get('status', '')
    qs = Complaint.objects.select_related('raised_by', 'booking__car').order_by('-created_at')
    if status:
        qs = qs.filter(status=status)
    return render(request, 'admin_panel/complaints.html', _ctx({
        'complaints': qs, 'status_filter': status,
    }))


@admin_required
def admin_resolve_complaint(request, complaint_id):
    if request.method == 'POST':
        c = get_object_or_404(Complaint, id=complaint_id)
        c.status          = 'resolved'
        c.resolved_at     = timezone.now()
        c.resolution_note = request.POST.get('resolution_note', '').strip()
        c.save()
        _log(request, f'Resolved complaint #{complaint_id}', 'Complaint', complaint_id)
        messages.success(request, f'Complaint #{complaint_id} resolved.')
    return redirect('/admin-panel/complaints/')


@admin_required
def admin_reject_complaint(request, complaint_id):
    if request.method == 'POST':
        c = get_object_or_404(Complaint, id=complaint_id)
        c.status      = 'rejected'
        c.resolved_at = timezone.now()
        c.save()
        _log(request, f'Rejected complaint #{complaint_id}', 'Complaint', complaint_id)
        messages.success(request, f'Complaint #{complaint_id} rejected.')
    return redirect('/admin-panel/complaints/')


@admin_required
def admin_escalate_complaint(request, complaint_id):
    if request.method == 'POST':
        c = get_object_or_404(Complaint, id=complaint_id)
        c.status = 'escalated'
        c.save()
        _log(request, f'Escalated complaint #{complaint_id}', 'Complaint', complaint_id)
        messages.success(request, f'Complaint #{complaint_id} escalated.')
    return redirect('/admin-panel/complaints/')


@admin_required
def admin_reviews(request):
    search = request.GET.get('search', '')
    qs = Review.objects.select_related('user', 'car').order_by('-created_at')
    if search:
        qs = qs.filter(
            Q(user__email__icontains=search) | Q(car__car_name__icontains=search) |
            Q(comment__icontains=search)
        )
    avg = Review.objects.aggregate(a=Avg('rating'))['a'] or 0
    return render(request, 'admin_panel/reviews.html', _ctx({
        'reviews': qs, 'search': search, 'platform_avg': round(avg, 1),
    }))


@admin_required
def admin_delete_review(request, review_id):
    if request.method == 'POST':
        rv = get_object_or_404(Review, id=review_id)
        info = f'{rv.user.email} on {rv.car.car_name}'
        rv.delete()
        _log(request, f'Deleted review: {info}', 'Review', review_id)
        messages.success(request, 'Review removed from platform.')
    return redirect('/admin-panel/reviews/')


@admin_required
def admin_reports(request):
    today = date.today()

    monthly_labels, monthly_revenue = [], []
    for i in range(11, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 30)
        rev = (
            Booking.objects.filter(
                booking_status='completed',
                booked_at__year=d.year, booked_at__month=d.month,
            ).aggregate(t=Sum('total_amount'))['t'] or 0
        )
        monthly_labels.append(d.strftime('%b %Y'))
        monthly_revenue.append(float(rev))

    top_cars = (
        Car.objects.annotate(booking_count=Count('booking'))
        .order_by('-booking_count')[:5]
    )

    booking_stats = {
        s: Booking.objects.filter(booking_status=s).count()
        for s in ['pending', 'approved', 'completed', 'cancelled']
    }

    verification_stats = {
        'cust_pending':  Profile.objects.filter(role='customer', verification_status='pending').count(),
        'cust_approved': Profile.objects.filter(role='customer', verification_status='approved').count(),
        'rent_pending':  Profile.objects.filter(role='renter',   verification_status='pending').count(),
        'rent_approved': Profile.objects.filter(role='renter',   verification_status='approved').count(),
        'veh_pending':   Car.objects.filter(verification_status='pending').count(),
        'veh_approved':  Car.objects.filter(verification_status='approved').count(),
    }

    complaint_stats = {
        s: Complaint.objects.filter(status=s).count()
        for s in ['open', 'resolved', 'rejected', 'escalated']
    }

    return render(request, 'admin_panel/reports.html', _ctx({
        'monthly_labels':     json.dumps(monthly_labels),
        'monthly_revenue':    json.dumps(monthly_revenue),
        'top_cars':           top_cars,
        'booking_stats':      json.dumps(booking_stats),
        'verification_stats': verification_stats,
        'complaint_stats':    json.dumps(complaint_stats),
    }))


@admin_required
def admin_notifications(request):
    notifications = Notification.objects.order_by('-created_at')
    Notification.objects.filter(is_read=False).update(is_read=True)
    return render(request, 'admin_panel/notifications.html', _ctx({
        'notifications': notifications,
    }))


@admin_required
def admin_settings(request):
    audit_logs = AuditLog.objects.select_related('admin').order_by('-timestamp')[:100]
    return render(request, 'admin_panel/settings.html', _ctx({
        'audit_logs': audit_logs,
    }))
