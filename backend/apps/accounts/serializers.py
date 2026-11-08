from rest_framework import serializers

from apps.core.serializers import EmptyAsNullCharField


class JshshirLoginSerializer(serializers.Serializer):
    jshshir = serializers.RegexField(r"^\d{14}$")


class QrLoginSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)


class PupilSerializer(serializers.Serializer):
    """
    The contract's `student` object. Never add IMIE or its hash here: the contract forbids
    sending them to the client.
    """

    id = serializers.CharField()
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    className = EmptyAsNullCharField(source="classroom.name")
    schoolName = EmptyAsNullCharField(source="classroom.school.name")
    photoUrl = EmptyAsNullCharField(source="photo_url")
