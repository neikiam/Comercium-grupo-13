from django.shortcuts import render, redirect
from market.models import Product

def home(request):
    productos = [
        {'imagen': 'home/producto1.jpg', 'descripcion': 'Frutas frescas y naturales'},
        {'imagen': 'home/producto2.jpg', 'descripcion': 'Verduras seleccionadas'},
        {'imagen': 'home/producto3.jpg', 'descripcion': 'Pan casero del día'},
    ]
    products = Product.objects.filter(active=True).select_related('seller').order_by("-created_at")[:6]
    return render(request, "index.html", {"products": products})

def login_view(request):
    return render(request, 'login.html')