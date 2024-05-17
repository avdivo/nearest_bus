from .views import alisa
from django.urls import path


urlpatterns = [
    path('', alisa, name='alisa'),
]


