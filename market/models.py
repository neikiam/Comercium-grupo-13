from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db import models

class Product(models.Model):
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=200, blank=True, default="sin categoria")
    description = models.TextField(blank=True)
    marca = models.CharField(max_length=100, blank=True, default="Generico")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def is_available(self):
        return self.active and self.stock > 0
    
# Carrito
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def total(self):
        return sum(item.subtotal() for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.price * self.quantity


# En algunos entornos (p. ej. SQLite con constraints antiguas), eliminar un Product
# desde el admin puede lanzar IntegrityError. Este hook asegura limpiar
# los CartItem asociados antes del borrado del producto.
@receiver(pre_delete, sender=Product)
def cleanup_cartitems_on_product_delete(sender, instance, **kwargs):
    CartItem.objects.filter(product=instance).delete()
