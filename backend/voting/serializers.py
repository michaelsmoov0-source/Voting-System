import hashlib

import pyotp
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from .models import AdminMFA, Candidate, Election, Vote, VoterRegistration


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ["id", "election", "full_name", "profile_image_url", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class ElectionSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)
    encryption_public_key = serializers.CharField(source="public_key_pem", read_only=True)
    requires_password = serializers.SerializerMethodField(read_only=True)
    access_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    voter_filter_pattern = serializers.CharField(write_only=True, required=False, allow_blank=True)
    election_group = serializers.CharField(write_only=True, required=False, allow_blank=True)
    registration_starts_at = serializers.DateTimeField(required=False, allow_null=True)
    registration_ends_at = serializers.DateTimeField(required=False, allow_null=True)
    is_registration_open = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Election
        fields = [
            "id",
            "title",
            "description",
            "registration_starts_at",
            "registration_ends_at",
            "starts_at",
            "ends_at",
            "max_votes",
            "status",
            "candidates_purged_at",
            "created_at",
            "candidates",
            "encryption_public_key",
            "requires_password",
            "access_password",
            "voter_filter_pattern",
            "election_group",
            "is_registration_open",
        ]
        read_only_fields = ["id", "created_at"]

    def get_requires_password(self, obj):
        return obj.requires_password
    
    def get_is_registration_open(self, obj):
        return obj.is_registration_open

    def create(self, validated_data):
        raw_password = validated_data.pop("access_password", "")
        election = super().create(validated_data)
        if raw_password is not None:
            election.set_access_password(raw_password.strip())
            election.save(update_fields=["access_password_hash"])
        return election

    def update(self, instance, validated_data):
        raw_password = validated_data.pop("access_password", None)
        election = super().update(instance, validated_data)
        if raw_password is not None:
            election.set_access_password(raw_password.strip())
            election.save(update_fields=["access_password_hash"])
        return election


class EncryptedVoteCreateSerializer(serializers.Serializer):
    election_id = serializers.IntegerField()
    encrypted_ballot = serializers.CharField()
    user_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    matric_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    election_password = serializers.CharField(required=False, allow_blank=True)
    is_anonymous = serializers.BooleanField(default=False)

    def validate(self, attrs):
        try:
            election = Election.objects.get(id=attrs["election_id"])
        except Election.DoesNotExist as exc:
            raise serializers.ValidationError("Election not found.") from exc

        now = timezone.now()
        if election.status != "open" or now < election.starts_at or now > election.ends_at:
            raise serializers.ValidationError("Election is not currently open for voting.")
        
        # Get user identifier (user_id or matric_number)
        user_id = attrs.get("user_id", "").strip()
        matric_number = attrs.get("matric_number", "").strip()
        
        # At least one identifier is required
        if not user_id and not matric_number:
            raise serializers.ValidationError({"non_field_errors": ["Either User ID or Matric Number is required."]})
        
        # Use primary identifier for validation
        primary_identifier = user_id or matric_number
        
        # Check if user is registered for this election
        if election.registration_starts_at and election.registration_ends_at:
            if not election.is_registration_open:
                raise serializers.ValidationError("Registration period is closed for this election.")
            
            if not election.is_user_registered(primary_identifier):
                raise serializers.ValidationError("You are not registered for this election.")
        
        # Check voter filter pattern
        if not election.user_can_vote(primary_identifier, matric_number):
            raise serializers.ValidationError("You are not eligible to vote in this election based on the voter filter criteria.")
        
        if election.max_votes is not None and Vote.objects.filter(election=election).count() >= election.max_votes:
            raise serializers.ValidationError("This election has reached its vote limit.")
        if election.requires_password and not election.check_access_password(attrs.get("election_password", "")):
            raise serializers.ValidationError("Invalid election access password.")

        voter_hash = hashlib.sha256(primary_identifier.strip().lower().encode("utf-8")).hexdigest()
        if Vote.objects.filter(election=election, voter_hash=voter_hash).exists():
            raise serializers.ValidationError("This voter has already cast a vote for this election.")

        attrs["election"] = election
        attrs["voter_hash"] = voter_hash
        attrs["primary_identifier"] = primary_identifier
        return attrs


class VoteReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["receipt_code", "created_at"]


class VoterRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoterRegistration
        fields = ["election", "election_group", "user_id", "matric_number"]
        read_only_fields = ["registered_at"]
    
    def validate(self, attrs):
        user_id = attrs.get("user_id", "").strip()
        matric_number = attrs.get("matric_number", "").strip()
        
        # At least one identifier is required
        if not user_id and not matric_number:
            raise serializers.ValidationError({"non_field_errors": ["Either User ID or Matric Number is required."]})
        
        return attrs


class ElectionResultSerializer(serializers.Serializer):
    election_id = serializers.IntegerField()
    election_title = serializers.CharField()
    total_votes = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class RegisterSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=150)
    matric_number = serializers.CharField(max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=["voter", "admin"], default="voter")
    admin_invite_key = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        user_id = attrs.get("user_id", "").strip()
        matric = attrs.get("matric_number", "").strip()
        
        # At least one of user_id or matric_number is required
        if not user_id and not matric:
            raise serializers.ValidationError({"non_field_errors": ["Either User ID or Matric Number is required."]})
        
        # Use user_id as primary identifier if provided, otherwise use matric_number
        primary_identifier = user_id or matric
        
        # Check if user already exists (case-insensitive)
        if User.objects.filter(username__iexact=primary_identifier).exists():
            field = "user_id" if user_id else "matric_number"
            raise serializers.ValidationError({field: [f"User with this {'User ID' if user_id else 'Matric Number'} already exists."]})
        
        if attrs["role"] == "admin":
            admin_invite_key = attrs.get("admin_invite_key", "").strip()
            expected_key = getattr(settings, "ADMIN_INVITE_KEY", "")
            if not admin_invite_key or admin_invite_key != expected_key:
                raise serializers.ValidationError({"admin_invite_key": ["Invalid admin invite key."]})
        
        if attrs["role"] == "admin":
            email = attrs.get("email", "").strip()
            if not email:
                raise serializers.ValidationError({"email": ["Email is required for admin registration."]})
        
        attrs["email"] = email
        attrs["primary_identifier"] = primary_identifier
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role")
        validated_data.pop("admin_invite_key", None)
        primary_identifier = validated_data.pop("primary_identifier")
        
        user = User.objects.create_user(
            username=primary_identifier,
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        user.is_staff = (role == "admin")
        user.save()
        if user.is_staff:
            AdminMFA.objects.create(user=user, secret=pyotp.random_base32(), is_enabled=False)
        return user


class LoginSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    matric_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        # Try user_id first, then matric_number as username
        username = attrs.get("user_id") or attrs["matric_number"]
        user = authenticate(username=username, password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        attrs["user"] = user
        return attrs


class MFAVerifySerializer(serializers.Serializer):
    code = serializers.RegexField(regex=r"^\d{6}$", max_length=6, min_length=6, error_messages={
        "invalid": "Code must be exactly 6 digits.",
    })


class MFASetupConfirmSerializer(serializers.Serializer):
    code = serializers.RegexField(regex=r"^\d{6}$", max_length=6, min_length=6, error_messages={
        "invalid": "Code must be exactly 6 digits.",
    })
