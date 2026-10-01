import sys
from django.conf import settings


class SessionDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/foncier/espaces/ajouter') or request.path.startswith('/accounts/login'):
            cookies = dict(request.COOKIES)
            session_key = request.session.session_key
            exists = request.session.exists(session_key) if session_key else False
            user_repr = getattr(request, 'user', None)
            print(
                f"[DEBUG] {request.method} {request.path} | "
                f"ALL_COOKIE_NAMES={list(cookies.keys())} | "
                f"cookie_session={cookies.get(settings.SESSION_COOKIE_NAME)} | "
                f"cookie_csrftoken={cookies.get('csrftoken')} | "
                f"session_key={session_key} exists_in_db={exists} | "
                f"user={user_repr} authenticated={getattr(user_repr, 'is_authenticated', None)}",
                file=sys.stderr, flush=True,
            )
        response = self.get_response(request)
        if request.path.startswith('/foncier/espaces/ajouter') or request.path.startswith('/accounts/login'):
            print(f"[DEBUG]   -> status={response.status_code}", file=sys.stderr, flush=True)
        return response
