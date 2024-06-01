from .views import alisa, gas
from django.urls import path


urlpatterns = [
    path('', alisa, name='alisa'),
    path('gas/', gas, name='gas'),
]


