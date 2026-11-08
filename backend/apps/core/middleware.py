from django.http import JsonResponse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class ApiGuardMiddleware:
    """
    Two rules for every /api/ request.

    CSRF: state-changing requests must carry `X-Requested-With: XMLHttpRequest` (the frontend's
    axios instance always sends it). A foreign site cannot add a custom header without a CORS
    preflight, and we enable no CORS at all. Together with the SameSite=Lax cookie this replaces
    a CSRF token for this JSON API. The admin keeps Django's normal CSRF protection.

    Caching: exam data must never be stored by a browser or proxy, hence `no-store`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        if (
            request.method not in SAFE_METHODS
            and request.headers.get("X-Requested-With") != "XMLHttpRequest"
        ):
            response = JsonResponse(
                {"code": "CSRF_CHECK_FAILED", "message": "Missing X-Requested-With header"},
                status=403,
            )
        else:
            response = self.get_response(request)

        response["Cache-Control"] = "no-store"
        return response
