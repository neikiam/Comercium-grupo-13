from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("home/", views.home, name="home"),
    path('login/', views.login_view, name='login'),
    path('tienda/', views.tienda, name='tienda'),
]