from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from CarRental.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', homefn),
    path('register/', registerfn),
    path('login/', loginfn),
    path('logout/', logoutfn),

    path('become-renter/', becomeRenterfn),
    path('dashboard/customer/', customerDashboardfn),
    path('dashboard/renter/', renterDashboardfn),
    path('cars/<int:car_id>/', carDetailsfn),
    path('cars/', carListfn),
    path('car/list/', carListfn),

    # Car management (renter only)
    path('add-car/', addCarfn),
    path('my-cars/edit/<int:car_id>/', editCarfn),
    path('my-cars/delete/<int:car_id>/', deleteCarfn),

    # Booking
    path('booking/<int:car_id>/', bookingfn),
    path('booking/cancel/<int:booking_id>/', cancelBookingfn),
    path('booking/<int:booking_id>/approve/', approveBookingfn),
    path('booking/<int:booking_id>/reject/', rejectBookingfn),
    path('booking/<int:booking_id>/complete/', completeBookingfn),
    path('payment/', paymentfn),

    # Profile
    path('profile/', editDashboardfn),
    path('edit-profile/', editDashboardfn),

    # Chatbot
    path('chatbot/query/', chatbot_query),
    
    #RESTAPIs
    
    path('api/cars/', apiCarListfn),
    path('api/cars/<int:car_id>/', apiCarDetailsfn),
    path('api/cars/search/', apiSearchCarfn),
    path('api/cars/add/', apiAddCarfn),
    path('api/booking/<int:car_id>/', apiBookingfn),
    path('api/my-bookings/', apiMyBookingsfn),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
