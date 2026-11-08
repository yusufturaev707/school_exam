import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.exams.importer import import_exam_data


class Command(BaseCommand):
    help = "Creates an exam from a JSON file. Format: see apps/demo/data/exam.json."

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path)
        parser.add_argument("--publish", action="store_true", help="Make it visible to pupils.")

    def handle(self, *args, path: Path, publish: bool, **options):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Could not read {path}: {error}") from error

        try:
            exam = import_exam_data(data, publish=publish)
        except ValueError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(f"Created exam '{exam}' with {exam.questions.count()} questions.")
        if exam.targets.exists():
            self.stdout.write("Assigned to: " + "; ".join(str(t) for t in exam.targets.all()))
        else:
            # Targets are chosen in the admin; until then no pupil sees the exam.
            self.stdout.write(
                self.style.WARNING(
                    "No pupil sees it yet: choose who takes it in the admin (Exam -> Kimga)."
                )
            )
