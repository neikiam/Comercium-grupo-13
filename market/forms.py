from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["title", "description", "price", "stock", "image", "active", "marca", "category"]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
        }
        labels = {
            'title': 'Título del producto',
            'description': 'Descripción',
            'price': 'Precio (ARS)',
            'stock': 'Stock disponible',
            'marca': 'Marca',
            'category': 'Categoría',
        }
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return price
    
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock and stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")
        return stock