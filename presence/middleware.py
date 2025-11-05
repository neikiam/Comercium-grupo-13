from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.auth import logout
from .models import UserActivity
from django.db.utils import OperationalError

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = timezone.now().timestamp()
            last = request.session.get("last_activity", now_ts)
            if now_ts - last > 1800:
                logout(request)
                return redirect("presence:session_expired")
            request.session["last_activity"] = now_ts
        return self.get_response(request)

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = timezone.now().timestamp()
            last_update = request.session.get("last_seen_update", 0)
            # Reducimos la frecuencia de escritura a cada 5 minutos para evitar locks en SQLite
            if now_ts - last_update >= 300:
                try:
                    UserActivity.objects.update_or_create(
                        user=request.user, defaults={"last_seen": timezone.now()}
                    )
                    request.session["last_seen_update"] = now_ts
                except OperationalError:
                    # Si la base está bloqueada, no interrumpimos la request; reintentará más tarde
                    pass
        return self.get_response(request)
