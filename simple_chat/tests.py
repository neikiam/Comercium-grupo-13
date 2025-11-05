from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import ChatMessage

User = get_user_model()


class ChatMessageModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_create_message(self):
        msg = ChatMessage.objects.create(user=self.user, text='Hello world')
        self.assertEqual(msg.text, 'Hello world')
        self.assertEqual(msg.user, self.user)
        self.assertIsNotNone(msg.created_at)

    def test_message_ordering(self):
        msg1 = ChatMessage.objects.create(user=self.user, text='First')
        msg2 = ChatMessage.objects.create(user=self.user, text='Second')
        messages = list(ChatMessage.objects.all())
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)


class ChatViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='chatuser', password='pass')

    def test_chat_view_requires_login(self):
        response = self.client.get(reverse('simple_chat:chat'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_chat_view_accessible_when_logged_in(self):
        self.client.login(username='chatuser', password='pass')
        response = self.client.get(reverse('simple_chat:chat'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chat del mercado')


class MessagesApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='pass')
        self.client.login(username='apiuser', password='pass')

    def test_messages_api_returns_empty_list(self):
        response = self.client.get(reverse('simple_chat:messages-api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['messages'], [])

    def test_messages_api_returns_messages(self):
        ChatMessage.objects.create(user=self.user, text='Test message 1')
        ChatMessage.objects.create(user=self.user, text='Test message 2')
        response = self.client.get(reverse('simple_chat:messages-api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['messages']), 2)
        self.assertEqual(data['messages'][0]['text'], 'Test message 1')
        self.assertEqual(data['messages'][1]['text'], 'Test message 2')

    def test_messages_api_filters_by_after_id(self):
        msg1 = ChatMessage.objects.create(user=self.user, text='Message 1')
        ChatMessage.objects.create(user=self.user, text='Message 2')
        response = self.client.get(reverse('simple_chat:messages-api') + f'?after_id={msg1.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['text'], 'Message 2')

    def test_messages_api_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('simple_chat:messages-api'))
        self.assertEqual(response.status_code, 302)


class PostMessageApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='poster', password='pass')
        self.client.login(username='poster', password='pass')

    def test_post_message_creates_message(self):
        response = self.client.post(
            reverse('simple_chat:post-api'),
            {'text': 'New message'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('created_at', data)
        self.assertEqual(ChatMessage.objects.count(), 1)
        msg = ChatMessage.objects.first()
        self.assertEqual(msg.text, 'New message')
        self.assertEqual(msg.user, self.user)

    def test_post_message_rejects_empty_text(self):
        response = self.client.post(
            reverse('simple_chat:post-api'),
            {'text': '   '}
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'empty')
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_post_message_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('simple_chat:post-api'),
            {'text': 'Test'}
        )
        self.assertEqual(response.status_code, 302)

    def test_post_message_requires_post_method(self):
        response = self.client.get(reverse('simple_chat:post-api'))
        self.assertEqual(response.status_code, 405)

