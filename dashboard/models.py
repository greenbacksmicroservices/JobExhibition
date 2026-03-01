import os

from django.conf import settings
from django.db import models
from django.utils import timezone

KYC_CHOICES = [
    ("Pending", "Pending"),
    ("Verified", "Verified"),
    ("Rejected", "Rejected"),
]

ACCOUNT_STATUS_CHOICES = [
    ("Active", "Active"),
    ("Suspended", "Suspended"),
    ("Blocked", "Blocked"),
]

PLAN_CHOICES = [
    ("Free", "Free"),
    ("Premium", "Premium"),
    ("Enterprise", "Enterprise"),
]

PAYMENT_CHOICES = [
    ("Paid", "Paid"),
    ("Due", "Due"),
    ("Failed", "Failed"),
]

JOB_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("Approved", "Approved"),
    ("Rejected", "Rejected"),
    ("Reported", "Reported"),
]

CONSULTANCY_JOB_LIFECYCLE_CHOICES = [
    ("Draft", "Draft"),
    ("Active", "Active"),
    ("Paused", "Paused"),
    ("Closed", "Closed"),
    ("Expired", "Expired"),
    ("Archived", "Archived"),
]

JOB_TYPE_CHOICES = [
    ("Full-time", "Full-time"),
    ("Part-time", "Part-time"),
    ("Contract", "Contract"),
    ("Remote", "Remote"),
]

JOB_VERIFICATION_CHOICES = [
    ("Verified", "Verified"),
    ("Pending", "Pending"),
    ("Flagged", "Flagged"),
]

APPLICATION_STATUS_CHOICES = [
    ("Applied", "Applied"),
    ("Shortlisted", "Shortlisted"),
    ("Interview", "Interview"),
    ("Selected", "Selected"),
    ("Rejected", "Rejected"),
    ("On Hold", "On Hold"),
    ("Archived", "Archived"),
    ("Offer Issued", "Offer Issued"),
    ("Interview Scheduled", "Interview Scheduled"),
]

AD_AUDIENCE_CHOICES = [
    ("company", "Company"),
    ("consultancy", "Consultancy"),
    ("candidate", "Candidate"),
]

AD_SEGMENT_CHOICES = [
    ("subscribed", "Subscribed"),
    ("non_subscribed", "Non-Subscribed"),
]

AD_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
AD_VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}

SUBSCRIPTION_PLAN_CHOICES = [
    ("Free", "Free"),
    ("Basic", "Basic"),
    ("Standard", "Standard"),
    ("Gold", "Gold"),
]

SUBSCRIPTION_PAYMENT_CHOICES = [
    ("Free", "Free"),
    ("Paid", "Paid"),
    ("Due", "Due"),
    ("Failed", "Failed"),
]

INTERVIEW_STATUS_CHOICES = [
    ("scheduled", "Scheduled"),
    ("rescheduled", "Rescheduled"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
    ("no_show", "No Show"),
]

INTERVIEW_MODE_CHOICES = [
    ("Online", "Online"),
    ("Offline", "Offline"),
]

INTERVIEW_DECISION_CHOICES = [
    ("next_round", "Move to Next Round"),
    ("selected", "Selected"),
    ("rejected", "Rejected"),
    ("hold", "Hold"),
]

INTERVIEW_ROUND_CHOICES = [
    ("HR", "HR"),
    ("Technical", "Technical"),
    ("Final", "Final"),
]

PLACEMENT_STATUS_CHOICES = [
    ("Pending Approval", "Pending Approval"),
    ("Approved", "Approved"),
    ("Paid", "Paid"),
    ("Cancelled", "Cancelled"),
]

ASSIGNED_JOB_STATUS_CHOICES = [
    ("Active", "Active"),
    ("Closed", "Closed"),
    ("Urgent", "Urgent"),
    ("Paused", "Paused"),
]

COMMISSION_TYPE_CHOICES = [
    ("Fixed", "Fixed"),
    ("Percentage", "Percentage"),
    ("Milestone", "Milestone"),
]


class UserBase(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=50, blank=True)
    password = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    profile_image = models.FileField(upload_to="profiles/", null=True, blank=True)
    account_type = models.CharField(max_length=50, blank=True)
    profile_completion = models.PositiveIntegerField(default=0)
    kyc_status = models.CharField(max_length=20, choices=KYC_CHOICES, default="Pending")
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default="Active")
    warning_count = models.PositiveIntegerField(default=0)
    suspension_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"


class AdminProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_profile")
    phone = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    photo = models.FileField(upload_to="profiles/admins/", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.username} Profile"


class Company(UserBase):
    gst_number = models.CharField(max_length=120, blank=True)
    cin_number = models.CharField(max_length=120, blank=True)
    registration_document = models.FileField(upload_to="documents/companies/", null=True, blank=True)
    contact_position = models.CharField(max_length=120, blank=True)
    hr_name = models.CharField(max_length=200, blank=True)
    hr_designation = models.CharField(max_length=120, blank=True)
    hr_phone = models.CharField(max_length=50, blank=True)
    hr_email = models.EmailField(blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    terms_accepted = models.BooleanField(default=False)
    registration_source = models.CharField(max_length=40, blank=True)
    plan_name = models.CharField(max_length=120, blank=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, blank=True)
    plan_start = models.DateField(null=True, blank=True)
    plan_expiry = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, blank=True)
    auto_renew = models.BooleanField(default=False)


class CompanyKycDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("gst_certificate", "GST Certificate"),
        ("cin_certificate", "CIN Certificate"),
        ("incorporation", "Certificate of Incorporation"),
        ("address_proof", "Address Proof"),
        ("other", "Other"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="kyc_documents",
    )
    title = models.CharField(max_length=120, blank=True)
    document_type = models.CharField(max_length=40, choices=DOCUMENT_TYPE_CHOICES, blank=True)
    file = models.FileField(upload_to="documents/companies/kyc/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.company.name} - {self.title or self.document_type or 'Document'}"


class Consultancy(UserBase):
    company_type = models.CharField(max_length=40, blank=True)
    registration_number = models.CharField(max_length=120, blank=True)
    gst_number = models.CharField(max_length=120, blank=True)
    year_established = models.PositiveIntegerField(null=True, blank=True)
    website_url = models.URLField(blank=True)
    alt_phone = models.CharField(max_length=50, blank=True)
    office_landline = models.CharField(max_length=50, blank=True)
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    pin_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=120, blank=True)
    owner_name = models.CharField(max_length=200, blank=True)
    owner_designation = models.CharField(max_length=120, blank=True)
    owner_phone = models.CharField(max_length=50, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_pan = models.CharField(max_length=50, blank=True)
    owner_aadhaar = models.CharField(max_length=50, blank=True)
    consultancy_type = models.CharField(max_length=200, blank=True)
    industries_served = models.CharField(max_length=255, blank=True)
    service_charges = models.CharField(max_length=120, blank=True)
    areas_of_operation = models.CharField(max_length=120, blank=True)
    license_number = models.CharField(max_length=120, blank=True)
    registration_certificate = models.FileField(upload_to="documents/consultancies/", null=True, blank=True)
    gst_certificate = models.FileField(upload_to="documents/consultancies/", null=True, blank=True)
    pan_card = models.FileField(upload_to="documents/consultancies/", null=True, blank=True)
    address_proof = models.FileField(upload_to="documents/consultancies/", null=True, blank=True)
    contact_position = models.CharField(max_length=120, blank=True)
    plan_name = models.CharField(max_length=120, blank=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, blank=True)
    plan_start = models.DateField(null=True, blank=True)
    plan_expiry = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, blank=True)
    auto_renew = models.BooleanField(default=False)
    commission_fixed_fee = models.PositiveIntegerField(default=25000)
    commission_percentage = models.PositiveIntegerField(default=10)
    commission_milestone_notes = models.CharField(
        max_length=255,
        blank=True,
        default="Stage-wise commission release",
    )


class ConsultancyKycDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("license", "License"),
        ("gst", "GST Certificate"),
        ("incorporation", "Certificate of Incorporation"),
        ("address", "Address Proof"),
        ("other", "Other"),
    ]

    consultancy = models.ForeignKey(
        Consultancy,
        on_delete=models.CASCADE,
        related_name="kyc_documents",
    )
    document_title = models.CharField(max_length=120, blank=True)
    document_type = models.CharField(max_length=40, choices=DOCUMENT_TYPE_CHOICES, blank=True)
    document_file = models.FileField(upload_to="documents/consultancies/kyc/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.consultancy.name} - {self.document_title or self.document_type or 'Document'}"


class Candidate(UserBase):
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    preferred_job_location = models.CharField(max_length=200, blank=True)
    marital_status = models.CharField(max_length=40, blank=True)
    nationality = models.CharField(max_length=120, blank=True)
    resume = models.FileField(upload_to="documents/candidates/", null=True, blank=True)
    id_proof = models.FileField(upload_to="documents/candidates/", null=True, blank=True)
    bio = models.TextField(blank=True)
    career_objective = models.TextField(blank=True)
    skills = models.CharField(max_length=255, blank=True)
    secondary_skills = models.CharField(max_length=255, blank=True)
    alt_phone = models.CharField(max_length=50, blank=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    experience_type = models.CharField(max_length=40, blank=True)
    employment_type = models.CharField(max_length=40, blank=True)
    experience = models.CharField(max_length=120, blank=True)
    total_experience = models.CharField(max_length=120, blank=True)
    current_job_status = models.CharField(max_length=40, blank=True)
    current_company = models.CharField(max_length=200, blank=True)
    current_salary = models.CharField(max_length=120, blank=True)
    current_position = models.CharField(max_length=120, blank=True)
    expected_salary = models.CharField(max_length=120, blank=True)
    notice_period = models.CharField(max_length=120, blank=True)
    preferred_industry = models.CharField(max_length=200, blank=True)
    willing_to_relocate = models.BooleanField(default=False)
    education = models.CharField(max_length=200, blank=True)
    education_10th = models.CharField(max_length=200, blank=True)
    education_12th = models.CharField(max_length=200, blank=True)
    education_graduation = models.CharField(max_length=200, blank=True)
    education_post_graduation = models.CharField(max_length=200, blank=True)
    education_other = models.CharField(max_length=200, blank=True)
    certifications = models.CharField(max_length=255, blank=True)
    languages = models.CharField(max_length=200, blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    portfolio_file = models.FileField(upload_to="documents/candidates/portfolio/", null=True, blank=True)
    video_resume = models.FileField(upload_to="documents/candidates/video/", null=True, blank=True)
    availability_status = models.CharField(max_length=40, blank=True)
    profile_visibility = models.BooleanField(default=True)
    source_consultancy = models.ForeignKey(
        "Consultancy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_pool",
    )


class CandidateResume(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=120, blank=True)
    template_name = models.CharField(max_length=40, blank=True)
    resume_file = models.FileField(upload_to="documents/candidates/resumes/")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.candidate.name} - {self.title or 'Resume'}"


class CandidateCertification(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="certification_files")
    title = models.CharField(max_length=120, blank=True)
    issuing_org = models.CharField(max_length=200, blank=True)
    year = models.CharField(max_length=10, blank=True)
    certificate_file = models.FileField(upload_to="documents/candidates/certifications/", null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.candidate.name} - {self.title or 'Certification'}"


class CandidateEducation(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="education_entries")
    qualification = models.CharField(max_length=120, blank=True)
    course_name = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    institution = models.CharField(max_length=200, blank=True)
    passing_year = models.CharField(max_length=10, blank=True)
    score = models.CharField(max_length=20, blank=True)

    def __str__(self) -> str:
        return f"{self.candidate.name} - {self.qualification or 'Education'}"


class CandidateExperience(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="experience_entries")
    company_name = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    responsibilities = models.TextField(blank=True)
    achievements = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.candidate.name} - {self.company_name or 'Experience'}"


class CandidateSkill(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="skill_entries")
    name = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=40, blank=True)
    level = models.CharField(max_length=40, blank=True)

    def __str__(self) -> str:
        return f"{self.candidate.name} - {self.name or 'Skill'}"


class CandidateProject(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="project_entries")
    title = models.CharField(max_length=200, blank=True)
    technology = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=120, blank=True)

    def __str__(self) -> str:
        return f"{self.candidate.name} - {self.title or 'Project'}"


class Job(models.Model):
    job_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    category = models.CharField(max_length=120)
    location = models.CharField(max_length=120)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default="Full-time")
    salary = models.CharField(max_length=120, blank=True)
    experience = models.CharField(max_length=120, blank=True)
    skills = models.CharField(max_length=255, blank=True)
    posted_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=JOB_STATUS_CHOICES, default="Pending")
    lifecycle_status = models.CharField(
        max_length=20,
        choices=CONSULTANCY_JOB_LIFECYCLE_CHOICES,
        default="Active",
    )
    applicants = models.PositiveIntegerField(default=0)
    verification = models.CharField(max_length=20, choices=JOB_VERIFICATION_CHOICES, default="Pending")
    featured = models.BooleanField(default=False)
    recruiter_name = models.CharField(max_length=200, blank=True)
    recruiter_email = models.EmailField(max_length=254, blank=True)
    recruiter_phone = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.job_id})"


class Application(models.Model):
    application_id = models.CharField(max_length=20, unique=True)
    candidate_name = models.CharField(max_length=200)
    candidate_email = models.EmailField(max_length=254)
    candidate_phone = models.CharField(max_length=50, blank=True)
    candidate_location = models.CharField(max_length=120, blank=True)
    education = models.CharField(max_length=200, blank=True)
    experience = models.CharField(max_length=120, blank=True)
    current_company = models.CharField(max_length=200, blank=True)
    notice_period = models.CharField(max_length=120, blank=True)
    skills = models.CharField(max_length=255, blank=True)
    expected_salary = models.CharField(max_length=120, blank=True)
    recent_salary = models.CharField(max_length=120, blank=True)
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS_CHOICES, default="Applied")
    applied_date = models.DateField(null=True, blank=True)
    interview_date = models.DateField(null=True, blank=True)
    interview_time = models.CharField(max_length=20, blank=True)
    interviewer = models.CharField(max_length=200, blank=True)
    interview_mode = models.CharField(max_length=20, blank=True)
    meeting_link = models.CharField(max_length=255, blank=True)
    offer_package = models.CharField(max_length=120, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    cover_letter = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    interview_feedback = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    resume = models.FileField(upload_to="documents/applications/", null=True, blank=True)
    job = models.ForeignKey(
        "Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    consultancy = models.ForeignKey(
        "Consultancy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    placement_status = models.CharField(
        max_length=30,
        choices=PLACEMENT_STATUS_CHOICES,
        blank=True,
        default="Pending Approval",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.application_id} - {self.candidate_name}"


class AssignedJob(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="assignments")
    consultancy = models.ForeignKey(Consultancy, on_delete=models.CASCADE, related_name="assignments")
    assigned_date = models.DateField(default=timezone.localdate)
    deadline = models.DateField(null=True, blank=True)
    positions = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=ASSIGNED_JOB_STATUS_CHOICES, default="Active")
    commission_type = models.CharField(
        max_length=20,
        choices=COMMISSION_TYPE_CHOICES,
        default="Fixed",
    )
    commission_value = models.CharField(max_length=50, blank=True, default="20000")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("job", "consultancy")

    def __str__(self) -> str:
        return f"{self.job.title} -> {self.consultancy.name}"


class Advertisement(models.Model):
    audience = models.CharField(max_length=20, choices=AD_AUDIENCE_CHOICES)
    segment = models.CharField(max_length=20, choices=AD_SEGMENT_CHOICES, blank=True)
    title = models.CharField(max_length=120, blank=True)
    message = models.TextField()
    media_file = models.FileField(upload_to="advertisements/", blank=True, null=True)
    posted_by = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def media_kind(self) -> str:
        if not self.media_file:
            return ""
        ext = os.path.splitext(self.media_file.name)[1].lower()
        if ext in AD_VIDEO_EXTENSIONS:
            return "video"
        if ext in AD_IMAGE_EXTENSIONS:
            return "image"
        return ""

    def __str__(self) -> str:
        return f"{self.get_audience_display()} Ad ({self.created_at:%Y-%m-%d})"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=60)
    plan_code = models.CharField(max_length=20, unique=True)
    price_monthly = models.PositiveIntegerField(default=0)
    price_quarterly = models.PositiveIntegerField(default=0)
    job_posts = models.CharField(max_length=60, blank=True)
    job_validity = models.CharField(max_length=60, blank=True)
    resume_view = models.CharField(max_length=60, blank=True)
    resume_download = models.CharField(max_length=60, blank=True)
    candidate_chat = models.CharField(max_length=60, blank=True)
    interview_scheduler = models.CharField(max_length=60, blank=True)
    auto_match = models.CharField(max_length=60, blank=True)
    shortlisting = models.CharField(max_length=60, blank=True)
    candidate_ranking = models.CharField(max_length=60, blank=True)
    candidate_pool_manager = models.CharField(max_length=60, blank=True)
    featured_jobs = models.CharField(max_length=60, blank=True)
    company_branding = models.CharField(max_length=60, blank=True)
    analytics_dashboard = models.CharField(max_length=60, blank=True)
    support = models.CharField(max_length=80, blank=True)
    dedicated_account_manager = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.plan_code})"


class Subscription(models.Model):
    subscription_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=50)
    plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLAN_CHOICES, default="Free")
    payment_status = models.CharField(max_length=20, choices=SUBSCRIPTION_PAYMENT_CHOICES, default="Free")
    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    contact = models.EmailField(max_length=254, blank=True)
    monthly_revenue = models.PositiveIntegerField(default=0)
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.subscription_id})"


class SubscriptionLog(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="logs")
    old_plan = models.CharField(max_length=20, blank=True)
    new_plan = models.CharField(max_length=20)
    admin_name = models.CharField(max_length=120, default="Admin")
    action_date = models.DateField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.subscription.name}: {self.old_plan} -> {self.new_plan}"


class Interview(models.Model):
    interview_id = models.CharField(max_length=20, unique=True, blank=True)
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews",
    )
    candidate_name = models.CharField(max_length=200)
    candidate_email = models.EmailField(max_length=254, blank=True)
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    interview_date = models.DateField(null=True, blank=True)
    interview_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    mode = models.CharField(max_length=10, choices=INTERVIEW_MODE_CHOICES, default="Online")
    meeting_link = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    interviewer = models.CharField(max_length=200, blank=True)
    round = models.CharField(max_length=20, choices=INTERVIEW_ROUND_CHOICES, blank=True)
    panel_interviewers = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=INTERVIEW_STATUS_CHOICES, default="scheduled")
    feedback_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    technical_skills = models.TextField(blank=True)
    communication_skills = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    weakness = models.TextField(blank=True)
    final_decision = models.CharField(max_length=20, choices=INTERVIEW_DECISION_CHOICES, blank=True)
    feedback_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.interview_id or self.id} - {self.candidate_name}"


class MessageThread(models.Model):
    THREAD_TYPE_CHOICES = [
        ("candidate_company", "Candidate <-> Company"),
        ("candidate_consultancy", "Candidate <-> Consultancy"),
        ("company_consultancy", "Company <-> Consultancy"),
    ]

    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True)
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    consultancy = models.ForeignKey(Consultancy, on_delete=models.SET_NULL, null=True, blank=True)
    thread_type = models.CharField(max_length=40, choices=THREAD_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["thread_type", "application"],
                name="unique_thread_per_application_type",
            ),
        ]

    def __str__(self) -> str:
        label = self.get_thread_type_display()
        if self.job:
            return f"{label} - {self.job.title}"
        return label


class Message(models.Model):
    SENDER_ROLE_CHOICES = [
        ("candidate", "Candidate"),
        ("company", "Company"),
        ("consultancy", "Consultancy"),
        ("admin", "Admin"),
    ]

    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender_role = models.CharField(max_length=20, choices=SENDER_ROLE_CHOICES)
    sender_name = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to="messages/attachments/", null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.sender_role} - {self.created_at:%Y-%m-%d %H:%M}"


class EmailVerificationToken(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("candidate", "Candidate"),
        ("company", "Company"),
    ]

    token = models.CharField(max_length=120, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_id = models.PositiveIntegerField()
    email = models.EmailField(max_length=254)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.account_type}:{self.email}"


class LoginHistory(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("admin", "Admin"),
        ("company", "Company"),
        ("consultancy", "Consultancy"),
        ("candidate", "Candidate"),
        ("unknown", "Unknown"),
    ]

    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default="unknown")
    account_id = models.PositiveIntegerField(null=True, blank=True)
    username_or_email = models.CharField(max_length=254, blank=True)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    is_success = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        status = "success" if self.is_success else "failed"
        return f"{self.account_type} {status} - {self.created_at:%Y-%m-%d %H:%M}"


class PasswordResetToken(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("admin", "Admin"),
        ("company", "Company"),
        ("consultancy", "Consultancy"),
        ("candidate", "Candidate"),
    ]

    token = models.CharField(max_length=120, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_id = models.PositiveIntegerField()
    email = models.EmailField(max_length=254, blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.account_type}:{self.account_id}"
