import hashlib
import json
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .crypto_utils import generate_rsa_keypair_pem


class Election(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("closed", "Closed"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    max_votes = models.PositiveIntegerField(null=True, blank=True)
    access_password_hash = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    public_key_pem = models.TextField(blank=True)
    private_key_pem = models.TextField(blank=True)
    candidates_purged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.public_key_pem or not self.private_key_pem:
            public_key, private_key = generate_rsa_keypair_pem()
            self.public_key_pem = public_key
            self.private_key_pem = private_key
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def requires_password(self) -> bool:
        return bool(self.access_password_hash)

    def set_access_password(self, raw_password: str):
        if raw_password:
            self.access_password_hash = make_password(raw_password)
        else:
            self.access_password_hash = ""

    def check_access_password(self, raw_password: str) -> bool:
        if not self.access_password_hash:
            return True
        if not raw_password:
            return False
        return check_password(raw_password, self.access_password_hash)


class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="candidates")
    full_name = models.CharField(max_length=150)
    profile_image_url = models.URLField(blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.election.title})"


class Vote(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="votes")
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, related_name="votes", null=True, blank=True)
    voter_hash = models.CharField(max_length=64)
    encrypted_ballot = models.TextField()
    receipt_code = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "voter_hash"],
                name="unique_vote_per_voter_per_election",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.receipt_code:
            entropy = f"{self.election_id}:{self.voter_hash}:{self.encrypted_ballot}:{secrets.token_hex(16)}"
            self.receipt_code = hashlib.sha256(entropy.encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Vote {self.receipt_code[:8]}..."


class AdminMFA(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mfa_profile")
    secret = models.CharField(max_length=64)
    secret_sent_at = models.DateTimeField(null=True, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        payload = {"user": self.user.username, "enabled": self.is_enabled}
        return json.dumps(payload)


class MFAFailedAttempt(models.Model):
    ip_address = models.GenericIPAddressField()
    attempt_count = models.PositiveIntegerField(default=1)
    last_attempt_at = models.DateTimeField(auto_now=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ip_address"], name="unique_mfa_failed_attempt_ip")
        ]

    def __str__(self):
        return f"MFA failed attempts from {self.ip_address}: {self.attempt_count}"


class ElectionResultSnapshot(models.Model):
    election = models.OneToOneField(Election, on_delete=models.CASCADE, related_name="result_snapshot")
    total_votes = models.PositiveIntegerField(default=0)
    results_json = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Snapshot for {self.election.title}"
