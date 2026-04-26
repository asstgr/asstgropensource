
from django.shortcuts import render, redirect, get_object_or_404


# Create your views here.


def how_it_works(request):
    return render(request, 'how_it_works.html')

