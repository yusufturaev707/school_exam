import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.exams.importer import import_exams_data
from apps.exams.models import Exam


class Command(BaseCommand):
    help = (
        "Creates exams from a JSON file: one exam ({...}, format: apps/demo/data/exam.json) or "
        "several ([{...}, ...], as export_exams writes). An exam whose title is already in the "
        "database is skipped, so running the command twice is safe."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path)
        parser.add_argument("--publish", action="store_true", help="Make them visible to pupils.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create the exam even if one with the same title exists.",
        )

    def handle(self, *args, path: Path, publish: bool, force: bool, **options):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Could not read {path}: {error}") from error

        existing = set() if force else set(Exam.objects.values_list("title", flat=True))
        try:
            created, skipped = import_exams_data(data, publish=publish, skip_titles=existing)
        except ValueError as error:
            raise CommandError(f"Nothing was saved. {error}") from error

        for title in skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped '{title}': an exam with this title already exists "
                    "(use --force to create a copy)."
                )
            )
        for exam in created:
            state = "published" if exam.is_published else "not published"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created exam '{exam}' with {exam.questions.count()} questions ({state})."
                )
            )
            if exam.targets.exists():
                self.stdout.write("  Assigned to: " + "; ".join(str(t) for t in exam.targets.all()))
            else:
                # Targets are chosen in the admin; until then no pupil sees the exam.
                self.stdout.write(
                    self.style.WARNING(
                        "  No pupil sees it yet: choose who takes it in the admin (Exam -> Kimga)."
                    )
                )
