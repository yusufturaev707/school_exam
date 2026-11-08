from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.accounts.models import Pupil
from apps.core.models import UUIDModel
from apps.core.richtext import RichTextField
from apps.schools.models import FINAL_GRADE, Classroom, District, Region, School


class Subject(models.TextChoices):
    MATH = "math", "Matematika"
    IQ = "iq", "Mantiq (IQ)"
    LANGUAGE = "language", "Ingliz tili"


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = "single_choice", "Bitta javobli"


class Difficulty(models.IntegerChoices):
    EASY = 1, "Oson"
    MEDIUM = 2, "O‘rta"
    HARD = 3, "Qiyin"


FORMULA_HELP = r"Formulani $ belgilari orasida yozing: $\frac{1}{2} + x^2$"


class ExamQuerySet(models.QuerySet):
    def visible_to(self, pupil: Pupil):
        """
        Published exams that one of the exam's targets assigns to this pupil. An exam the pupil
        has already started stays visible even if the targets change later or the pupil moves to
        another class, so a finished exam never disappears from their results.
        """
        classroom = pupil.classroom
        school = classroom.school
        assigned = ExamTarget.objects.filter(
            # Within one target, every field that is filled in must match.
            Q(region__isnull=True) | Q(region_id=school.district.region_id),
            Q(district__isnull=True) | Q(district_id=school.district_id),
            Q(school__isnull=True) | Q(school_id=school.pk),
            Q(classroom__isnull=True) | Q(classroom_id=classroom.pk),
            Q(grade__isnull=True) | Q(grade=classroom.number),
            exam=OuterRef("pk"),
        )
        started = ExamAttempt.objects.filter(exam=OuterRef("pk"), pupil=pupil)
        return self.filter(Exists(assigned) | Exists(started), is_published=True)


class Exam(UUIDModel):
    title = models.CharField("nomi", max_length=200)
    description = models.TextField("tavsifi", blank=True)
    duration_minutes = models.PositiveSmallIntegerField(
        "davomiyligi (daqiqa)", validators=[MinValueValidator(1)]
    )
    points_per_question = models.PositiveSmallIntegerField(
        "bir savol balli", default=2, validators=[MinValueValidator(1)]
    )
    review_enabled = models.BooleanField(
        "javoblarni ko‘rsatish",
        default=True,
        help_text="O‘quvchi natijada to‘g‘ri javoblar va izohlarni ko‘radimi.",
    )
    shuffle_questions = models.BooleanField(
        "savollar tartibini aralashtirish",
        default=False,
        help_text="Har bir o‘quvchiga savollar boshqa tartibda tushadi. Fanlar tartibi saqlanadi, "
        "fan ichida esa savollar qiyinlik darajasi bo‘yicha (osondan qiyinga) guruhlanib, har bir "
        "guruh ichida aralashtiriladi.",
    )
    shuffle_options = models.BooleanField(
        "javob variantlarini aralashtirish",
        default=False,
        help_text="Har bir o‘quvchiga variantlar boshqa tartibda va boshqa harflar bilan tushadi, "
        "shuning uchun javob kaliti ham har kimda har xil bo‘ladi.",
    )
    is_published = models.BooleanField("e’lon qilingan", default=False)
    available_from = models.DateTimeField("ochilish vaqti", null=True, blank=True)
    available_until = models.DateTimeField("yopilish vaqti", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ExamQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Imtihon"
        verbose_name_plural = "Imtihonlar"

    def __str__(self) -> str:
        return self.title

    def is_open(self, now: datetime) -> bool:
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False
        return True


class ExamTarget(models.Model):
    """
    Who takes an exam. A pupil sees the exam if at least one of its targets matches them.

    One target is one place (a region, a district, a school or a class), a grade (every 9th
    grade), or both (every 9th grade in one district). An exam without targets is seen by nobody:
    forgetting this step hides an exam, instead of showing it to every child in the country.

    Admins naturally fill a row top-down (region, then district, then school). That's accepted
    when the levels agree, and only the lowest one is stored: it already implies the others, and a
    stored copy of them could go stale if a school later moves to another district.
    """

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="targets", verbose_name="imtihon"
    )
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, null=True, blank=True, verbose_name="viloyat"
    )
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, null=True, blank=True, verbose_name="tuman"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, null=True, blank=True, verbose_name="maktab"
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, null=True, blank=True, verbose_name="sinf"
    )
    grade = models.PositiveSmallIntegerField(
        "sinf raqami",
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(FINAL_GRADE)],
        help_text="Masalan 9: tanlangan joydagi barcha 9-sinflar.",
    )

    PLACES = ("region", "district", "school", "classroom")  # from the widest to the narrowest
    # "Not in the chosen district" etc., for the mismatch error.
    PLACE_IN = {"region": "viloyatda", "district": "tumanda", "school": "maktabda"}

    class Meta:
        verbose_name = "Kimga"
        verbose_name_plural = "Kimga (imtihon kimlarga ko‘rinadi)"
        constraints = [
            # An empty target would mean "everyone" to one reader and "no one" to another.
            models.CheckConstraint(
                condition=Q(region__isnull=False)
                | Q(district__isnull=False)
                | Q(school__isnull=False)
                | Q(classroom__isnull=False)
                | Q(grade__isnull=False),
                name="exam_target_not_empty",
            )
        ]

    def __str__(self) -> str:
        filled = [name for name in self.PLACES if getattr(self, f"{name}_id")]
        place = getattr(self, filled[0]) if filled else None
        grade = f"{self.grade}-sinflar" if self.grade else ""
        if place is None:
            return f"Barcha {grade}"
        return f"{place}, {grade}" if grade else str(place)

    def _parents_of(self, level: str) -> dict[str, int]:
        """The ids of the wider places that contain the chosen place at `level`."""
        if level == "classroom":
            school = self.classroom.school
            district = school.district
            return {"school": school.pk, "district": district.pk, "region": district.region_id}
        if level == "school":
            return {"district": self.school.district_id, "region": self.school.district.region_id}
        if level == "district":
            return {"region": self.district.region_id}
        return {}

    def clean(self) -> None:
        places = [name for name in self.PLACES if getattr(self, f"{name}_id")]
        if not places and self.grade is None:
            raise ValidationError(
                "Joyni (viloyat, tuman, maktab, sinf) yoki sinf raqamini tanlang."
            )
        if self.classroom_id and self.grade is not None:
            raise ValidationError({"grade": "Sinf tanlanganda sinf raqami kerak emas."})
        if len(places) > 1:
            narrowest = places[-1]
            parents = self._parents_of(narrowest)
            errors = {
                name: f"{getattr(self, narrowest)} tanlangan {self.PLACE_IN[name]} emas."
                for name in places[:-1]
                if getattr(self, f"{name}_id") != parents[name]
            }
            if errors:
                raise ValidationError(errors)
            for name in places[:-1]:
                setattr(self, name, None)


class ExamSection(models.Model):
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="sections", verbose_name="imtihon"
    )
    subject = models.CharField("fan", max_length=20, choices=Subject.choices)
    title = models.CharField("nomi", max_length=100)
    order = models.PositiveSmallIntegerField("tartibi", default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Bo‘lim"
        verbose_name_plural = "Bo‘limlar"
        constraints = [
            models.UniqueConstraint(fields=["exam", "subject"], name="unique_section_per_subject")
        ]

    def __str__(self) -> str:
        return self.title


class Question(UUIDModel):
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="questions", verbose_name="imtihon"
    )
    number = models.PositiveSmallIntegerField("raqami")
    subject = models.CharField("fan", max_length=20, choices=Subject.choices)
    type = models.CharField(
        "turi", max_length=20, choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE
    )
    difficulty = models.PositiveSmallIntegerField(
        "qiyinlik darajasi",
        choices=Difficulty.choices,
        null=True,
        blank=True,
        help_text="Aralashtirishda savollar shu daraja ichida aralashtiriladi.",
    )
    prompt = RichTextField("savol matni", help_text=FORMULA_HELP)
    passage = RichTextField("o‘qish uchun matn", blank=True, help_text="Savolga oid uzun matn.")
    explanation = RichTextField("izoh", blank=True, help_text="Natija sahifasida ko‘rsatiladi.")

    class Meta:
        ordering = ["number"]
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        constraints = [
            models.UniqueConstraint(fields=["exam", "number"], name="unique_question_number")
        ]

    def __str__(self) -> str:
        return f"#{self.number} ({self.subject})"


class AnswerOption(UUIDModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    label = models.CharField("harfi", max_length=5)
    content = RichTextField("javob matni")
    is_correct = models.BooleanField("to‘g‘ri javob", default=False)

    class Meta:
        ordering = ["label"]
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"
        constraints = [
            models.UniqueConstraint(fields=["question", "label"], name="unique_option_label")
        ]

    def __str__(self) -> str:
        return self.label


class ExamAttempt(UUIDModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Davom etmoqda"
        SUBMITTED = "submitted", "Topshirilgan"
        EXPIRED = "expired", "Vaqti tugagan"

    # PROTECT: an exam record is an official result; it must not vanish with an accidental delete.
    pupil = models.ForeignKey(Pupil, on_delete=models.PROTECT, related_name="exam_attempts")
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="attempts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    # This pupil's own order, fixed when the attempt starts (apps/exams/layout.py):
    # {"questions": [question id, ...], "options": {question id: [option id, ...]}}.
    # Empty for an exam without shuffling. Stored rather than recomputed, so the order a pupil saw
    # and their answer key stay the same even if the exam is edited afterwards.
    layout = models.JSONField(default=dict, blank=True, editable=False)

    class Meta:
        verbose_name = "Urinish"
        verbose_name_plural = "Urinishlar"
        constraints = [
            # One attempt per exam, enforced by the database so even parallel requests can't
            # create a second one. For a retake, see the `allow_retake` admin action.
            models.UniqueConstraint(fields=["pupil", "exam"], name="one_attempt_per_exam")
        ]
        indexes = [
            # Keeps the deadline job fast: it only ever looks at unfinished attempts.
            models.Index(
                fields=["expires_at"],
                condition=models.Q(status="in_progress"),
                name="attempt_open_deadline_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.pupil} / {self.exam}"

    @property
    def result_id(self):
        result = getattr(self, "result", None)
        return result.pk if result else None

    @property
    def submit_deadline(self) -> datetime:
        """After this moment nothing from the client is accepted any more."""
        return self.expires_at + timedelta(seconds=settings.EXAM_GRACE_SECONDS)

    def accepts_answers(self) -> bool:
        return self.status == self.Status.IN_PROGRESS and timezone.now() <= self.expires_at


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="answers")
    # PROTECT: a question that has been answered can't be deleted out from under a result.
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="+")
    # A list so multiple-choice questions can be added later without a schema change.
    selected_option_ids = models.JSONField(default=list)
    # BigInteger because the frontend uses wall-clock milliseconds, which overflow a 32-bit int.
    client_seq = models.BigIntegerField()
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "O‘quvchi javobi"
        verbose_name_plural = "O‘quvchi javoblari"
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="one_answer_per_question")
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id} / {self.question_id}"


class ExamResult(UUIDModel):
    """
    A snapshot of the score, computed once when the attempt is finalised. If someone later corrects
    a question in the admin, the results pupils have already received don't change by themselves.
    """

    class FinishReason(models.TextChoices):
        MANUAL = "manual", "O‘quvchi yakunladi"
        TIMEOUT = "timeout", "Vaqt tugadi"

    attempt = models.OneToOneField(ExamAttempt, on_delete=models.CASCADE, related_name="result")
    finish_reason = models.CharField(max_length=10, choices=FinishReason.choices)
    completed_at = models.DateTimeField()
    correct = models.PositiveSmallIntegerField()
    incorrect = models.PositiveSmallIntegerField()
    unanswered = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    score = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField()
    percent = models.FloatField()
    # [{"subject", "correct", "incorrect", "unanswered", "total", "percent"}, ...]
    subjects = models.JSONField()

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = "Natija"
        verbose_name_plural = "Natijalar"

    def __str__(self) -> str:
        return f"{self.attempt}: {self.correct}/{self.total}"
