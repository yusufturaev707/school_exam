from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.core.exceptions import ApiError


@csrf_exempt
def api_not_found(request):
    return JsonResponse({"code": "NOT_FOUND", "message": "No such API route"}, status=404)


def require_idempotency_key(request) -> None:
    """
    The contract requires this header, but we don't store it: repeated calls are already safe,
    because the row lock and status check make the operation happen exactly once.
    """
    if not request.headers.get("Idempotency-Key"):
        raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED")
