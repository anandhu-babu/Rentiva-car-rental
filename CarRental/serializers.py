from rest_framework import serializers
from .models import Car, Booking, Review, Location


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user_name', 'rating', 'comment', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class CarSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Car
        fields = [
            'id', 'car_name', 'brand', 'model', 'year', 'fuel',
            'transmission', 'seats', 'location', 'availability',
            'rent_per_day', 'image', 'description', 'created_at',
        ]
        read_only_fields = ['created_at']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'city', 'state', 'pincode']


class BookingSerializer(serializers.ModelSerializer):
    car_name             = serializers.CharField(source='car.car_name', read_only=True)
    pickup_location_name = serializers.CharField(source='pickup_location.city', read_only=True)
    drop_location_name   = serializers.CharField(source='drop_location.city', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'car', 'car_name',
            'pickup_location', 'pickup_location_name',
            'drop_location', 'drop_location_name',
            'pickup_date', 'return_date',
            'total_amount', 'booking_status', 'booked_at',
        ]
        read_only_fields = ['total_amount', 'booking_status', 'booked_at']
