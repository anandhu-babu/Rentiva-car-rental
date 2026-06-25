from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from CarRental.views import (
    home, register, customer_register, renter_register,
    login_view, logout_view,
    customer_dashboard, renter_dashboard, edit_profile, remove_profile_photo,
    car_list, car_details,
    add_car, edit_car, delete_car,
    booking, booking_confirmation, cancel_booking,
    approve_booking, reject_booking, complete_booking,
    renter_confirm_booking,
    payment,
    chatbot_query,
    api_car_list, api_car_details, api_search_cars,
    api_add_car, api_booking, api_my_bookings,
)
from CarRental.admin_views import (
    admin_login, admin_logout,
    admin_dashboard,
    admin_customers, admin_renters,
    admin_suspend_user, admin_activate_user, admin_delete_user,
    admin_vehicles, admin_approve_vehicle, admin_reject_vehicle,
    admin_bookings, admin_cancel_booking, admin_complete_booking,
    admin_verify_customers, admin_approve_customer_kyc, admin_reject_customer_kyc,
    admin_verify_renters, admin_approve_renter_kyc, admin_reject_renter_kyc,
    admin_verify_vehicles, admin_approve_vehicle_docs, admin_reject_vehicle_docs,
    admin_payments, admin_refund_payment,
    admin_complaints, admin_resolve_complaint, admin_reject_complaint, admin_escalate_complaint,
    admin_reviews, admin_delete_review,
    admin_reports,
    admin_notifications,
    admin_settings,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public pages
    path('', home),
    path('register/', register),
    path('register/customer/', customer_register),
    path('register/renter/', renter_register),
    path('login/', login_view),
    path('logout/', logout_view),

    # Dashboards & profile
    path('dashboard/customer/', customer_dashboard),
    path('dashboard/renter/', renter_dashboard),
    path('profile/', edit_profile),
    path('edit-profile/', edit_profile),
    path('remove-profile-photo/', remove_profile_photo),

    # Car listings
    path('cars/', car_list),
    path('car/list/', car_list),
    path('cars/<int:car_id>/', car_details),

    # Car management (renter only)
    path('add-car/', add_car),
    path('my-cars/edit/<int:car_id>/', edit_car),
    path('my-cars/delete/<int:car_id>/', delete_car),

    # Booking flow
    path('booking/<int:car_id>/', booking),
    path('booking/confirmation/<int:booking_id>/', booking_confirmation),
    path('booking/cancel/<int:booking_id>/', cancel_booking),
    path('booking/<int:booking_id>/approve/', approve_booking),
    path('booking/<int:booking_id>/reject/', reject_booking),
    path('booking/<int:booking_id>/complete/', complete_booking),
    path('booking/<int:booking_id>/renter-action/', renter_confirm_booking),
    path('payment/<int:booking_id>/', payment),

    # Chatbot
    path('chatbot/query/', chatbot_query),

    # REST API
    path('api/cars/', api_car_list),
    path('api/cars/<int:car_id>/', api_car_details),
    path('api/cars/search/', api_search_cars),
    path('api/cars/add/', api_add_car),
    path('api/booking/<int:car_id>/', api_booking),
    path('api/my-bookings/', api_my_bookings),

    # Admin panel
    path('admin-panel/login/', admin_login),
    path('admin-panel/logout/', admin_logout),
    path('admin-panel/', admin_dashboard),

    path('admin-panel/users/customers/', admin_customers),
    path('admin-panel/users/renters/', admin_renters),
    path('admin-panel/users/<int:user_id>/suspend/',  admin_suspend_user),
    path('admin-panel/users/<int:user_id>/activate/', admin_activate_user),
    path('admin-panel/users/<int:user_id>/delete/',   admin_delete_user),

    path('admin-panel/vehicles/', admin_vehicles),
    path('admin-panel/vehicles/<int:car_id>/approve/', admin_approve_vehicle),
    path('admin-panel/vehicles/<int:car_id>/reject/',  admin_reject_vehicle),

    path('admin-panel/bookings/', admin_bookings),
    path('admin-panel/bookings/<int:booking_id>/cancel/',   admin_cancel_booking),
    path('admin-panel/bookings/<int:booking_id>/complete/', admin_complete_booking),

    path('admin-panel/verification/customers/', admin_verify_customers),
    path('admin-panel/verification/customers/<int:profile_id>/approve/', admin_approve_customer_kyc),
    path('admin-panel/verification/customers/<int:profile_id>/reject/',  admin_reject_customer_kyc),
    path('admin-panel/verification/renters/', admin_verify_renters),
    path('admin-panel/verification/renters/<int:profile_id>/approve/', admin_approve_renter_kyc),
    path('admin-panel/verification/renters/<int:profile_id>/reject/',  admin_reject_renter_kyc),
    path('admin-panel/verification/vehicles/', admin_verify_vehicles),
    path('admin-panel/verification/vehicles/<int:car_id>/approve/', admin_approve_vehicle_docs),
    path('admin-panel/verification/vehicles/<int:car_id>/reject/',  admin_reject_vehicle_docs),

    path('admin-panel/payments/', admin_payments),
    path('admin-panel/payments/<int:payment_id>/refund/', admin_refund_payment),

    path('admin-panel/complaints/', admin_complaints),
    path('admin-panel/complaints/<int:complaint_id>/resolve/',  admin_resolve_complaint),
    path('admin-panel/complaints/<int:complaint_id>/reject/',   admin_reject_complaint),
    path('admin-panel/complaints/<int:complaint_id>/escalate/', admin_escalate_complaint),

    path('admin-panel/reviews/', admin_reviews),
    path('admin-panel/reviews/<int:review_id>/delete/', admin_delete_review),

    path('admin-panel/reports/',       admin_reports),
    path('admin-panel/notifications/', admin_notifications),
    path('admin-panel/settings/',      admin_settings),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
