from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.auth import logout
from .models import UserActivity

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
            if now_ts - last_update >= 120:
                UserActivity.objects.update_or_create(user=request.user, defaults={"last_seen": timezone.now()})
                request.session["last_seen_update"] = now_ts
        return self.get_response(request)
