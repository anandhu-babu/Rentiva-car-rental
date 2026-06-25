from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRental', '0014_privacy_pickup_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='rental_plan',
            field=models.CharField(
                max_length=10,
                choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
                default='daily',
            ),
        ),
    ]
