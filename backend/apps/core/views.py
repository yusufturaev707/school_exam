from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ckeditor_5.forms import UploadFileForm
from django_ckeditor_5.permissions import check_upload_permission

from apps.core.exceptions import ApiError
from apps.core.images import ImageError, compress_image, data_uri


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


@require_POST
@check_upload_permission
def editor_image_upload(request):
    """
    Takes the place of django-ckeditor-5's upload view. The editor sends the picture here and puts
    whatever "url" comes back into <img src>. Instead of a file under /media/ that "url" is the
    compressed picture itself, so it ends up inside the question text. See apps/core/images.py.
    """
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        message = (form.errors.get("upload") or ["Rasm yuborilmadi."])[0]
        return JsonResponse({"error": {"message": message}}, status=400)
    try:
        webp = compress_image(form.cleaned_data["upload"].read())
    except ImageError as error:
        return JsonResponse({"error": {"message": error.messages[0]}}, status=400)
    return JsonResponse({"url": data_uri(webp)})
