import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.exams.importer import export_exam_data
from apps.exams.models import Exam


class Command(BaseCommand):
    help = (
        "Writes exams with their sections, questions and options into one JSON file, which "
        "import_exam loads on another server. Only reads the database."
    )

    def add_arguments(self, parser):
        parser.add_argument("--out", type=Path, default=Path("content/imtihonlar.json"))
        parser.add_argument(
            "--title", action="append", default=[], help="Only this exam (may be repeated)."
        )

    def handle(self, *args, out: Path, title: list[str], **options):
        exams = Exam.objects.order_by("created_at")
        if title:
            exams = exams.filter(title__in=title)
            missing = set(title) - set(exams.values_list("title", flat=True))
            if missing:
                raise CommandError("No exam with title: " + ", ".join(sorted(missing)))
        data = [export_exam_data(exam) for exam in exams]
        if not data:
            raise CommandError("There are no exams to export.")

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        questions = sum(len(exam["questions"]) for exam in data)
        self.stdout.write(
            self.style.SUCCESS(f"Wrote {len(data)} exam(s), {questions} questions to {out}.")
        )
