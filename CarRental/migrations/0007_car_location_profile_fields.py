from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRental', '0006_alter_car_brand_delete_brand'),
    ]

    operations = [
        # Car gets a city/location field so cars can be filtered by location
        migrations.AddField(
            model_name='car',
            name='location',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        # Profile extra fields used by the edit-profile template
        migrations.AddField(
            model_name='profile',
            name='location',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='languages',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='work',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='school',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='about',
            field=models.TextField(blank=True, null=True),
        ),
    ]
