import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.exams.importer import import_exams_data
from apps.exams.models import (
    AnswerOption,
    AttemptAnswer,
    Exam,
    ExamAttempt,
    ExamResult,
    ExamSection,
    ExamTarget,
    Question,
)

# What goes, in the order it has to go: attempts PROTECT their exam, answers their question.
TABLES = [
    (ExamResult, "results"),
    (AttemptAnswer, "pupils' answers"),
    (ExamAttempt, "attempts"),
    (AnswerOption, "answer options"),
    (Question, "questions"),
    (ExamSection, "sections"),
    (ExamTarget, "targets (Kimga)"),
    (Exam, "exams"),
]


class Command(BaseCommand):
    help = (
        "Deletes every exam with everything that hangs on it (questions, options, sections, "
        "targets, pupils' attempts, answers and results), then loads exams from a JSON file. "
        "One transaction: if the file is broken, nothing is deleted. Pupils, schools and games "
        "are not touched. For getting a test server ready; never run it where real results live."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path, nargs="?", default=Path("content/imtihonlar.json"))
        parser.add_argument("--publish", action="store_true", help="Make them visible to pupils.")
        parser.add_argument(
            "--yes", action="store_true", help="Don't ask for confirmation (for scripts)."
        )

    def handle(self, *args, path: Path, publish: bool, yes: bool, **options):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Could not read {path}: {error}") from error

        counts = [(label, model.objects.count()) for model, label in TABLES]
        self.stdout.write("This deletes:")
        for label, count in counts:
            self.stdout.write(f"  {count:>6}  {label}")
        if not yes:
            answer = input("Type 'yes' to delete them and load the file: ")
            if answer.strip().lower() != "yes":
                raise CommandError("Cancelled. Nothing was changed.")

        try:
            with transaction.atomic():
                for model, _ in TABLES:
                    model.objects.all().delete()
                outcomes = import_exams_data(data, publish=publish, on_existing="copy")
        except ValueError as error:
            raise CommandError(f"Nothing was changed. {error}") from error

        self.stdout.write(self.style.SUCCESS("Deleted the old exams. Loaded:"))
        for outcome in outcomes:
            exam = outcome.exam
            state = "published" if exam.is_published else "not published"
            targets = "; ".join(str(t) for t in exam.targets.all()) or "nobody (choose in Kimga)"
            self.stdout.write(
                f"  '{exam}': {exam.questions.count()} questions, {state}, for {targets}"
            )
