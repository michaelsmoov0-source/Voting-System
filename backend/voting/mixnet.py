import json
import random
import threading
from collections import defaultdict
from typing import Dict, List

from django.db import IntegrityError, transaction

from .crypto_utils import decrypt_ballot
from .models import Candidate, Election, Vote

_queue_lock = threading.Lock()
_mix_queue: Dict[int, List[dict]] = defaultdict(list)


def queue_encrypted_vote(*, election: Election, voter_hash: str, encrypted_ballot: str) -> int:
    with _queue_lock:
        _mix_queue[election.id].append(
            {
                "voter_hash": voter_hash,
                "encrypted_ballot": encrypted_ballot,
            }
        )
        return len(_mix_queue[election.id])


def flush_mixed_votes(election_id: int) -> int:
    with _queue_lock:
        batch = _mix_queue[election_id][:]
        _mix_queue[election_id].clear()

    if not batch:
        return 0

    random.SystemRandom().shuffle(batch)

    election = Election.objects.get(id=election_id)
    current_votes = Vote.objects.filter(election=election).count()
    inserted = 0
    for item in batch:
        if election.max_votes is not None and current_votes >= election.max_votes:
            break
        try:
            payload = json.loads(decrypt_ballot(election.private_key_pem, item["encrypted_ballot"]))
            candidate_id = int(payload["candidate_id"])
        except Exception:
            continue

        if not Candidate.objects.filter(id=candidate_id, election=election).exists():
            continue

        try:
            with transaction.atomic():
                Vote.objects.create(
                    election=election,
                    candidate_id=candidate_id,
                    voter_hash=item["voter_hash"],
                    encrypted_ballot=item["encrypted_ballot"],
                )
            inserted += 1
            current_votes += 1
        except IntegrityError:
            continue

    return inserted
