# Generated by Django 5.0.4 on 2024-05-13 19:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Holiday',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True, verbose_name='Дата праздника')),
                ('name', models.CharField(max_length=100, verbose_name='Название праздника')),
            ],
            options={
                'verbose_name': 'Праздник',
                'verbose_name_plural': 'Праздники',
            },
        ),
    ]
