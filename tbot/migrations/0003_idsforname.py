# Generated by Django 5.0.4 on 2024-05-13 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tbot', '0002_alter_botuser_user_login_alter_botuser_user_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='IdsForName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='Имя')),
            ],
            options={
                'verbose_name': 'Идентификатор для имени',
                'verbose_name_plural': 'Идентификаторы для имен',
            },
        ),
    ]