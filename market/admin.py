from django.contrib import admin
from django.db import transaction
from .models import Product, CartItem, Cart

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "seller", "marca", "price", "active", "created_at")  # columnas que ves en la lista
    search_fields = ("title", "description", "marca", "seller__username")          # campos por los que podés buscar
    list_filter = ("active", "created_at", "seller")                       # filtros en la barra lateral
    actions = ("soft_delete_selected", "safe_delete_selected",)

    # Al borrar productos desde el admin, primero limpiamos los CartItems relacionados
    # para evitar errores de clave foránea en bases con restricciones estrictas
    def delete_model(self, request, obj):
        CartItem.objects.filter(product=obj).delete()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        CartItem.objects.filter(product__in=queryset).delete()
        super().delete_queryset(request, queryset)

    # Reemplazamos la acción por defecto de borrado masivo por una segura
    def get_actions(self, request):
        actions = super().get_actions(request)
        # Quitamos la acción estándar para evitar el borrado rápido (fast delete)
        actions.pop("delete_selected", None)
        return actions

    # Acción recomendada: soft delete
    @admin.action(description="Ocultar seleccionados (soft delete)")
    def soft_delete_selected(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description="Eliminar seleccionados (limpia carritos primero)")
    def safe_delete_selected(self, request, queryset):
        # Ejecuta la limpieza y borrado dentro de una transacción atómica
        with transaction.atomic():
            CartItem.objects.filter(product__in=queryset).delete()
            # Borrado objeto por objeto para respetar hooks y señales
            for obj in queryset:
                super().delete_model(request, obj)

    # Deshabilitamos el botón de Delete en el admin para este modelo
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item_count", "total_amount")
    search_fields = ("user__username", "user__email")
    actions = ("empty_selected_carts",)

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = "Items"

    def total_amount(self, obj):
        try:
            return obj.total()
        except Exception:
            return "-"
    total_amount.short_description = "Total"

    @admin.action(description="Vaciar carritos seleccionados")
    def empty_selected_carts(self, request, queryset):
        CartItem.objects.filter(cart__in=queryset).delete()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity")
    list_filter = ("product", "cart__user")
    search_fields = ("product__title", "cart__user__username")
