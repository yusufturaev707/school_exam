import uuid

from django.db import models


class UUIDModel(models.Model):
    """
    Base for anything whose id reaches the client. Random UUIDs cannot be enumerated, so a pupil
    cannot walk through /results/1, /results/2. Ownership is still always checked on top of this.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
