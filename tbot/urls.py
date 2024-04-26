from .views import bot
from django.urls import path


urlpatterns = [
    path('tbot/', bot, name='tbot'),
]


