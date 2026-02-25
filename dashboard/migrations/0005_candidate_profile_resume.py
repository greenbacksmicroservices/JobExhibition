from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_interview"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="bio",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="candidate",
            name="skills",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="candidate",
            name="experience",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="candidate",
            name="education",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="candidate",
            name="certifications",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="candidate",
            name="languages",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="candidate",
            name="linkedin_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="candidate",
            name="github_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="candidate",
            name="portfolio_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="candidate",
            name="portfolio_file",
            field=models.FileField(blank=True, null=True, upload_to="documents/candidates/portfolio/"),
        ),
        migrations.AddField(
            model_name="candidate",
            name="video_resume",
            field=models.FileField(blank=True, null=True, upload_to="documents/candidates/video/"),
        ),
        migrations.AddField(
            model_name="candidate",
            name="availability_status",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="candidate",
            name="profile_visibility",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="CandidateResume",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=120)),
                ("resume_file", models.FileField(upload_to="documents/candidates/resumes/")),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "candidate",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="resumes", to="dashboard.candidate"),
                ),
            ],
        ),
    ]
