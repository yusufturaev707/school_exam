from rest_framework.authentication import BaseAuthentication

from .models import Pupil

SESSION_PUPIL_KEY = "pupil_id"


class PupilSessionAuthentication(BaseAuthentication):
    """Puts the logged-in `Pupil` into `request.user`. Applied to every view by default."""

    def authenticate(self, request):
        pupil_id = request.session.get(SESSION_PUPIL_KEY)
        if not pupil_id:
            return None
        # Checked on every request, so switching off a pupil, class or school takes effect at once.
        pupil = Pupil.objects.active().filter(pk=pupil_id).first()
        return (pupil, None) if pupil else None

    def authenticate_header(self, request) -> str:
        # Having a value here is what makes DRF answer 401 instead of 403 for anonymous requests.
        return "Session"
