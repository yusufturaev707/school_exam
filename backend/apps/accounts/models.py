import hashlib
import hmac

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import UUIDModel
from apps.schools.models import Classroom


def hash_imie(imie: str) -> str:
    """
    IMIE (JSHSHIR) is a child's national id, so the database never stores it in plain text.
    A keyed hash (HMAC) stays deterministic, which is what login needs for an indexed lookup,
    and it can't be brute-forced from a leaked database without JSHSHIR_HASH_KEY.
    """
    key = settings.JSHSHIR_HASH_KEY.encode()
    return hmac.new(key, imie.encode(), hashlib.sha256).hexdigest()


def hash_token(token: str) -> str:
    """QR tokens are long and random, so a plain fast hash is enough here (unlike passwords)."""
    return hashlib.sha256(token.encode()).hexdigest()


class PupilQuerySet(models.QuerySet):
    def active(self):
        """Pupils who may log in: they and every level above them are switched on."""
        return self.filter(
            status=True,
            classroom__status=True,
            classroom__graduated_year__isnull=True,
            classroom__school__status=True,
            classroom__school__district__status=True,
            classroom__school__district__region__status=True,
            # The district is needed to decide which exams the pupil sees (Exam.visible_to).
        ).select_related("classroom__school__district")


class Pupil(UUIDModel):
    """
    A separate model, not `auth.User`: pupils have no password, username or admin rights.
    `auth.User` stays reserved for admin staff, who work only in the Django admin.

    The API contract calls this resource `student` and its login field `jshshir`; both are kept
    there because the frontend depends on them. Inside the backend the words are Pupil and IMIE.
    """

    classroom = models.ForeignKey(
        Classroom, on_delete=models.PROTECT, related_name="pupils", verbose_name="sinf"
    )
    last_name = models.CharField("familiyasi", max_length=100)
    first_name = models.CharField("ismi", max_length=100)
    middle_name = models.CharField("otasining ismi", max_length=100, blank=True)
    imie_hash = models.CharField(max_length=64, unique=True, editable=False)
    photo_url = models.URLField("rasm havolasi", blank=True)
    status = models.BooleanField("faol", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PupilQuerySet.as_manager()

    # DRF's IsAuthenticated permission checks this on whatever is in `request.user`.
    is_authenticated = True

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "O‘quvchi"
        verbose_name_plural = "O‘quvchilar"

    def __str__(self) -> str:
        return " ".join(filter(None, [self.last_name, self.first_name, self.middle_name]))

    def set_imie(self, imie: str) -> None:
        self.imie_hash = hash_imie(imie)


class QrLoginToken(models.Model):
    """A single-use login ticket. Only the hash is stored; the raw token exists on the QR code."""

    pupil = models.ForeignKey(Pupil, on_delete=models.CASCADE, related_name="qr_tokens")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "QR token"
        verbose_name_plural = "QR tokenlar"

    def __str__(self) -> str:
        return f"QR token: {self.pupil}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
