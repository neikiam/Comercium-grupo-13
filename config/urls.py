from django.contrib import admin
from django.urls import path, include
from core.views import home
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.templatetags.static import static as static_tag

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("allauth.urls")),
    path("market/", include("mercado.urls")),
    path("profiles/", include("perfil.urls")),
    path("user-activity/", include("user_activity.urls")),
    path("chat/", include("chat_interno.urls")),
    path('core/', include('core.urls')),
    path("favicon.ico", RedirectView.as_view(url=static_tag('favicon.svg'), permanent=True)),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)