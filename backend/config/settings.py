"""
Single, environment-driven settings module (12-factor).

There is deliberately no base/dev/prod split: every difference between environments is an
env variable, so there is one place to read. See `.env.example` for the full list.
"""

import re
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

# No defaults on purpose: a forgotten secret must fail at startup, not run insecurely.
SECRET_KEY = env("DJANGO_SECRET_KEY")
JSHSHIR_HASH_KEY = env("JSHSHIR_HASH_KEY")

DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_ckeditor_5",
    "apps.core",
    "apps.schools",
    "apps.accounts",
    "apps.exams",
    "apps.games",
    "apps.demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.ApiGuardMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
# The API contract has no trailing slashes; redirecting a PUT/POST would lose its body.
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Searched before the apps, so templates/admin/base_site.html replaces Django's own.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
        # Ulanish 60 soniya ochiq turadi -- har so'rovda qaytadan ulanmaydi.
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login throttling needs a cache shared by all workers. Without REDIS_URL each process counts
# separately, which is fine for `runserver` but not for several gunicorn workers.
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "uz"
# Admin screens and the "daily" calendar day use Tashkent time. The API itself always returns UTC.
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Images uploaded through the question editor.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# --------------------------------------------------------------------------- student session
# Contract: an HttpOnly cookie owned by the backend. Django's session framework already does
# this well, so we use it directly instead of inventing tokens or adding JWT.
SESSION_COOKIE_NAME = "bilimdon_sid"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# --------------------------------------------------------------------------- HTTPS
USE_TLS = env.bool("USE_TLS", default=not DEBUG)
SESSION_COOKIE_SECURE = USE_TLS
CSRF_COOKIE_SECURE = USE_TLS
SECURE_SSL_REDIRECT = USE_TLS
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if USE_TLS else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = USE_TLS
SECURE_HSTS_PRELOAD = USE_TLS

# How many trusted reverse proxies sit in front of Django. 0 means X-Forwarded-For is ignored,
# because any client can forge it, and a forged IP would bypass login rate limiting.
NUM_PROXIES = env.int("NUM_PROXIES", default=0)
if NUM_PROXIES > 0:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --------------------------------------------------------------------------- DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.authentication.PupilSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "UNAUTHENTICATED_USER": None,
    "NUM_PROXIES": NUM_PROXIES,
    "DEFAULT_THROTTLE_RATES": {
        # A whole school shares one public IP, and a class logs in during the same minute.
        # So the per-IP limit stays generous and the strict limit is per identifier.
        "login_ip": env("THROTTLE_LOGIN_IP", default="300/min"),
        "login_identifier": env("THROTTLE_LOGIN_IDENTIFIER", default="10/min"),
    },
}

# --------------------------------------------------------------------------- domain
# After the deadline, answers that were still in flight are accepted through submit for this long.
EXAM_GRACE_SECONDS = env.int("EXAM_GRACE_SECONDS", default=30)
QR_TOKEN_TTL_MINUTES = env.int("QR_TOKEN_TTL_MINUTES", default=5)
# The pupil app's /qr page. Ticket QR codes hold this address with the token after "#"
# (https://bilimdon.uz/qr#t=...), so a phone camera opens it and logs the pupil in. The part after
# "#" is never sent to any server, so the token stays out of logs. Empty: the code holds the bare
# token, which only the scanner inside the app can read.
QR_LOGIN_URL = env("QR_LOGIN_URL", default="http://localhost:5173/qr" if DEBUG else "")
if QR_LOGIN_URL and not re.fullmatch(r"https?://[^\s?#]+", QR_LOGIN_URL):
    raise ImproperlyConfigured(
        "QR_LOGIN_URL must be an http(s) address without ? or #, e.g. https://bilimdon.uz/qr"
    )

# --------------------------------------------------------------------------- question editor
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"
CKEDITOR_5_UPLOAD_FILE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]  # no SVG: it can carry scripts
CKEDITOR_5_MAX_FILE_SIZE = 5  # megabytes
CKEDITOR_5_CONFIGS = {
    "default": {
        "language": "uz",
        # These rewrite text while typing (1/2 becomes ½, -- becomes –, _x_ becomes italic), which
        # would silently corrupt LaTeX formulas. Link and MediaEmbed have no place in an exam.
        "removePlugins": ["Autoformat", "TextTransformation", "Link", "AutoLink", "MediaEmbed"],
        "toolbar": {
            "items": [
                "heading",
                "|",
                "bold",
                "italic",
                "underline",
                "subscript",
                "superscript",
                "|",
                "bulletedList",
                "numberedList",
                "blockQuote",
                "|",
                "insertTable",
                "insertImage",
                "|",
                "undo",
                "redo",
            ]
        },
        "heading": {
            "options": [
                {"model": "paragraph", "title": "Matn", "class": "ck-heading_paragraph"},
                {
                    "model": "heading3",
                    "view": "h3",
                    "title": "Sarlavha",
                    "class": "ck-heading_heading3",
                },
            ]
        },
        "image": {"toolbar": ["imageTextAlternative"]},
        "table": {"contentToolbar": ["tableColumn", "tableRow", "mergeTableCells"]},
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
