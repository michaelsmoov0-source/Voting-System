from django.contrib import admin

from .models import AdminMFA, Candidate, Election, ElectionResultSnapshot, Vote


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "max_votes", "starts_at", "ends_at", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("full_name", "election", "created_at")
    list_filter = ("election",)
    search_fields = ("full_name",)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("election", "candidate", "voter_hash", "receipt_code", "created_at")
    list_filter = ("election", "candidate")
    search_fields = ("voter_hash", "receipt_code")
    readonly_fields = ("receipt_code", "created_at")


@admin.register(AdminMFA)
class AdminMFAAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enabled", "created_at")
    search_fields = ("user__username",)


@admin.register(ElectionResultSnapshot)
class ElectionResultSnapshotAdmin(admin.ModelAdmin):
    list_display = ("election", "total_votes", "created_at")
    search_fields = ("election__title",)
