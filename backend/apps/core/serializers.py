"""
Convention for all apps: Python code is snake_case, the JSON contract is camelCase, and serializers
are the only place where the two meet. Field names are written literally (`firstName`), so you can
grep the same word in the frontend's zod schema and here, with no renaming magic in between.

Output serializers are also a whitelist: a field that is not declared cannot leak to the client.
"""

from datetime import UTC, datetime

from rest_framework import serializers


def iso_utc(value: datetime) -> str:
    """Same format as JavaScript's `toISOString()`, e.g. `2026-11-06T12:00:00.000Z`."""
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class UtcDateTimeField(serializers.ReadOnlyField):
    def to_representation(self, value: datetime) -> str:
        return iso_utc(value)


class EmptyAsNullCharField(serializers.ReadOnlyField):
    """Django text columns store "missing" as an empty string; the contract expects null."""

    def to_representation(self, value: str) -> str | None:
        return value or None


class RichContentField(serializers.ReadOnlyField):
    """
    Sends stored editor HTML as the contract's content blocks: `[{"type": "html", "html": ...}]`.
    The HTML was cleaned when it was saved (see apps/core/richtext.py). An empty value becomes `[]`,
    or null with `nullable=True`, for optional texts that the frontend hides when absent.
    """

    def __init__(self, nullable: bool = False, **kwargs):
        self.nullable = nullable
        super().__init__(**kwargs)

    def to_representation(self, value: str) -> list[dict] | None:
        if value:
            return [{"type": "html", "html": value}]
        return None if self.nullable else []


def parse_body(serializer_class: type[serializers.Serializer], request) -> dict:
    """Validates the request body and returns clean data. Invalid input becomes a 422 response."""
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
