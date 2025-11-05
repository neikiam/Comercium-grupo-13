from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django_ratelimit.decorators import ratelimit
from .models import ChatMessage, DirectMessageThread, DirectMessage

@login_required
def chat_view(request):
    return render(request, "chat.html")

@login_required
@ratelimit(key="user", rate="60/m", method="GET", block=True)
def messages_api(request):
    after = request.GET.get("after_id")
    qs = ChatMessage.objects.select_related("user", "user__profile").all()
    if after:
        qs = qs.filter(id__gt=int(after))
    msgs = []
    for m in qs:
        if m.user:
            if hasattr(m.user, "profile") and m.user.profile.avatar:
                avatar = m.user.profile.avatar.url
            else:
                avatar = f"https://ui-avatars.com/api/?name={m.user.username}&background=random"
            username = m.user.username
            user_id = m.user.id
        else:
            avatar = None
            username = "Anon"
            user_id = None
        msgs.append({
            "id": m.id,
            "user_id": user_id,
            "user": username,
            "avatar": avatar,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
        })
    return JsonResponse({"messages": msgs})

@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def post_message_api(request):
    user = request.user
    text = request.POST.get("text","").strip()
    if not text:
        return JsonResponse({"error": "empty"}, status=400)
    m = ChatMessage.objects.create(user=user, text=text)
    return JsonResponse({"id": m.id, "created_at": m.created_at.isoformat()})


@login_required
def private_list(request):
    user = request.user
    threads = DirectMessageThread.objects.filter(user1=user) | DirectMessageThread.objects.filter(user2=user)
    threads = threads.select_related("user1", "user2").order_by("-created_at")
    return render(request, "private_list.html", {"threads": threads})


@login_required
def private_chat(request, thread_id: int):
    thread = get_object_or_404(DirectMessageThread, id=thread_id)
    if request.user not in thread.participants():
        return HttpResponseForbidden()
    other = thread.user1 if thread.user2 == request.user else thread.user2
    return render(request, "private_chat.html", {"thread": thread, "other": other})


@login_required
def private_start(request, user_id: int):
    User = get_user_model()
    other = get_object_or_404(User, id=user_id)
    if other == request.user:
        return redirect("simple_chat:private-list")
    a, b = (request.user, other) if request.user.id < other.id else (other, request.user)
    thread, _ = DirectMessageThread.objects.get_or_create(user1=a, user2=b)
    return redirect("simple_chat:private-chat", thread_id=thread.id)


@login_required
def private_start_by_username(request):
    if request.method != "POST":
        return HttpResponseForbidden()
    username = request.POST.get("username", "").strip()
    if not username:
        return redirect("simple_chat:private-list")
    
    User = get_user_model()
    
    # Búsqueda flexible: busca coincidencias exactas primero, luego parciales
    try:
        # Intenta encontrar coincidencia exacta (case-insensitive)
        other = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        # Si no hay coincidencia exacta, busca coincidencias parciales
        matches = User.objects.filter(
            Q(username__icontains=username) | 
            Q(first_name__icontains=username) | 
            Q(last_name__icontains=username)
        ).exclude(id=request.user.id)[:10]
        
        if matches.count() == 0:
            # No se encontró ningún usuario
            threads = DirectMessageThread.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ).select_related("user1", "user2").order_by("-created_at")
            
            return render(request, "private_list.html", {
                "threads": threads,
                "error_message": f'No se encontró ningún usuario con "{username}"',
                "search_query": username
            })
        elif matches.count() == 1:
            # Solo una coincidencia, usar esa
            other = matches.first()
        else:
            # Múltiples coincidencias, mostrar para que el usuario elija
            threads = DirectMessageThread.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ).select_related("user1", "user2").order_by("-created_at")
            
            return render(request, "private_list.html", {
                "threads": threads,
                "user_suggestions": matches,
                "search_query": username
            })
    except User.MultipleObjectsReturned:
        # No debería pasar con username único, pero por si acaso
        other = User.objects.filter(username__iexact=username).first()
    
    if other == request.user:
        return redirect("simple_chat:private-list")
    
    a, b = (request.user, other) if request.user.id < other.id else (other, request.user)
    thread, _ = DirectMessageThread.objects.get_or_create(user1=a, user2=b)
    return redirect("simple_chat:private-chat", thread_id=thread.id)


@login_required
@ratelimit(key="user", rate="30/m", method="GET", block=True)
def search_users_api(request):
    """API para buscar usuarios en tiempo real (autocompletado)"""
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"users": []})
    
    User = get_user_model()
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).select_related("profile")[:10]
    
    results = []
    for u in users:
        avatar = None
        if hasattr(u, "profile") and u.profile.avatar:
            avatar = u.profile.avatar.url
        else:
            avatar = f"https://ui-avatars.com/api/?name={u.username}&background=random&size=40"
        
        display_name = u.get_full_name() or u.username
        results.append({
            "id": u.id,
            "username": u.username,
            "display_name": display_name,
            "avatar": avatar
        })
    
    return JsonResponse({"users": results})


@login_required
@ratelimit(key="user", rate="60/m", method="GET", block=True)
def private_messages_api(request, thread_id: int):
    thread = get_object_or_404(DirectMessageThread, id=thread_id)
    if request.user not in thread.participants():
        return HttpResponseForbidden()
    after = request.GET.get("after_id")
    qs = thread.messages.select_related("user", "user__profile").all()
    if after:
        qs = qs.filter(id__gt=int(after))
    msgs = []
    for m in qs:
        if m.user:
            if hasattr(m.user, "profile") and m.user.profile.avatar:
                avatar = m.user.profile.avatar.url
            else:
                avatar = f"https://ui-avatars.com/api/?name={m.user.username}&background=random"
            username = m.user.username
            user_id = m.user.id
        else:
            avatar = None
            username = "Anon"
            user_id = None
        msgs.append({
            "id": m.id,
            "user_id": user_id,
            "user": username,
            "avatar": avatar,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
        })
    return JsonResponse({"messages": msgs})


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def private_post_message_api(request, thread_id: int):
    thread = get_object_or_404(DirectMessageThread, id=thread_id)
    if request.user not in thread.participants():
        return HttpResponseForbidden()
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "empty"}, status=400)
    m = DirectMessage.objects.create(thread=thread, user=request.user, text=text)
    return JsonResponse({"id": m.id, "created_at": m.created_at.isoformat()})
