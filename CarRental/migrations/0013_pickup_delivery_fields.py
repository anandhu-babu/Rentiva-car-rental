import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRental', '0012_booking_advance_amount_booking_remaining_amount_and_more'),
    ]

    operations = [
        # ── Car: pickup & delivery configuration ─────────────────────────────
        migrations.AddField(
            model_name='car',
            name='self_pickup_available',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='car',
            name='delivery_available',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='car',
            name='pickup_address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='car',
            name='pickup_latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='car',
            name='pickup_longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='car',
            name='delivery_radius',
            field=models.FloatField(blank=True, help_text='Delivery radius in km', null=True),
        ),
        migrations.AddField(
            model_name='car',
            name='delivery_charge',
            field=models.FloatField(blank=True, help_text='Delivery charge in ₹', null=True),
        ),

        # ── Booking: delivery method + nullable location FKs ─────────────────
        migrations.AddField(
            model_name='booking',
            name='delivery_method',
            field=models.CharField(
                choices=[('self_pickup', 'Self Pickup'), ('home_delivery', 'Home Delivery')],
                default='self_pickup',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='delivery_address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='pickup_location',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pickup_location',
                to='CarRental.location',
            ),
        ),
        migrations.AlterField(
            model_name='booking',
            name='drop_location',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='drop_location',
                to='CarRental.location',
            ),
        ),
    ]
