# Generated by Django 3.2.8 on 2021-11-09 19:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_car_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='car',
            old_name='number',
            new_name='brand',
        ),
    ]
