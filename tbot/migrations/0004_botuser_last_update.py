# Generated by Django 5.0.4 on 2024-05-14 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0003_idsforname'),
    ]

    operations = [
        migrations.AddField(
            model_name='botuser',
            name='last_update',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='Последнее обновление'),
        ),
    ]