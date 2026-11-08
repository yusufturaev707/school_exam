from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.models import Pupil, QrLoginToken
from apps.accounts.services import authenticate_by_qr, issue_qr_token

from .conftest import ALIYA_JSHSHIR, client_for

pytestmark = pytest.mark.django_db


def login(client, jshshir=ALIYA_JSHSHIR):
    return client.post("/api/auth/jshshir", {"jshshir": jshshir}, format="json")


def test_login_sets_httponly_cookie_and_never_returns_jshshir(aliya):
    client = client_for()
    response = login(client)

    assert response.status_code == 200
    assert response.json()["student"]["firstName"] == "Aliya"
    assert ALIYA_JSHSHIR not in response.content.decode()
    assert "jshshir" not in response.content.decode().lower()

    cookie = response.cookies["bilimdon_sid"]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    assert client.get("/api/auth/me").json()["student"]["id"] == str(aliya.pk)


def test_jshshir_is_not_stored_in_plain_text(aliya):
    aliya.refresh_from_db()
    assert ALIYA_JSHSHIR not in aliya.imie_hash


def test_login_fails_for_unknown_or_inactive_pupil(aliya):
    response = login(client_for(), "99999999999999")
    assert (response.status_code, response.json()["code"]) == (401, "INVALID_CREDENTIALS")

    Pupil.objects.filter(pk=aliya.pk).update(status=False)
    assert login(client_for()).status_code == 401


def test_malformed_jshshir_is_a_validation_error(aliya):
    response = login(client_for(), "123")
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


def test_me_without_session_is_401():
    response = client_for().get("/api/auth/me")
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


def test_deactivating_a_pupil_ends_their_session(aliya):
    client = client_for(aliya)
    assert client.get("/api/auth/me").status_code == 200
    Pupil.objects.filter(pk=aliya.pk).update(status=False)
    assert client.get("/api/auth/me").status_code == 401


def test_logout_ends_session_and_is_safe_to_repeat(aliya):
    client = client_for(aliya)
    assert client.post("/api/auth/logout").json() == {"ok": True}
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/logout").status_code == 200


def test_mutating_request_without_custom_header_is_rejected(aliya):
    response = APIClient().post("/api/auth/jshshir", {"jshshir": ALIYA_JSHSHIR}, format="json")
    assert (response.status_code, response.json()["code"]) == (403, "CSRF_CHECK_FAILED")


def test_api_responses_are_not_cacheable_and_unknown_routes_are_json(aliya):
    response = client_for(aliya).get("/api/no/such/route")
    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")
    assert response["Cache-Control"] == "no-store"


class TestQr:
    def post(self, token):
        return client_for().post("/api/auth/qr", {"token": token}, format="json")

    def test_token_works_exactly_once(self, aliya):
        token, _ = issue_qr_token(aliya)
        first = self.post(token)
        assert first.status_code == 200
        assert first.json()["student"]["id"] == str(aliya.pk)

        second = self.post(token)
        assert (second.status_code, second.json()["code"]) == (409, "QR_ALREADY_USED")

    def test_consuming_update_has_no_subquery(self, aliya):
        """
        Deterministic guard for the double-use race: PostgreSQL doesn't re-check conditions inside
        a subquery after waiting for a row lock, so the UPDATE must filter on its own columns.
        """
        token, _ = issue_qr_token(aliya)
        with CaptureQueriesContext(connection) as queries:
            authenticate_by_qr(token)
        updates = [q["sql"] for q in queries if q["sql"].startswith("UPDATE")]
        assert len(updates) == 1
        assert "SELECT" not in updates[0]

    def test_inactive_pupil_token_is_invalid_and_not_consumed(self, aliya):
        token, entry = issue_qr_token(aliya)
        Pupil.objects.filter(pk=aliya.pk).update(status=False)
        response = self.post(token)
        assert (response.status_code, response.json()["code"]) == (401, "QR_INVALID")
        entry.refresh_from_db()
        assert entry.used_at is None

    def test_expired_token(self, aliya):
        token, entry = issue_qr_token(aliya)
        QrLoginToken.objects.filter(pk=entry.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = self.post(token)
        assert (response.status_code, response.json()["code"]) == (410, "QR_EXPIRED")

    def test_unknown_token(self):
        response = self.post("this-token-does-not-exist")
        assert (response.status_code, response.json()["code"]) == (401, "QR_INVALID")

    def test_raw_token_is_not_stored(self, aliya):
        token, entry = issue_qr_token(aliya)
        assert token != entry.token_hash
        assert len(token) >= 32  # at least 128 bits, as the contract requires


class TestRateLimit:
    def test_one_identifier_is_limited_strictly(self, aliya):
        for _ in range(10):
            assert login(client_for(), "99999999999999").status_code == 401
        response = login(client_for(), "99999999999999")
        assert (response.status_code, response.json()["code"]) == (429, "RATE_LIMITED")
        assert "Retry-After" in response

        # Another pupil behind the same school IP can still log in.
        assert login(client_for()).status_code == 200

    def test_ip_limit_applies_across_identifiers(self, aliya, monkeypatch):
        monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "login_ip", "3/min")
        for number in range(3):
            assert login(client_for(), f"9999999999999{number}").status_code == 401
        assert login(client_for(), "99999999999993").status_code == 429
