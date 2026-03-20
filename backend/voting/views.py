import pyotp
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import DatabaseError
from django.core import signing
from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixnet import flush_mixed_votes, queue_encrypted_vote
from .models import AdminMFA, Candidate, Election, MFAFailedAttempt, Vote
from .permissions import IsAdminUserOrAPIKey
from .retention import purge_expired_candidate_data
from .serializers import (
    CandidateSerializer,
    ElectionResultSerializer,
    ElectionSerializer,
    EncryptedVoteCreateSerializer,
    LoginSerializer,
    MFASetupConfirmSerializer,
    MFAVerifySerializer,
    RegisterSerializer,
    VoteReceiptSerializer,
)
from .storage import upload_candidate_image


def _build_totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret, interval=settings.MFA_CODE_INTERVAL_SECONDS)


def _code_window_label() -> str:
    interval = settings.MFA_CODE_INTERVAL_SECONDS
    if interval % 60 == 0 and interval >= 60:
        minutes = interval // 60
        return f"{minutes} minute(s)"
    return f"{interval} second(s)"


@method_decorator(csrf_exempt, name='dispatch')
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "username": user.username, "is_admin": user.is_staff},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if user.is_staff:
            mfa_profile, _ = AdminMFA.objects.get_or_create(user=user, defaults={"secret": pyotp.random_base32()})
            if not mfa_profile.is_enabled:
                if not user.email:
                    return Response(
                        {
                            "detail": "Admin account has no email. Update admin email before MFA setup.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                token, _ = Token.objects.get_or_create(user=user)
                return Response(
                    {
                        "mfa_setup_required": True,
                        "setup_token": token.key,
                        "detail": "Admin MFA setup is required before login completion.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if mfa_profile.last_verified_at and timezone.now() - mfa_profile.last_verified_at <= timedelta(
                hours=settings.ADMIN_MFA_REVERIFY_HOURS
            ):
                token, _ = Token.objects.get_or_create(user=user)
                return Response(
                    {
                        "token": token.key,
                        "username": user.username,
                        "is_admin": True,
                        "mfa_status": "fresh",
                    },
                    status=status.HTTP_200_OK,
                )

            preauth_token = signing.dumps({"user_id": user.id}, salt="admin-mfa", compress=True)
            return Response({"mfa_required": True, "preauth_token": preauth_token}, status=status.HTTP_200_OK)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username, "is_admin": False}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class MFAVerifyLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request):
        preauth_token = request.data.get("preauth_token", "")
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = signing.loads(
                preauth_token,
                salt="admin-mfa",
                max_age=settings.MFA_PREAUTH_MAX_AGE_SECONDS,
            )
            user_id = payload["user_id"]
        except signing.BadSignature:
            return Response({"detail": "Invalid or expired preauth token."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mfa_profile = AdminMFA.objects.select_related("user").get(user_id=user_id, is_enabled=True)
        except AdminMFA.DoesNotExist:
            return Response({"detail": "MFA profile not configured."}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({
                "detail": "Database connection error. Please try again later or contact support."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        client_ip = self.get_client_ip(request)
        
        try:
            # Check if IP is currently locked
            failed_attempt, created = MFAFailedAttempt.objects.get_or_create(
                ip_address=client_ip,
                defaults={'attempt_count': 1}
            )
        except DatabaseError:
            return Response({
                "detail": "Database connection error. Please try again later."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        if failed_attempt.is_locked:
            return Response({
                "detail": "Too many failed attempts. Please request reverification.",
                "reverification_required": True,
                "attempts_remaining": 0
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        totp = _build_totp(mfa_profile.secret)
        if not totp.verify(serializer.validated_data["code"].strip(), valid_window=1):
            # Increment failed attempt count
            failed_attempt.attempt_count += 1
            failed_attempt.last_attempt_at = timezone.now()
            
            if failed_attempt.attempt_count >= 4:
                failed_attempt.is_locked = True
                failed_attempt.save()
                return Response({
                    "detail": "Too many failed attempts. Please request reverification.",
                    "reverification_required": True,
                    "attempts_remaining": 0
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                failed_attempt.save()
                attempts_remaining = 4 - failed_attempt.attempt_count
                return Response({
                    "detail": f"Invalid MFA code. {attempts_remaining} attempts remaining.",
                    "attempts_remaining": attempts_remaining
                }, status=status.HTTP_400_BAD_REQUEST)

        # Successful verification - reset failed attempts
        failed_attempt.attempt_count = 0
        failed_attempt.is_locked = False
        failed_attempt.save()

        mfa_profile.last_verified_at = timezone.now()
        mfa_profile.save(update_fields=["last_verified_at"])
        token, _ = Token.objects.get_or_create(user=mfa_profile.user)
        return Response(
            {"token": token.key, "username": mfa_profile.user.username, "is_admin": True},
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class MFAReverificationAPIView(APIView):
    permission_classes = [AllowAny]

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request):
        preauth_token = request.data.get("preauth_token", "")
        
        try:
            payload = signing.loads(
                preauth_token,
                salt="admin-mfa",
                max_age=settings.MFA_PREAUTH_MAX_AGE_SECONDS,
            )
            user_id = payload["user_id"]
        except signing.BadSignature:
            return Response({"detail": "Invalid or expired preauth token."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mfa_profile = AdminMFA.objects.select_related("user").get(user_id=user_id, is_enabled=True)
        except AdminMFA.DoesNotExist:
            return Response({"detail": "MFA profile not configured."}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({
                "detail": "Database connection error. Please try again later or contact support."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        client_ip = self.get_client_ip(request)
        
        try:
            # Check if IP is locked (should be, but verify)
            failed_attempt = MFAFailedAttempt.objects.get(ip_address=client_ip)
            if not failed_attempt.is_locked:
                return Response({"detail": "Reverification not required."}, status=status.HTTP_400_BAD_REQUEST)
        except MFAFailedAttempt.DoesNotExist:
            return Response({"detail": "No failed attempts found."}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({
                "detail": "Database connection error. Please try again later."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Generate new secret and reset MFA
        mfa_profile.secret = pyotp.random_base32()
        mfa_profile.is_enabled = False  # Require reconfirmation
        mfa_profile.save(update_fields=["secret", "is_enabled"])

        # Reset failed attempts
        failed_attempt.attempt_count = 0
        failed_attempt.is_locked = False
        failed_attempt.save()

        # Send new secret via email
        issuer = "SecureVotingSystem"
        totp = _build_totp(mfa_profile.secret)
        otpauth_url = totp.provisioning_uri(name=mfa_profile.user.username, issuer_name=issuer)

        try:
            send_mail(
                subject="Your Secure Voting MFA Secret - Reverification",
                message=(
                    "Your MFA secret key has been reset due to failed verification attempts:\n\n"
                    f"{mfa_profile.secret}\n\n"
                    "Add this new key to your authenticator app.\n"
                    f"Code validity window: {_code_window_label()}.\n"
                    f"otpauth URL:\n{otpauth_url}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[mfa_profile.user.email],
                fail_silently=False,
            )
        except Exception as exc:
            if settings.DEBUG:
                return Response(
                    {
                        "detail": f"Email send failed in DEBUG mode: {exc}. Enter MFA secret from email before requesting debug code.",
                        "debug_otpauth_url": otpauth_url,
                        "reverification_sent": True,
                        "setup_required": True
                    },
                    status=status.HTTP_200_OK,
                )
            return Response({"detail": f"Could not send MFA email: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Generate new setup token
        token, _ = Token.objects.get_or_create(user=mfa_profile.user)
        
        return Response(
            {
                "detail": f"New MFA secret sent to your email. Please complete setup again.",
                "reverification_sent": True,
                "setup_token": token.key,
                "setup_required": True
            },
            status=status.HTTP_200_OK,
        )


class MFASetupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Only admin users can configure MFA."}, status=status.HTTP_403_FORBIDDEN)
        if not request.user.email:
            return Response({"detail": "Admin email is required for MFA setup."}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = AdminMFA.objects.get_or_create(user=request.user, defaults={"secret": pyotp.random_base32()})
        if not profile.secret:
            profile.secret = pyotp.random_base32()
            profile.save(update_fields=["secret"])

        issuer = "SecureVotingSystem"
        totp = _build_totp(profile.secret)
        otpauth_url = totp.provisioning_uri(name=request.user.username, issuer_name=issuer)

        try:
            send_mail(
                subject="Your Secure Voting MFA Secret",
                message=(
                    "Your MFA secret key is:\n\n"
                    f"{profile.secret}\n\n"
                    "Add this key to your authenticator app.\n"
                    f"Code validity window: {_code_window_label()}.\n"
                    f"otpauth URL:\n{otpauth_url}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False,
            )
        except Exception as exc:
            if settings.DEBUG:
                return Response(
                    {
                        "detail": f"Email send failed in DEBUG mode: {exc}. Use the debug info below to setup MFA.",
                        "debug_otpauth_url": otpauth_url,
                        "debug_secret": profile.secret,
                        "is_enabled": profile.is_enabled,
                        "debug_instructions": f"Secret: {profile.secret} - Add this to your authenticator app or use debug code endpoint."
                    },
                    status=status.HTTP_200_OK,
                )
            return Response({"detail": f"Could not send MFA email: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "detail": f"MFA secret sent to your email. Codes rotate every {_code_window_label()}.",
                "is_enabled": profile.is_enabled,
            }
        )


@method_decorator(csrf_exempt, name='dispatch')
class MFASetupConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Only admin users can confirm MFA."}, status=status.HTTP_403_FORBIDDEN)
        serializer = MFASetupConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            profile = AdminMFA.objects.get(user=request.user)
        except AdminMFA.DoesNotExist:
            return Response({"detail": "Setup MFA first."}, status=status.HTTP_400_BAD_REQUEST)

        if not _build_totp(profile.secret).verify(serializer.validated_data["code"].strip(), valid_window=1):
            return Response({"detail": "Invalid MFA code."}, status=status.HTTP_400_BAD_REQUEST)

        profile.is_enabled = True
        profile.last_verified_at = timezone.now()
        profile.save(update_fields=["is_enabled", "last_verified_at"])
        return Response({"detail": "MFA enabled."}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class MFADebugCodeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Only admin users can access debug MFA code."}, status=status.HTTP_403_FORBIDDEN)
        try:
            profile = AdminMFA.objects.get(user=request.user)
        except AdminMFA.DoesNotExist:
            return Response({"detail": "Setup MFA first."}, status=status.HTTP_400_BAD_REQUEST)
        provided_secret = str(request.data.get("secret", "")).replace(" ", "").strip().upper()
        expected_secret = str(profile.secret or "").replace(" ", "").strip().upper()
        if not provided_secret:
            return Response({"detail": "MFA secret is required before requesting debug code."}, status=status.HTTP_400_BAD_REQUEST)
        if provided_secret != expected_secret:
            return Response({"detail": "Incorrect MFA secret."}, status=status.HTTP_400_BAD_REQUEST)

        totp = _build_totp(profile.secret)
        return Response(
            {
                "debug_current_code": totp.now(),
                "debug_code_interval_seconds": settings.MFA_CODE_INTERVAL_SECONDS,
            }
        )


class ElectionListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ElectionSerializer

    def get_queryset(self):
        purge_expired_candidate_data()
        return Election.objects.order_by("-created_at")


class ElectionCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAdminUserOrAPIKey]
    serializer_class = ElectionSerializer
    queryset = Election.objects.all()


class ElectionDetailAdminAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUserOrAPIKey]
    serializer_class = ElectionSerializer
    queryset = Election.objects.all()


class CandidateListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CandidateSerializer

    def get_queryset(self):
        purge_expired_candidate_data()
        election_id = self.request.query_params.get("election_id")
        queryset = Candidate.objects.select_related("election").order_by("id")
        if election_id:
            queryset = queryset.filter(election_id=election_id)
        return queryset


class CandidateCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAdminUserOrAPIKey]
    serializer_class = CandidateSerializer
    queryset = Candidate.objects.all()


class CandidateDetailAdminAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUserOrAPIKey]
    serializer_class = CandidateSerializer
    queryset = Candidate.objects.all()


class CandidateImageUploadAPIView(APIView):
    permission_classes = [IsAdminUserOrAPIKey]

    def post(self, request):
        election_id = request.data.get("election_id")
        image = request.FILES.get("image")
        if not election_id:
            return Response({"detail": "election_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not image:
            return Response({"detail": "image file is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            election_id_int = int(election_id)
        except ValueError:
            return Response({"detail": "election_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if not Election.objects.filter(id=election_id_int).exists():
            return Response({"detail": "Election not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            public_url = upload_candidate_image(image, election_id_int)
        except Exception as exc:
            return Response({"detail": f"Image upload failed: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"profile_image_url": public_url}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class CastVoteAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EncryptedVoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        election = serializer.validated_data["election"]
        voter_hash = serializer.validated_data["voter_hash"]
        encrypted_ballot = serializer.validated_data["encrypted_ballot"]
        is_anonymous = serializer.validated_data.get("is_anonymous", False)
        voter_identifier = serializer.validated_data["voter_identifier"]

        queue_encrypted_vote(election=election, voter_hash=voter_hash, encrypted_ballot=encrypted_ballot)
        flush_mixed_votes(election.id)

        vote = Vote.objects.filter(election=election, voter_hash=voter_hash).first()
        if vote:
            # Update vote with anonymous preference and identifier
            vote.is_anonymous = is_anonymous
            if not is_anonymous:
                vote.voter_identifier = voter_identifier
            else:
                vote.voter_identifier = ""  # Clear identifier if anonymous
            vote.save(update_fields=["is_anonymous", "voter_identifier"])

        if not vote:
            return Response({"detail": "Vote accepted into mix-net queue."}, status=status.HTTP_202_ACCEPTED)

        receipt = VoteReceiptSerializer(vote)
        return Response(receipt.data, status=status.HTTP_201_CREATED)


class ElectionResultsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, election_id):
        purge_expired_candidate_data()
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            return Response({"detail": "Election not found."}, status=status.HTTP_404_NOT_FOUND)

        if election.candidates_purged_at and hasattr(election, "result_snapshot"):
            snapshot = election.result_snapshot
            # Use decrypted results if available, fallback to unencrypted
            results_data = snapshot.decrypt_results()
            payload = {
                "election_id": election.id,
                "election_title": election.title,
                "total_votes": snapshot.total_votes,
                "results": results_data,
                "encrypted": bool(snapshot.encrypted_results),
            }
            result_serializer = ElectionResultSerializer(payload)
            return Response(result_serializer.data)

        candidate_counts = (
            Candidate.objects.filter(election=election)
            .annotate(vote_count=Count("votes"))
            .order_by("-vote_count", "full_name")
        )

        payload = {
            "election_id": election.id,
            "election_title": election.title,
            "total_votes": sum(item.vote_count for item in candidate_counts),
            "results": [
                {
                    "candidate_id": item.id,
                    "candidate_name": item.full_name,
                    "vote_count": item.vote_count,
                }
                for item in candidate_counts
            ],
        }

        result_serializer = ElectionResultSerializer(payload)
        return Response(result_serializer.data)


class AdminDashboardAPIView(APIView):
    permission_classes = [IsAdminUserOrAPIKey]

    def get(self, request):
        purge_expired_candidate_data()
        elections = Election.objects.count()
        candidates = Candidate.objects.count()
        total_votes = Vote.objects.count()

        return Response({"elections": elections, "candidates": candidates, "total_votes": total_votes})
