import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.core.exceptions import ApiError

from .authentication import SESSION_PUPIL_KEY
from .models import Pupil, QrLoginToken, hash_imie, hash_token


def authenticate_by_jshshir(jshshir: str) -> Pupil:
    pupil = Pupil.objects.active().filter(imie_hash=hash_imie(jshshir)).first()
    if pupil is None:
        raise ApiError(401, "INVALID_CREDENTIALS")
    return pupil


def authenticate_by_qr(token: str) -> Pupil:
    now = timezone.now()
    entry = QrLoginToken.objects.filter(token_hash=hash_token(token)).first()
    pupil = Pupil.objects.active().filter(pk=entry.pupil_id).first() if entry else None
    if pupil is None:
        raise ApiError(401, "QR_INVALID")

    # A conditional UPDATE lets exactly one of several simultaneous scans change the row. Its filter
    # must stay on this table's own columns: a join (e.g. pupil__status) makes Django generate
    # `WHERE id IN (SELECT ...)`, and after waiting for the row lock PostgreSQL does not re-check
    # the conditions inside that subquery, so every waiting request would consume the token too.
    consumed = QrLoginToken.objects.filter(
        pk=entry.pk, used_at__isnull=True, expires_at__gt=now
    ).update(used_at=now)
    if consumed:
        return pupil

    entry.refresh_from_db(fields=["used_at"])  # the first read may predate a parallel scan
    if entry.used_at is not None:
        raise ApiError(409, "QR_ALREADY_USED")
    raise ApiError(410, "QR_EXPIRED")


def issue_qr_token(pupil: Pupil, ttl_minutes: int | None = None) -> tuple[str, QrLoginToken]:
    """Returns the raw token. This is the only moment it is available; it can't be recovered."""
    ttl = ttl_minutes if ttl_minutes is not None else settings.QR_TOKEN_TTL_MINUTES
    raw_token = secrets.token_urlsafe(24)  # 192 bits of randomness
    entry = QrLoginToken.objects.create(
        pupil=pupil,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=ttl),
    )
    return raw_token, entry


def issue_qr_tokens(pupils, ttl_minutes: int) -> list[tuple[Pupil, str, QrLoginToken]]:
    """Many tickets at once, in one INSERT. Raw tokens live only in the returned list."""
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    issued = [(pupil, secrets.token_urlsafe(24)) for pupil in pupils]
    entries = QrLoginToken.objects.bulk_create(
        QrLoginToken(pupil=pupil, token_hash=hash_token(raw), expires_at=expires_at)
        for pupil, raw in issued
    )
    return [(pupil, raw, entry) for (pupil, raw), entry in zip(issued, entries, strict=True)]


def qr_payload(raw_token: str) -> str:
    """What a ticket's QR code holds: the app's /qr link with the token after "#", or the token."""
    if settings.QR_LOGIN_URL:
        return f"{settings.QR_LOGIN_URL}#t={raw_token}"
    return raw_token


def start_session(request, pupil: Pupil) -> None:
    # A new session key on login prevents session fixation.
    request.session.cycle_key()
    request.session[SESSION_PUPIL_KEY] = str(pupil.pk)


def end_session(request) -> None:
    request.session.flush()  # the session middleware then clears the cookie too
