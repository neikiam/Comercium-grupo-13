import logging

import mercadopago
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

from .forms import ProductForm
from .models import Cart, CartItem, Product
from .services import CartService, ProductService

logger = logging.getLogger(__name__)
@cache_page(60 * 5)  # Cache por 5 minutos
def product_list(request):
    """
    Lista productos activos con filtrado, búsqueda, ordenamiento y paginación.
    
    Args:
        request: HttpRequest con parámetros opcionales:
            - categories: filtro de categorías (separadas por coma)
            - order: ordenamiento (recent, oldest, price_asc, price_desc)
            - q: búsqueda por texto
            - page: número de página
    
    Returns:
        HttpResponse con template de lista de productos
    """
    products = Product.objects.filter(active=True).select_related('seller')

    # Filtro de múltiples categorías
    categories_param = request.GET.get('categories')
    if categories_param is not None:
        category_list = [c.strip() for c in categories_param.split(',') if c.strip()]
        products = products.filter(category__in=category_list)

    order = request.GET.get('order')
    query = request.GET.get('q')

    if query:
        products = products.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(marca__icontains=query) |
            Q(category__icontains=query)
        )

    # Ordenamiento: recent (default), oldest, price_asc, price_desc
    if order == "price_asc":
        products = products.order_by('price')
    elif order == "price_desc":
        products = products.order_by('-price')
    elif order == "oldest":
        products = products.order_by('created_at')
    else:
        products = products.order_by('-created_at')

    all_categories = Product.CATEGORY_CHOICES

    get_params = request.GET.copy()
    get_params.pop('page', None)
    base_qs = get_params.urlencode()

    # Mostrar 50 productos por página
    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "product_list.html",
        {
            "page_obj": page_obj,
            "all_categories": all_categories,
            "base_qs": base_qs,
        }
    )

def product_detail(request, pk: int):
    """
    Muestra el detalle de un producto específico.
    
    Args:
        request: HttpRequest
        pk: ID del producto
    
    Returns:
        HttpResponse con template de detalle de producto
    """
    product = get_object_or_404(Product, pk=pk, active=True)
    return render(request, "product_detail.html", {"product": product})


@login_required
def product_create(request):
    """
    Permite a usuarios autenticados crear nuevos productos para vender.
    
    Args:
        request: HttpRequest (POST con form data o GET para mostrar formulario)
    
    Returns:
        HttpResponse con formulario o redirect a lista de productos
    """
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            ProductService.create_product(request.user, form)
            messages.success(request, "Producto creado correctamente.")
            return redirect("mercado:productlist")
    else:
        form = ProductForm()
    return render(request, "product_form.html", {"form": form, "is_edit": False})


@login_required
def product_edit(request, pk):
    """
    Permite editar un producto existente. Solo el vendedor propietario puede editar.
    
    Args:
        request: HttpRequest (POST con form data o GET para mostrar formulario)
        pk: ID del producto a editar
    
    Returns:
        HttpResponse con formulario o redirect a lista de productos
    """
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    old_image = product.image if product.image else None
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            ProductService.update_product(product, form, old_image)
            messages.success(request, "Producto actualizado correctamente.")
            return redirect("mercado:productlist")
    else:
        form = ProductForm(instance=product)
    return render(request, "product_form.html", {"form": form, "is_edit": True})


@login_required
def product_delete(request, pk):
    """
    Elimina un producto. Solo el vendedor propietario puede eliminarlo.
    
    Args:
        request: HttpRequest (POST para confirmar o GET para mostrar confirmación)
        pk: ID del producto a eliminar
    
    Returns:
        HttpResponse con confirmación o redirect tras eliminación
    """
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == "POST":
        ProductService.delete_product(product)
        messages.success(request, "Producto eliminado correctamente.")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("mercado:productlist")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    return render(request, "product_confirm_delete.html", {"product": product, "next_url": next_url})


@login_required
@require_POST
def add_to_cart(request, product_id):
    """
    Añade un producto al carrito del usuario.
    
    Args:
        request: HttpRequest
        product_id: ID del producto a añadir
    
    Returns:
        Redirect a vista del carrito
    """
    product = get_object_or_404(Product, id=product_id)
    success, message = CartService.add_item(request.user, product)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect("mercado:view-cart")


@login_required
def view_cart(request):
    """
    Muestra el carrito de compras del usuario.
    
    Args:
        request: HttpRequest
    
    Returns:
        HttpResponse con template del carrito
    """
    cart, created = CartService.get_or_create_cart(request.user)
    context = {
        "cart": cart,
        "PUBLIC_KEY": getattr(settings, "MERCADOPAGO_PUBLIC_KEY", None),
    }
    return render(request, "cart.html", context)


@login_required
@require_POST
def cart_increase(request, product_id: int):
    """
    Incrementa la cantidad de un producto en el carrito.
    
    Args:
        request: HttpRequest
        product_id: ID del producto
    
    Returns:
        Redirect a vista del carrito
    """
    success, message = CartService.increase_quantity(request.user, product_id)
    
    if not success:
        messages.warning(request, message)
    
    return redirect("mercado:view-cart")


@login_required
@require_POST
def cart_decrease(request, product_id: int):
    """
    Decrementa la cantidad de un producto en el carrito.
    
    Args:
        request: HttpRequest
        product_id: ID del producto
    
    Returns:
        Redirect a vista del carrito
    """
    CartService.decrease_quantity(request.user, product_id)
    return redirect("mercado:view-cart")


@login_required
@require_POST
def cart_remove(request, product_id: int):
    """
    Elimina un producto del carrito.
    
    Args:
        request: HttpRequest
        product_id: ID del producto a eliminar
    
    Returns:
        Redirect a vista del carrito
    """
    CartService.remove_item(request.user, product_id)
    return redirect("mercado:view-cart")


@login_required
def create_preference_cart(request):
    """Crea una preferencia de pago para el carrito del usuario.
    Incluye validaciones de token, carrito vacío y manejo robusto de errores.
    """
    cart, created = CartService.get_or_create_cart(request.user)

    # Validar ACCESS TOKEN
    access_token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", None)
    if not access_token:
        logger.error("MERCADOPAGO_ACCESS_TOKEN no configurado")
        return JsonResponse(
            {"error": "payment_unavailable", "message": "Servicio de pago no disponible temporalmente."},
            status=503,
        )

    # Validar el carrito con el servicio
    is_valid, error_message = CartService.validate_cart_for_checkout(cart)
    if not is_valid:
        logger.warning(f"Validación de carrito fallida para usuario {request.user.id}: {error_message}")
        return JsonResponse(
            {"error": "cart_validation_failed", "message": error_message},
            status=400,
        )

    sdk = mercadopago.SDK(access_token)
    
    cart_items = cart.items.select_related('product').all()
    items = []
    for item in cart_items:
        # Seguridad: forzar tipos primitivos y evitar valores sospechosos en título
        title = (item.product.title or "Producto").strip()[:120]
        items.append({
            "title": title,
            "quantity": int(item.quantity),
            "unit_price": float(item.product.price),
            "currency_id": "ARS",
        })

    preference_data = {
        "items": items,
        "back_urls": {
            "success": request.build_absolute_uri("/mercado/pago-exitoso/"),
            "failure": request.build_absolute_uri("/mercado/pago-fallido/"),
        },
        "auto_return": "approved",
    }

    try:
        preference = sdk.preference().create(preference_data)
        response = preference.get("response", {})
        init_point = response.get("init_point")
        if not init_point:
            logger.error(f"MercadoPago no devolvió init_point para usuario {request.user.id}")
            return JsonResponse(
                {"error": "payment_error", "message": "No se pudo iniciar el pago. Intenta más tarde."},
                status=502,
            )
        logger.info(f"Preferencia de pago creada para usuario {request.user.id}")
        return JsonResponse({"init_point": init_point})
    except Exception as e:
        logger.exception(f"Error al crear preferencia de pago para usuario {request.user.id}: {e}")
        return JsonResponse(
            {"error": "payment_exception", "message": "Ocurrió un error al iniciar el pago."},
            status=502,
        )
    


def payment_success(request):
    """
    Vista para manejar el retorno exitoso desde MercadoPago.
    
    Args:
        request: HttpRequest con parámetros de pago de MercadoPago
    
    Returns:
        HttpResponse con template de éxito
    """
    messages.success(request, "Pago aprobado. ¡Gracias por tu compra!")
    return render(request, "payment_success.html")


def payment_failure(request):
    """
    Vista para manejar fallo o cancelación del pago desde MercadoPago.
    
    Args:
        request: HttpRequest con parámetros de pago de MercadoPago
    
    Returns:
        HttpResponse con template de fallo
    """
    messages.error(request, "El pago no se pudo completar o fue cancelado.")
    return render(request, "payment_failure.html")
