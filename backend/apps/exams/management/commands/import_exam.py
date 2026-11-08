import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.exams.importer import import_exams_data


class Command(BaseCommand):
    help = (
        "Loads exams from a JSON file: one exam ({...}, format: apps/demo/data/exam.json) or "
        "several ([{...}, ...], as export_exams writes). An exam whose title is already in the "
        "database is skipped by default, so running the command twice is safe; --update brings "
        "it in line with the file instead."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path)
        parser.add_argument("--publish", action="store_true", help="Make them visible to pupils.")
        existing = parser.add_mutually_exclusive_group()
        existing.add_argument(
            "--update",
            action="store_true",
            help="Update an exam with the same title in place: questions by number, options by "
            "letter. Pupils' answers and results stay valid.",
        )
        existing.add_argument(
            "--force",
            action="store_true",
            help="Create another exam even if one with the same title exists.",
        )

    def handle(self, *args, path: Path, publish: bool, update: bool, force: bool, **options):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Could not read {path}: {error}") from error

        on_existing = "update" if update else "copy" if force else "skip"
        try:
            outcomes = import_exams_data(data, publish=publish, on_existing=on_existing)
        except ValueError as error:
            raise CommandError(f"Nothing was saved. {error}") from error

        for outcome in outcomes:
            if outcome.action == "skipped":
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped '{outcome.title}': an exam with this title already exists. "
                        "Use --update to update it from the file (or --force for a copy)."
                    )
                )
                continue
            exam = outcome.exam
            state = "published" if exam.is_published else "not published"
            if outcome.action == "updated":
                counts = outcome.counts
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated exam '{exam}' ({state}): {counts['changed']} questions changed, "
                        f"{counts['added']} added, {counts['removed']} removed, "
                        f"{counts['unchanged']} unchanged."
                    )
                )
            else:
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
