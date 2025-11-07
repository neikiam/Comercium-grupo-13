from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'category', 'description', 'marca', 'price', 'stock', 'image', 'active']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nombre del producto',
                'required': True,
            }),
            'category': forms.Select(attrs={
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Describe tu producto en detalle',
                'rows': 4,
                'required': True,
            }),
            'marca': forms.TextInput(attrs={
                'placeholder': 'Marca del producto (opcional)',
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True,
            }),
            'stock': forms.NumberInput(attrs={
                'placeholder': 'Cantidad disponible',
                'min': '1',
                'required': True,
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        help_texts = {
            'title': 'Máximo 200 caracteres',
            'description': 'Describe características, estado, etc.',
            'price': 'Precio en pesos argentinos (ARS)',
            'stock': 'Cantidad de unidades disponibles',
            'image': 'Imagen principal del producto (máx. 5MB)',
            'active': 'Desactiva tu producto si quieres pausar su publicación temporalmente',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields.pop('title', None)
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise forms.ValidationError("El título es obligatorio.")
        return title.strip()
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or not description.strip():
            raise forms.ValidationError("La descripción es obligatoria.")
        return description.strip()
    
    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category or not category.strip():
            raise forms.ValidationError("La categoría es obligatoria.")
        return category.strip()
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if not price or price <= 0:
            raise forms.ValidationError("El precio debe ser mayor a 0.")
        return price
    
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or stock < 1:
            raise forms.ValidationError("El stock debe ser al menos 1.")
        # Asegurar que sea entero
        try:
            stock = int(stock)
        except (ValueError, TypeError):
            raise forms.ValidationError("El stock debe ser un número entero.")
        if stock < 1:
            raise forms.ValidationError("El stock debe ser al menos 1.")
        return stock
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError("La imagen principal es obligatoria.")
        # Validar tamaño máximo (5MB)
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen no puede superar los 5MB.")
        return image