from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, get_user_model
from .forms import ProfileForm
from market.models import Product

User = get_user_model()

@login_required
def profile_view(request):
    profile = request.user.profile
    user_products = Product.objects.filter(seller=request.user).select_related('seller').order_by('-created_at')
    
    context = {
        "profile": profile,
        "user_products": user_products,
        "is_own_profile": True,
    }
    return render(request, "profile.html", context)


@login_required
def user_profile_view(request, user_id):
    viewed_user = get_object_or_404(User, id=user_id)
    profile = viewed_user.profile
    user_products = Product.objects.filter(seller=viewed_user, active=True).select_related('seller').order_by('-created_at')
    
    context = {
        "profile": profile,
        "user_products": user_products,
        "viewed_user": viewed_user,
        "is_own_profile": request.user == viewed_user,
    }
    return render(request, "profile.html", context)


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        # Verificar si se marcó el checkbox para eliminar avatar
        should_clear_avatar = request.POST.get('avatar-clear') == 'on'
        
        if form.is_valid():
            # Guardar el formulario pero sin hacer commit todavía
            profile_instance = form.save(commit=False)
            
            # Si se marcó eliminar y hay un avatar, eliminarlo
            if should_clear_avatar and profile.avatar:
                profile.avatar.delete(save=False)
                profile_instance.avatar = None
            
            # Guardar los cambios
            profile_instance.save()
            messages.success(request, "Tu perfil ha sido actualizado correctamente.")
            return redirect("perfil:profile_view")
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
            return redirect("perfil:profile_view")
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
