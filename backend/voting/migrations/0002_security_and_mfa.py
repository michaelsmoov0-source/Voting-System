from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("voting", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="election",
            name="private_key_pem",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="election",
            name="public_key_pem",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="vote",
            name="encrypted_ballot",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="vote",
            name="voter_hash",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="vote",
            name="candidate",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="votes", to="voting.candidate"),
        ),
        migrations.RemoveField(
            model_name="vote",
            name="voter_identifier",
        ),
        migrations.AddConstraint(
            model_name="vote",
            constraint=models.UniqueConstraint(fields=("election", "voter_hash"), name="unique_vote_per_voter_per_election"),
        ),
        migrations.CreateModel(
            name="AdminMFA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("secret", models.CharField(max_length=64)),
                ("is_enabled", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="mfa_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
