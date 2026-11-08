import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginIpThrottle(SimpleRateThrottle):
    """Slows down one machine guessing many identifiers. See the rate comment in settings."""

    scope = "login_ip"

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginIdentifierThrottle(SimpleRateThrottle):
    """Slows down guessing against one identifier, even from many IP addresses."""

    scope = "login_identifier"

    def get_cache_key(self, request, view) -> str | None:
        data = request.data if isinstance(request.data, dict) else {}
        identifier = data.get("jshshir") or data.get("token")
        if not isinstance(identifier, str):
            return None  # malformed body: the serializer will reject it, nothing to count
        # Hashed so that a JSHSHIR never ends up in cache keys, Redis dumps or logs.
        digest = hashlib.sha256(identifier.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}
