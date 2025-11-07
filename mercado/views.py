import mercadopago
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Product, Cart, CartItem
from .forms import ProductForm
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.db.models import Q


def product_list(request):
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
    product = get_object_or_404(Product, pk=pk, active=True)
    return render(request, "product_detail.html", {"product": product})


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, "Producto creado correctamente.")
            return redirect("mercado:productlist")
    else:
        form = ProductForm()
    return render(request, "product_form.html", {"form": form, "is_edit": False})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado correctamente.")
            return redirect("mercado:productlist")
    else:
        form = ProductForm(instance=product)
    return render(request, "product_form.html", {"form": form, "is_edit": True})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == "POST":
        # Eliminar definitivamente el producto (y recursos asociados por señales)
        product.delete()
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("mercado:productlist")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    return render(request, "product_confirm_delete.html", {"product": product, "next_url": next_url})


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if not product.is_available():
        messages.error(request, "Este producto no está disponible.")
        return redirect("mercado:productlist")
    
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    new_qty = 1 if created else item.quantity + 1
    
    if new_qty > product.stock:
        messages.warning(request, f"Solo hay {product.stock} unidades disponibles.")
        if created:
            item.delete()
    else:
        item.quantity = new_qty
        item.save()
        messages.success(request, "Producto agregado al carrito.")
    
    return redirect("mercado:view-cart")


@login_required
def view_cart(request):
    cart, created = Cart.objects.prefetch_related('items__product__seller').get_or_create(user=request.user)
    context = {
        "cart": cart,
        "PUBLIC_KEY": getattr(settings, "MERCADOPAGO_PUBLIC_KEY", None),
    }
    return render(request, "cart.html", context)


@login_required
@require_POST
def cart_increase(request, product_id: int):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    if item.quantity + 1 > item.product.stock:
        messages.warning(request, "No hay suficiente stock para aumentar la cantidad.")
    else:
        item.quantity += 1
        item.save()
    return redirect("mercado:view-cart")


@login_required
@require_POST
def cart_decrease(request, product_id: int):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
    return redirect("mercado:view-cart")


@login_required
@require_POST
def cart_remove(request, product_id: int):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    return redirect("mercado:view-cart")


@login_required
def create_preference_cart(request):
    """Crea una preferencia de pago para el carrito del usuario.
    Incluye validaciones de token, carrito vacío y manejo robusto de errores.
    """
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Validar ACCESS TOKEN
    access_token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", None)
    if not access_token:
        return JsonResponse(
            {"error": "payment_unavailable", "message": "Servicio de pago no disponible temporalmente."},
            status=503,
        )

    # Validar que el carrito no esté vacío
    if not cart.items.exists():
        return JsonResponse(
            {"error": "empty_cart", "message": "Tu carrito está vacío."},
            status=400,
        )

    sdk = mercadopago.SDK(access_token)

    items = []
    for item in cart.items.all():
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
            return JsonResponse(
                {"error": "payment_error", "message": "No se pudo iniciar el pago. Intenta más tarde."},
                status=502,
            )
        return JsonResponse({"init_point": init_point})
    except Exception:
        # Evitar filtrar detalles del error al cliente
        return JsonResponse(
            {"error": "payment_exception", "message": "Ocurrió un error al iniciar el pago."},
            status=502,
        )


def payment_success(request):
    messages.success(request, "Pago aprobado. ¡Gracias por tu compra!")
    return render(request, "payment_success.html")


def payment_failure(request):
    messages.error(request, "El pago no se pudo completar o fue cancelado.")
    return render(request, "payment_failure.html")
