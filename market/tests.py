from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Product, Cart, CartItem


class MarketViewsTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="u1", password="pass12345")
		self.product = Product.objects.create(
			seller=self.user,
			title="Prod1",
			description="Desc",
			price=100,
			stock=5,
			active=True,
		)

	def test_product_detail(self):
		url = reverse("market:product-detail", args=[self.product.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, "Prod1")

	def test_cart_increase_decrease_remove(self):
		self.client.login(username="u1", password="pass12345")

		add_url = reverse("market:add-to-cart", args=[self.product.pk])
		self.client.post(add_url)
		cart = Cart.objects.get(user=self.user)
		item = CartItem.objects.get(cart=cart, product=self.product)
		self.assertEqual(item.quantity, 1)

		inc_url = reverse("market:cart-increase", args=[self.product.pk])
		dec_url = reverse("market:cart-decrease", args=[self.product.pk])
		rem_url = reverse("market:cart-remove", args=[self.product.pk])

		self.client.post(inc_url)
		item.refresh_from_db()
		self.assertEqual(item.quantity, 2)

		self.client.post(dec_url)
		item.refresh_from_db()
		self.assertEqual(item.quantity, 1)

		self.client.post(rem_url)
		self.assertFalse(CartItem.objects.filter(cart=cart, product=self.product).exists())
