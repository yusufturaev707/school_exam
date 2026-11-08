from django.core.management.base import BaseCommand

from apps.exams.services import finalize_overdue_attempts


class Command(BaseCommand):
    help = "Finalises every attempt past its deadline. Run from cron once a minute."

    def handle(self, *args, **options):
        count = finalize_overdue_attempts()
        self.stdout.write(f"Finalised attempts: {count}")
