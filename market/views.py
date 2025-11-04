import mercadopago
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Product, Cart, CartItem
from .forms import ProductForm
 


def product_list(request):
    products = Product.objects.filter(active=True)

    category = request.GET.get('category')
    order = request.GET.get('order')

    if category:
        products = products.filter(category=category)

    if order == "asc":
        products = products.order_by('price')
    elif order == "desc":
        products = products.order_by('-price')
    else:
        products = products.order_by("-created_at")

    categories = Product.objects.values_list('category', flat=True).distinct()

    return render(
        request,
        "product_list.html",
        {
            "products": products,
            "categories": categories
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
            return redirect("market:productlist")
    else:
        form = ProductForm()
    return render(request, "product_form.html", {"form": form})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("market:productlist")
    else:
        form = ProductForm(instance=product)
    return render(request, "product_form.html", {"form": form})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == "POST":
        product.active = False
        product.save()
        return redirect("market:productlist")
    return render(request, "product_confirm_delete.html", {"product": product})


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    new_qty = item.quantity if created else item.quantity + 1
    if new_qty > product.stock:
        messages.warning(request, "No hay suficiente stock para agregar más unidades de este producto.")
    else:
        if created:
            messages.success(request, "Producto agregado al carrito.")
        else:
            item.quantity = new_qty
            item.save()
            messages.success(request, "Cantidad actualizada en el carrito.")
    return redirect("market:view-cart")


@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
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
    return redirect("market:view-cart")


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
    return redirect("market:view-cart")


@login_required
@require_POST
def cart_remove(request, product_id: int):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    return redirect("market:view-cart")


@login_required
def create_preference_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    items = []
    for item in cart.items.all():
        items.append({
            "title": item.product.title,
            "quantity": item.quantity,
            "unit_price": float(item.product.price),
            "currency_id": "ARS",
        })

    preference_data = {
        "items": items,
        "back_urls": {
            "success": request.build_absolute_uri("/market/pago-exitoso/"),
            "failure": request.build_absolute_uri("/market/pago-fallido/"),
        },
        "auto_return": "approved",
    }

    preference = sdk.preference().create(preference_data)
    return JsonResponse({"init_point": preference["response"]["init_point"]})


def payment_success(request):
    messages.success(request, "Pago aprobado. ¡Gracias por tu compra!")
    return render(request, "payment_success.html")


def payment_failure(request):
    messages.error(request, "El pago no se pudo completar o fue cancelado.")
    return render(request, "payment_failure.html")
