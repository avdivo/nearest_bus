from django.contrib import admin

from .models import BotUser, Parameter, IdsForName


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    """Пользователи в Админке"""
    list_display = ('user_name', 'user_login', 'user_id', 'user_menu')
    search_fields = ['user_name', 'user_login', 'user_id']
    list_filter = ('user_menu',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Параметры в Админке"""
    list_display = ('class_name', 'favorites', 'addition', 'bot_user')
    search_fields = ['class_name', 'bot_user']


@admin.register(IdsForName)
class IdsForNameAdmin(admin.ModelAdmin):
    """Идентификаторы в Админке"""
    list_display = ('name', 'id')
