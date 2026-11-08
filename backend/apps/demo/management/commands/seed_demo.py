"""
Fills a development database with the same demo data the frontend's mock backend has, so the two
are interchangeable. Refuses to run outside DEBUG: these pupils have well-known JSHSHIRs.
"""

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Pupil, QrLoginToken, hash_imie, hash_token
from apps.exams.importer import import_exam_data
from apps.exams.models import AttemptAnswer, Exam, ExamAttempt, ExamTarget
from apps.exams.services import submit_attempt
from apps.games.models import DailyChallengeCompletion, DailyQuestionAnswer, Game, GameSession
from apps.games.services import answer_question, complete_game, start_game
from apps.schools.models import Classroom, District, Region, School

DEMO_EXAM_FILE = Path(__file__).resolve().parents[2] / "data" / "exam.json"

# IMIE, first name, last name, middle name, school number, class number, class letter
PUPILS = [
    ("12345678901234", "Aziz", "Karimov", "Rustamovich", 12, 6, "B"),
    ("23456789012345", "Malika", "Yusupova", "Akmalovna", 7, 5, "A"),
    ("34567890123456", "Bobur", "Aliyev", "Shavkatovich", 12, 7, "V"),
]
AZIZ, _MALIKA, BOBUR = (row[0] for row in PUPILS)

QR_VALID = "demo-qr-valid-7f3a9c2e1b4d"
QR_EXPIRED = "demo-qr-expired-0c8e2a9f71"
QR_USED = "demo-qr-used-5b1d7e3c9a20"


class Command(BaseCommand):
    help = "Creates demo pupils, the demo exam, QR tokens and some history (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete demo pupils' data and start over."
        )

    def handle(self, *args, reset: bool, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DJANGO_DEBUG=True.")

        with transaction.atomic():
            if reset:
                self._reset()
            exam = self._exam()
            pupils = {row[0]: self._pupil(*row) for row in PUPILS}
            # Every demo pupil studies in this region, so all of them see the exam.
            ExamTarget.objects.get_or_create(exam=exam, region=self._region())
            self._qr_tokens(pupils[AZIZ])
            if not ExamAttempt.objects.filter(pupil=pupils[BOBUR], exam=exam).exists():
                self._finished_exam(pupils[BOBUR], exam)
                self._game_history(pupils[BOBUR])

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("JSHSHIR: " + ", ".join(row[0] for row in PUPILS))
        self.stdout.write(f"QR: {QR_VALID} (single-use), {QR_EXPIRED}, {QR_USED}")

    def _reset(self) -> None:
        hashes = [hash_imie(row[0]) for row in PUPILS]
        demo_pupils = Pupil.objects.filter(imie_hash__in=hashes)
        # Exam attempts are protected from deletion, so they have to go before the pupils do.
        ExamAttempt.objects.filter(pupil__in=demo_pupils).delete()
        DailyChallengeCompletion.objects.filter(pupil__in=demo_pupils).delete()
        DailyQuestionAnswer.objects.filter(pupil__in=demo_pupils).delete()
        demo_pupils.delete()

    def _exam(self) -> Exam:
        data = json.loads(DEMO_EXAM_FILE.read_text(encoding="utf-8"))
        existing = Exam.objects.filter(title=data["title"]).first()
        return existing or import_exam_data(data, publish=True)

    def _pupil(self, imie, first_name, last_name, middle_name, school_no, class_no, letter):
        pupil, _ = Pupil.objects.update_or_create(
            imie_hash=hash_imie(imie),
            defaults={
                "classroom": self._classroom(school_no, class_no, letter),
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
                "status": True,
            },
        )
        return pupil

    def _region(self) -> Region:
        region, _ = Region.objects.get_or_create(number=26, defaults={"name": "Toshkent shahri"})
        return region

    def _classroom(self, school_no: int, class_no: int, letter: str) -> Classroom:
        district, _ = District.objects.get_or_create(
            region=self._region(), number=1, defaults={"name": "Chilonzor tumani"}
        )
        school, _ = School.objects.get_or_create(
            district=district, number=school_no, defaults={"name": f"{school_no}-maktab"}
        )
        classroom, _ = Classroom.objects.get_or_create(
            school=school, number=class_no, category=letter, defaults={"count": 25}
        )
        return classroom

    def _qr_tokens(self, pupil: Pupil) -> None:
        now = timezone.now()
        long_from_now = now + timedelta(days=365)
        tokens = [
            (QR_VALID, long_from_now, None),
            (QR_EXPIRED, now - timedelta(minutes=1), None),
            (QR_USED, long_from_now, now - timedelta(hours=1)),
        ]
        for token, expires_at, used_at in tokens:
            QrLoginToken.objects.update_or_create(
                token_hash=hash_token(token),
                defaults={"pupil": pupil, "expires_at": expires_at, "used_at": used_at},
            )

    def _finished_exam(self, pupil: Pupil, exam: Exam) -> None:
        """Bobur finished yesterday: mostly right, some wrong, some blank, like a real child."""
        started = timezone.now() - timedelta(days=1)
        attempt = ExamAttempt.objects.create(
            pupil=pupil,
            exam=exam,
            started_at=started,
            expires_at=started + timedelta(minutes=exam.duration_minutes),
        )
        for index, question in enumerate(exam.questions.prefetch_related("options")):
            if index % 7 == 6:
                continue
            options = list(question.options.all())
            right = next(option for option in options if option.is_correct)
            wrong = next(option for option in options if not option.is_correct)
            chosen = wrong if index % 4 == 3 else right
            AttemptAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_option_ids=[str(chosen.pk)],
                client_seq=index + 1,
            )
        submit_attempt(pupil, attempt.pk, "manual", [])

    def _game_history(self, pupil: Pupil) -> None:
        self._play_memory(pupil, "xotira-kartalari", days_ago=2)
        self._play_quiz(pupil, "yashiringan-son", days_ago=1)

    def _play_memory(self, pupil: Pupil, slug: str, days_ago: int) -> None:
        session = start_game(pupil, Game.objects.get(slug=slug).pk, "easy", False)
        by_face: dict[str, list[str]] = {}
        for card in session.content["cards"]:
            by_face.setdefault(card["face"], []).append(card["id"])
        pairs = list(by_face.values())
        # One miss first, then every pair: a realistic, valid move log.
        moves = [[pairs[0][0], pairs[1][0]], *pairs]
        complete_game(pupil, session.pk, moves)
        self._move_to_past(session, days_ago)

    def _play_quiz(self, pupil: Pupil, slug: str, days_ago: int) -> None:
        session = start_game(pupil, Game.objects.get(slug=slug).pk, "easy", False)
        questions = session.content["questions"]
        for index, question in enumerate(questions):
            correct_id = question["correct_option_id"]
            wrong_id = next(o["id"] for o in question["options"] if o["id"] != correct_id)
            chosen = correct_id if index < len(questions) * 0.75 else wrong_id
            answer_question(pupil, session.pk, question["id"], chosen)
        complete_game(pupil, session.pk, None)
        self._move_to_past(session, days_ago)

    def _move_to_past(self, session: GameSession, days_ago: int) -> None:
        started = timezone.now() - timedelta(days=days_ago)
        GameSession.objects.filter(pk=session.pk).update(
            started_at=started, completed_at=started + timedelta(seconds=95)
        )
