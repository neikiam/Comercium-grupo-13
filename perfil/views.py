from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import ProfileForm
from mercado.models import Product

User = get_user_model()

@login_required
def profile_view(request):
    profile = request.user.profile
    # Mostrar solo productos activos del usuario para evitar ver eliminados o pausados
    user_products = Product.objects.filter(seller=request.user, active=True).select_related('seller').order_by('-created_at')
    
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
        
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil ha sido actualizado correctamente.")
            return redirect("perfil:profile_view")
        else:
            messages.error(request, "Hubo un error al actualizar tu perfil. Revisa los datos.")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "profile_edit.html", {"form": form})


@login_required
def delete_avatar(request):
    if request.method == "POST":
        profile = request.user.profile
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save()
            messages.success(request, "Tu foto de perfil ha sido eliminada.")
        else:
            messages.info(request, "No tienes una foto de perfil para eliminar.")
        return redirect("perfil:edit_profile")
    return redirect("perfil:edit_profile")
