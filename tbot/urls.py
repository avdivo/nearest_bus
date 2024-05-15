from .views import telegram
from django.urls import path


urlpatterns = [
    path('', telegram, name='tbot'),
]


