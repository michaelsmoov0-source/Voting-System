from django.core.management.base import BaseCommand

from voting.retention import purge_expired_candidate_data


class Command(BaseCommand):
    help = "Purge candidate data and photos after retention period while keeping election review snapshots."

    def handle(self, *args, **options):
        purged = purge_expired_candidate_data()
        self.stdout.write(self.style.SUCCESS(f"Purged candidate data for {purged} election(s)."))
