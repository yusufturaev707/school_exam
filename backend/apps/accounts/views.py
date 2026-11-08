from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import parse_body

from . import services
from .serializers import JshshirLoginSerializer, PupilSerializer, QrLoginSerializer
from .throttles import LoginIdentifierThrottle, LoginIpThrottle


class _PublicAuthView(APIView):
    # No authentication here: a stale session cookie must not get in the way of logging in again.
    authentication_classes = []
    permission_classes = [AllowAny]


class _LoginView(_PublicAuthView):
    throttle_classes = [LoginIpThrottle, LoginIdentifierThrottle]

    def _logged_in(self, request, pupil) -> Response:
        services.start_session(request, pupil)
        return Response({"student": PupilSerializer(pupil).data})


class JshshirLoginView(_LoginView):
    def post(self, request):
        data = parse_body(JshshirLoginSerializer, request)
        return self._logged_in(request, services.authenticate_by_jshshir(data["jshshir"]))


class QrLoginView(_LoginView):
    def post(self, request):
        data = parse_body(QrLoginSerializer, request)
        return self._logged_in(request, services.authenticate_by_qr(data["token"]))


class LogoutView(_PublicAuthView):
    def post(self, request):
        services.end_session(request)
        return Response({"ok": True})


class MeView(APIView):
    def get(self, request):
        return Response({"student": PupilSerializer(request.user).data})
