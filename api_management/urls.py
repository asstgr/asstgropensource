# core/urls.py
from django.urls import path
from . import views
from django.shortcuts import redirect


app_name = 'api_management'

urlpatterns = [

    path('', views.how_it_works, name='how_it_works'),


]
