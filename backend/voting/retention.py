from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from .models import Candidate, Election, ElectionResultSnapshot
from .storage import delete_candidate_image_by_url


def purge_expired_candidate_data() -> int:
    retention_days = int(getattr(settings, "CANDIDATE_RETENTION_DAYS", 2))
    cutoff = timezone.now() - timedelta(days=retention_days)

    elections = Election.objects.filter(ends_at__lte=cutoff, candidates_purged_at__isnull=True)
    purged_count = 0

    for election in elections:
        candidates = list(Candidate.objects.filter(election=election).order_by("id"))
        if not candidates:
            election.candidates_purged_at = timezone.now()
            election.save(update_fields=["candidates_purged_at"])
            continue

        vote_counts = (
            election.votes.values("candidate_id")
            .annotate(vote_count=Count("id"))
            .order_by("-vote_count")
        )
        count_map = {row["candidate_id"]: row["vote_count"] for row in vote_counts}
        results = [
            {
                "candidate_id": candidate.id,
                "candidate_name": candidate.full_name,
                "vote_count": count_map.get(candidate.id, 0),
            }
            for candidate in candidates
        ]
        total_votes = sum(item["vote_count"] for item in results)
        ElectionResultSnapshot.objects.update_or_create(
            election=election,
            defaults={"total_votes": total_votes, "results_json": results},
        )

        for candidate in candidates:
            try:
                delete_candidate_image_by_url(candidate.profile_image_url)
            except Exception:
                pass

        Candidate.objects.filter(election=election).delete()
        election.candidates_purged_at = timezone.now()
        election.save(update_fields=["candidates_purged_at"])
        purged_count += 1

    return purged_count
