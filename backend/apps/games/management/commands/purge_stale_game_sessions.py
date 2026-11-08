from django.core.management.base import BaseCommand

from apps.games.services import purge_stale_sessions


class Command(BaseCommand):
    help = "Deletes unfinished game sessions older than a day. Run from cron once a day."

    def handle(self, *args, **options):
        self.stdout.write(f"Deleted rows: {purge_stale_sessions()}")
