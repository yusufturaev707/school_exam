"""Test settings: real settings plus safe defaults. POSTGRES_* come from `.env`."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-used-anywhere-else-000000")
os.environ.setdefault("JSHSHIR_HASH_KEY", "test-only-jshshir-hash-key")
os.environ["USE_TLS"] = "False"

from .settings import *  # noqa: E402, F403

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
# Connections are opened by worker threads in the concurrency tests and closed there.
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
