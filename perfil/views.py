from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import ProfileForm
from market.models import Product

@login_required
def profile_view(request):
    profile = request.user.profile
    user_products = Product.objects.filter(seller=request.user).order_by('-created_at')
    
    context = {
        "profile": profile,
        "user_products": user_products,
    }
    return render(request, "profile.html", context)


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil ha sido actualizado correctamente.")
            return redirect("profile")
        else:
            messages.error(request, "Hubo un error al actualizar tu perfil. Revisa los datos.")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "profile_edit.html", {"form": form})


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect("profile")
        else:
            messages.error(request, "Error al cambiar la contraseña. Revisa los datos.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, "profile_change_password.html", {"form": form})


@login_required
def delete_profile(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Tu cuenta ha sido eliminada correctamente.")
        return redirect("home")
    return render(request, "profile_delete_confirm.html")
