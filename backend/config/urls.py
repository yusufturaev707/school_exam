from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import api_not_found

admin.site.site_header = "Bilimdon boshqaruv paneli"
admin.site.site_title = "Bilimdon admin"
admin.site.index_title = "Boshqaruv"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.exams.urls")),
    path("api/", include("apps.games.urls")),
    # Must stay last: unknown API paths answer with the JSON error format, not an HTML page.
    re_path(r"^api/", api_not_found),
    # Serves uploaded images in development only; in production nginx serves /media/ itself.
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
