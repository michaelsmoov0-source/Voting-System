import hashlib
import json
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.conf import settings

from .crypto_utils import generate_rsa_keypair_pem


class Election(models.Model):
    STATUS_CHOICES = [
        ("registration", "Registration"),
        ("open", "Open"),
        ("closed", "Closed"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    registration_starts_at = models.DateTimeField(null=True, blank=True)
    registration_ends_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    max_votes = models.PositiveIntegerField(null=True, blank=True)
    access_password_hash = models.CharField(max_length=255, blank=True)
    voter_filter_pattern = models.CharField(max_length=200, blank=True, help_text="Optional: Filter voters by pattern in candidate ID or matric number (e.g., 'CS', '2021', 'A')")
    election_group = models.CharField(max_length=100, blank=True, help_text="Optional: Group name for shared registration across multiple elections")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="registration")
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
    def encryption_public_key(self) -> str:
        return self.public_key_pem

    @property
    def requires_password(self) -> bool:
        return bool(self.access_password_hash)
    
    @property
    def is_registration_open(self) -> bool:
        """Check if registration period is currently open"""
        if not self.registration_starts_at or not self.registration_ends_at:
            return True  # No registration period means always open
        now = timezone.now()
        return self.registration_starts_at <= now <= self.registration_ends_at
    
    def user_can_vote(self, user_id: str, matric_number: str) -> bool:
        """Check if user can vote based on voter filter pattern"""
        if not self.voter_filter_pattern:
            return True  # No filter means everyone can vote
        
        pattern = self.voter_filter_pattern.upper()
        user_id_upper = user_id.upper()
        matric_upper = matric_number.upper()
        
        # Check if pattern exists in either user ID or matric number
        return pattern in user_id_upper or pattern in matric_upper
    
    def is_user_registered(self, user_id: str) -> bool:
        """Check if user is registered for this election or group"""
        if self.election_group:
            # Check if user is registered for any election in the same group
            return VoterRegistration.objects.filter(
                election_group=self.election_group,
                user_id=user_id
            ).exists()
        else:
            # Check specific election registration
            return VoterRegistration.objects.filter(
                election=self,
                user_id=user_id
            ).exists()

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
    voter_identifier = models.CharField(max_length=120, blank=True)  # Store original identifier for admin reference
    encrypted_ballot = models.TextField()
    is_anonymous = models.BooleanField(default=False)
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
    encrypted_results = models.TextField(blank=True)  # Encrypted version of results_json
    encryption_key = models.CharField(max_length=255, blank=True)  # Encrypted key
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Snapshot for {self.election.title}"


class VoterRegistration(models.Model):
    """Track which users are registered to vote in specific elections"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="voter_registrations")
    election_group = models.CharField(max_length=100, blank=True)  # Store group for group registrations
    user_id = models.CharField(max_length=120)
    matric_number = models.CharField(max_length=50)
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "user_id"],
                name="unique_registration_per_user_per_election"
            )
        ]
    
    def __str__(self):
        return f"{self.user_id} registered for {self.election.title}"


class UserIP(models.Model):
    """Store encrypted IP addresses for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="ip_address")
    encrypted_ip = models.CharField(max_length=255)  # Encrypted IP address
    ip_hash = models.CharField(max_length=64, unique=True)  # Hash for duplicate detection
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"IP record for {self.user.username}"
    
    @classmethod
    def encrypt_ip(cls, ip_address: str) -> str:
        """Encrypt IP address using Fernet symmetric encryption"""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate encryption key from SECRET_KEY
        password = f"ip_encryption_{settings.SECRET_KEY}".encode()
        salt = hashlib.sha256(f"ip_salt_{settings.SECRET_KEY}".encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        fernet = Fernet(key)
        
        # Encrypt the IP address
        encrypted_ip = fernet.encrypt(ip_address.encode())
        return base64.urlsafe_b64encode(encrypted_ip).decode()
    
    @classmethod
    def decrypt_ip(cls, encrypted_ip: str) -> str:
        """Decrypt IP address"""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate encryption key from SECRET_KEY
        password = f"ip_encryption_{settings.SECRET_KEY}".encode()
        salt = hashlib.sha256(f"ip_salt_{settings.SECRET_KEY}".encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        fernet = Fernet(key)
        
        # Decrypt the IP address
        encrypted_data = base64.urlsafe_b64decode(encrypted_ip.encode())
        decrypted_ip = fernet.decrypt(encrypted_data)
        return decrypted_ip.decode()
    
    @classmethod
    def get_ip_hash(cls, ip_address: str) -> str:
        """Generate hash for IP address to detect duplicates"""
        return hashlib.sha256(ip_address.encode()).hexdigest()
    
    @classmethod
    def ip_exists(cls, ip_address: str) -> bool:
        """Check if IP address already exists"""
        ip_hash = cls.get_ip_hash(ip_address)
        return cls.objects.filter(ip_hash=ip_hash).exists()
    
    @classmethod
    def generate_encryption_key(cls, election_id: str) -> tuple:
        """Generate encryption key based on election ID and secret"""
        password = f"election_results_{election_id}_{settings.SECRET_KEY}".encode()
        salt = hashlib.sha256(f"salt_{election_id}".encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_results(self, results_data: list) -> str:
        """Encrypt the results JSON data"""
        key = self.generate_encryption_key(str(self.election.id))
        fernet = Fernet(key)
        
        # Convert to JSON string and encrypt
        json_data = json.dumps(results_data)
        encrypted_data = fernet.encrypt(json_data.encode())
        
        # Store encrypted key (for demonstration - in production, use key management service)
        encrypted_key = base64.b64encode(key).decode()
        
        self.encrypted_results = base64.b64encode(encrypted_data).decode()
        self.encryption_key = encrypted_key
        self.save()
        
        return self.encrypted_results
    
    def decrypt_results(self) -> list:
        """Decrypt the results JSON data"""
        if not self.encrypted_results or not self.encryption_key:
            return self.results_json  # Fallback to unencrypted
        
        try:
            key = base64.b64decode(self.encryption_key.encode())
            fernet = Fernet(key)
            
            encrypted_data = base64.b64decode(self.encrypted_results.encode())
            decrypted_data = fernet.decrypt(encrypted_data).decode()
            
            return json.loads(decrypted_data)
        except Exception:
            # If decryption fails, return unencrypted data
            return self.results_json
