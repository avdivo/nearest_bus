# Generated by Django 5.0.4 on 2024-05-13 19:41

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0002_holiday'),
    ]

    operations = [
        migrations.AddField(
            model_name='holiday',
            name='day',
            field=models.IntegerField(default=7, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(7)], verbose_name='День недели'),
        ),
    ]
