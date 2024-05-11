from django.contrib import admin

from .models import BusStop, Order, Router, Bus, Schedule


@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    """Настройки в Админке"""
    list_display = ('name', 'external_id', 'finish')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки в Админке"""
    list_display = ('router', 'bus_stop', 'order_number')


@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    """Настройки в Админке"""
    list_display = ('start', 'end', 'bus')


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    """Настройки в Админке"""
    list_display = ('number', 'active')


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """Настройки в Админке"""
    list_display = ('bus', 'bus_stop', 'time', 'day')
    list_filter = ('bus', 'bus_stop', 'day')
    search_fields = ('bus', 'bus_stop', 'time')
    list_editable = ('time', 'day')
