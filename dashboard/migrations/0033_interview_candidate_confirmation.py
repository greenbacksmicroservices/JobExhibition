from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0032_deleteddatalog_company_pending_registration_password_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="interview",
            name="candidate_confirmation",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="interview",
            name="candidate_confirmation_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="interview",
            name="candidate_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
