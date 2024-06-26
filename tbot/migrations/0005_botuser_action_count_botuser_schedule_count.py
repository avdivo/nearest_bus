# Generated by Django 5.0.4 on 2024-05-15 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0004_botuser_last_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='botuser',
            name='action_count',
            field=models.IntegerField(default=0, verbose_name='Количество всех действий'),
        ),
        migrations.AddField(
            model_name='botuser',
            name='schedule_count',
            field=models.IntegerField(default=0, verbose_name='Количество запросов расписаний'),
        ),
    ]
