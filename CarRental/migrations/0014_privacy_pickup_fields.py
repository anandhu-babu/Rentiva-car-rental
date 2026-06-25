from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRental', '0013_pickup_delivery_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='car',
            name='pickup_point_name',
            field=models.CharField(
                blank=True, null=True, max_length=200,
                help_text='Public landmark name, e.g. "Technopark Gate 1"'
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='pickup_instructions',
            field=models.TextField(blank=True, null=True),
        ),
    ]
