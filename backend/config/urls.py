from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import api_not_found, editor_image_upload

admin.site.site_header = "Bilimdon boshqaruv paneli"
admin.site.site_title = "Bilimdon admin"
admin.site.index_title = "Boshqaruv"

urlpatterns = [
    path("admin/", admin.site.urls),
    # The editor's widget finds its upload address by this name. Pictures go into the question
    # text itself, so no /media/ files are stored or served.
    path("ckeditor5/image_upload/", editor_image_upload, name="ck_editor_5_upload_file"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.exams.urls")),
    path("api/", include("apps.games.urls")),
    # Must stay last: unknown API paths answer with the JSON error format, not an HTML page.
    re_path(r"^api/", api_not_found),
]
