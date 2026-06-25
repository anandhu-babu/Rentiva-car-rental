from django.core.management.base import BaseCommand
from django.utils import timezone

from CarRental.models import Booking, UserNotification


class Command(BaseCommand):
    help = 'Mark expired awaiting_renter_confirmation bookings as refunded and notify customers.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Booking.objects.filter(
            booking_status='awaiting_renter_confirmation',
            renter_confirmation_deadline__lt=now,
        ).select_related('user', 'car')

        count = 0
        for booking in expired:
            booking.booking_status = 'refunded'
            booking.save()

            UserNotification.objects.create(
                user=booking.user,
                notif_type='refund_issued',
                title='Booking Auto-Cancelled — Refund Initiated',
                message=(
                    f'Your booking for {booking.car.car_name} (#{booking.id}) was not confirmed '
                    f'by the renter within 24 hours. Your advance payment of '
                    f'₹{booking.advance_amount:,.0f} will be refunded within 5–7 business days.'
                ),
                related_booking=booking,
            )

            count += 1
            self.stdout.write(
                self.style.WARNING(f'  Refunded booking #{booking.id} for {booking.user.username}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Done. {count} expired booking(s) processed.')
        )
