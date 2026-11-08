"""
The school structure: Region -> District -> School -> Classroom. Pupils (apps.accounts) join at the
bottom. Everything here is entered by admin staff through the Django admin.

These tables never reach the client directly, so they use ordinary integer primary keys.
Deleting is PROTECT everywhere: removing a region by mistake must not wipe out pupils and results.
To retire something, turn its `status` off instead.
"""

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

# The last grade of a general school. A class in this grade graduates at the yearly promotion.
FINAL_GRADE = 11


class StatusModel(models.Model):
    # Works downwards: when a school is off, nobody in it can log in (see PupilQuerySet.active).
    status = models.BooleanField("faol", default=True)

    class Meta:
        abstract = True


class Region(StatusModel):
    name = models.CharField("nomi", max_length=100, unique=True)
    number = models.PositiveSmallIntegerField("raqami", unique=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"

    def __str__(self) -> str:
        return self.name


class District(StatusModel):
    region = models.ForeignKey(
        Region, on_delete=models.PROTECT, related_name="districts", verbose_name="viloyat"
    )
    name = models.CharField("nomi", max_length=100)
    number = models.PositiveSmallIntegerField("raqami")

    class Meta:
        ordering = ["region__number", "number"]
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
        constraints = [
            models.UniqueConstraint(fields=["region", "number"], name="unique_district_number"),
            models.UniqueConstraint(fields=["region", "name"], name="unique_district_name"),
        ]

    def __str__(self) -> str:
        return self.name


class School(StatusModel):
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name="schools", verbose_name="tuman"
    )
    name = models.CharField("nomi", max_length=200)
    # Optional, because some specialised schools have only a name.
    number = models.PositiveSmallIntegerField("raqami", null=True, blank=True)
    # Guards the yearly promotion: pressing the button twice must not move children two grades.
    last_promoted_year = models.PositiveSmallIntegerField(
        "keyingi sinfga o‘tkazilgan yil",
        null=True,
        blank=True,
        help_text="O‘quvchilar shu yili keyingi sinfga o‘tkazilgan. Xato bilan o‘tkazilgan bo‘lsa "
        "va qayta o‘tkazish kerak bo‘lsa, maydonni tozalang.",
    )

    class Meta:
        ordering = ["district__region__number", "district__number", "number", "name"]
        verbose_name = "Maktab"
        verbose_name_plural = "Maktablar"
        constraints = [
            models.UniqueConstraint(fields=["district", "number"], name="unique_school_number"),
            models.UniqueConstraint(fields=["district", "name"], name="unique_school_name"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.district})"


class ClassroomQuerySet(models.QuerySet):
    def current(self):
        """Classes that still study here, without the archived classes of past graduates."""
        return self.filter(graduated_year__isnull=True)


class Classroom(StatusModel):
    school = models.ForeignKey(
        School, on_delete=models.PROTECT, related_name="classrooms", verbose_name="maktab"
    )
    number = models.PositiveSmallIntegerField(
        "sinf", validators=[MinValueValidator(1), MaxValueValidator(FINAL_GRADE)]
    )
    # Latin only: a Cyrillic "А" looks like "A" but is another letter, so "5-А" and "5-A" would
    # become two different classes that nobody can tell apart in a list.
    category = models.CharField(
        "harfi",
        max_length=3,
        validators=[RegexValidator(r"^\s*[A-Za-z]{1,3}\s*$", "Lotin harfi bo‘lsin: A, B, V.")],
        help_text="Masalan: A, B, V",
    )
    name = models.CharField(
        "nomi", max_length=50, blank=True, help_text="Bo‘sh qoldirilsa, avtomatik: 5-A"
    )
    count = models.PositiveSmallIntegerField(
        "o‘quvchilar soni (reja)",
        default=0,
        help_text="Sinfda bo‘lishi kerak bo‘lgan o‘quvchilar soni. Ro‘yxatdagi haqiqiy son alohida "
        "ko‘rsatiladi, shu sababli to‘liq kiritilmagan sinflar darhol ko‘rinadi.",
    )
    # Set by the yearly promotion when the class finishes school. The class and its pupils stay
    # for the results history, but they no longer occupy "11-A", so the next 11-A can exist.
    graduated_year = models.PositiveSmallIntegerField("bitirgan yili", null=True, blank=True)

    objects = ClassroomQuerySet.as_manager()

    class Meta:
        ordering = ["number", "category"]
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "number", "category"],
                condition=models.Q(graduated_year__isnull=True),
                name="unique_classroom_in_school",
            ),
        ]

    def __str__(self) -> str:
        graduated = f" ({self.graduated_year} bitiruvchilari)" if self.graduated_year else ""
        # The school's own __str__ adds the district: "12-maktab" exists in every district.
        return f"{self.name}{graduated}, {self.school}"

    def save(self, *args, **kwargs) -> None:
        self.category = self.category.strip().upper()
        if not self.name:
            self.name = f"{self.number}-{self.category}"
        super().save(*args, **kwargs)
