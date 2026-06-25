from django.shortcuts import redirect
from django.contrib.auth.models import User


class AdminAuthenticationMiddleware:
    # Paths under /admin-panel/ that do NOT require an active admin session
    EXEMPT = {'/admin-panel/login/'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.admin_user = None

        if request.path.startswith('/admin-panel/') and request.path not in self.EXEMPT:
            admin_id = request.session.get('admin_user_id')
            if not admin_id:
                return redirect('/admin-panel/login/')

            try:
                request.admin_user = User.objects.get(pk=admin_id, is_staff=True)
            except User.DoesNotExist:
                # Stale or tampered session key — force re-login
                request.session.pop('admin_user_id', None)
                return redirect('/admin-panel/login/')

        return self.get_response(request)
