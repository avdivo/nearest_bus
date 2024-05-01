from .views import telegram
from django.urls import path


urlpatterns = [
    path('tbot/', telegram, name='tbot'),
]


