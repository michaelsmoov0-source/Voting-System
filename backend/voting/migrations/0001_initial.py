from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Election",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("open", "Open"), ("closed", "Closed")], default="draft", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Candidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("profile_image_url", models.URLField(blank=True)),
                ("description", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "election",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidates", to="voting.election"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Vote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("voter_identifier", models.CharField(max_length=120)),
                ("receipt_code", models.CharField(editable=False, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "candidate",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="votes", to="voting.candidate"),
                ),
                (
                    "election",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="votes", to="voting.election"),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("election", "voter_identifier"), name="unique_vote_per_voter_per_election")
                ],
            },
        ),
    ]
