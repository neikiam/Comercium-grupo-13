from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from market.models import Product


@admin.action(description="Desactivar usuarios y ocultar sus productos")
def deactivate_users_and_hide_products(modeladmin, request, queryset):
	# Desactivamos usuarios para impedir login
	queryset.update(is_active=False)
	# Ocultamos todos sus productos del catálogo
	Product.objects.filter(seller__in=queryset).update(active=False)


class UserAdmin(DjangoUserAdmin):
	actions = DjangoUserAdmin.actions + (deactivate_users_and_hide_products,)


# Reemplazamos el UserAdmin por nuestra versión extendida
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
