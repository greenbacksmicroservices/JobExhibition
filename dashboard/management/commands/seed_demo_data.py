import random
import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from dashboard.models import Candidate, Company, Consultancy, Job


class Command(BaseCommand):
    help = "Seed demo data for companies, consultancies, candidates, and jobs."

    def add_arguments(self, parser):
        parser.add_argument("--companies", type=int, default=600)
        parser.add_argument("--consultancies", type=int, default=500)
        parser.add_argument("--candidates", type=int, default=1000)
        parser.add_argument("--jobs", type=int, default=500)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        seed = options.get("seed")
        if seed is not None:
            random.seed(seed)

        self.demo_password = make_password("Jobex@123")

        target_companies = options["companies"]
        target_consultancies = options["consultancies"]
        target_candidates = options["candidates"]
        target_jobs = options["jobs"]

        self.stdout.write("Seeding demo data...")

        company_needed = max(0, target_companies - Company.objects.count())
        consultancy_needed = max(0, target_consultancies - Consultancy.objects.count())
        candidate_needed = max(0, target_candidates - Candidate.objects.count())
        job_needed = max(0, target_jobs - Job.objects.count())

        if company_needed:
            self._seed_companies(company_needed)
        else:
            self.stdout.write("Companies: already at or above target.")

        if consultancy_needed:
            self._seed_consultancies(consultancy_needed)
        else:
            self.stdout.write("Consultancies: already at or above target.")

        if candidate_needed:
            self._seed_candidates(candidate_needed)
        else:
            self.stdout.write("Candidates: already at or above target.")

        if job_needed:
            self._seed_jobs(job_needed)
        else:
            self.stdout.write("Jobs: already at or above target.")

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))

    def _seed_companies(self, count):
        prefixes = ["Blue", "Quantum", "Nova", "Vertex", "Next", "Prime", "Bright", "Zen", "Pulse", "Sky"]
        suffixes = ["Labs", "Works", "Systems", "Soft", "Dynamics", "Solutions", "Networks", "Industries", "Tech"]
        industries = [
            "Information Technology",
            "FinTech",
            "Healthcare",
            "EdTech",
            "Manufacturing",
            "Retail",
            "Logistics",
            "Telecom",
            "Energy",
            "Consulting",
        ]
        company_sizes = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
        company_types = ["Private Limited", "Public Limited", "LLP", "Startup"]
        cities = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Noida", "Gurugram"]
        states = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Tamil Nadu", "West Bengal", "Uttar Pradesh"]
        plans = ["Free", "Premium", "Enterprise"]
        plan_names = ["Starter", "Growth", "Scale", "Enterprise"]
        payment_status = ["Paid", "Due", "Failed"]

        existing_emails = set(Company.objects.values_list("email", flat=True))
        companies = []
        start_index = Company.objects.count() + 1
        today = timezone.localdate()

        for idx in range(count):
            name = f"{random.choice(prefixes)} {random.choice(suffixes)} {start_index + idx}"
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            email = f"hr{start_index + idx}@{slug}.com"
            if email in existing_emails:
                email = f"hr{start_index + idx}@jobexhibition-demo.com"
            existing_emails.add(email)

            city = random.choice(cities)
            state = random.choice(states)
            plan_type = random.choice(plans)
            plan_start = today - timedelta(days=random.randint(10, 220))
            plan_expiry = plan_start + timedelta(days=365)

            companies.append(
                Company(
                    name=name,
                    email=email,
                    phone=self._random_phone(),
                    password=self.demo_password,
                    location=city,
                    address=f"{random.randint(10, 140)} {city} Tech Park",
                    account_type="Company",
                    profile_completion=random.randint(85, 100),
                    kyc_status="Verified",
                    account_status="Active",
                    username=slug[:40],
                    company_type=random.choice(company_types),
                    industry_type=random.choice(industries),
                    company_size=random.choice(company_sizes),
                    website_url=f"https://www.{slug}.com",
                    alt_phone=self._random_phone(),
                    address_line1=f"{random.randint(10, 140)} Business Avenue",
                    address_line2=f"Suite {random.randint(100, 999)}",
                    city=city,
                    state=state,
                    country="India",
                    pincode=str(random.randint(100000, 999999)),
                    gst_number=f"GST{random.randint(100000, 999999)}",
                    cin_number=f"CIN{random.randint(100000, 999999)}",
                    pan_number=f"PAN{random.randint(1000, 9999)}",
                    company_description=f"{name} is a fast-growing {random.choice(industries).lower()} company.",
                    year_established=random.randint(1995, 2022),
                    employee_count=random.randint(20, 2000),
                    contact_position="HR Manager",
                    hr_name=f"{random.choice(self.first_names)} {random.choice(self.last_names)}",
                    hr_designation="Talent Acquisition Lead",
                    hr_phone=self._random_phone(),
                    hr_email=email,
                    email_verified=True,
                    phone_verified=True,
                    terms_accepted=True,
                    privacy_accepted=True,
                    guidelines_accepted=True,
                    registration_source="seed",
                    plan_name=random.choice(plan_names),
                    plan_type=plan_type,
                    plan_start=plan_start,
                    plan_expiry=plan_expiry,
                    payment_status=random.choice(payment_status),
                    auto_renew=bool(random.getrandbits(1)),
                )
            )

        Company.objects.bulk_create(companies, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Companies created: {len(companies)}"))

    def _seed_consultancies(self, count):
        prefixes = ["Career", "Talent", "Hire", "Elite", "Focus", "Bright", "Prime", "Axis", "Ever"]
        suffixes = ["Consulting", "Partners", "Advisors", "Placements", "Recruiters"]
        consultancy_types = ["Recruitment", "Staffing", "Executive Search", "HR Consulting"]
        industries = [
            "IT Services",
            "Healthcare",
            "Manufacturing",
            "BFSI",
            "Retail",
            "Logistics",
            "EdTech",
        ]
        cities = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Gurugram", "Bhubaneswar" , "Cuttack", "Rourkela", "Sambalpur", "Puri", "Konark", "Paradeep", "Balasore", "Jajpur", "Bhadrak", "Baripada", "Noida"]
        states = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Tamil Nadu", "West Bengal", "Haryana", "Odisha", "Uttar Pradesh"]
        plans = ["Free", "Premium", "Enterprise"]
        plan_names = ["Starter", "Growth", "Scale", "Enterprise"]
        payment_status = ["Paid", "Due", "Failed"]

        existing_emails = set(Consultancy.objects.values_list("email", flat=True))
        consultancies = []
        start_index = Consultancy.objects.count() + 1
        today = timezone.localdate()

        for idx in range(count):
            name = f"{random.choice(prefixes)} {random.choice(suffixes)} {start_index + idx}"
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            email = f"info{start_index + idx}@{slug}.com"
            if email in existing_emails:
                email = f"info{start_index + idx}@jobexhibition-demo.com"
            existing_emails.add(email)

            city = random.choice(cities)
            state = random.choice(states)
            plan_type = random.choice(plans)
            plan_start = today - timedelta(days=random.randint(10, 220))
            plan_expiry = plan_start + timedelta(days=365)

            consultancies.append(
                Consultancy(
                    name=name,
                    email=email,
                    phone=self._random_phone(),
                    password=self.demo_password,
                    location=city,
                    address=f"{random.randint(10, 140)} {city} Business Hub",
                    account_type="Consultancy",
                    profile_completion=random.randint(80, 100),
                    kyc_status="Verified",
                    account_status="Active",
                    company_type=random.choice(["LLP", "Private Limited", "Proprietorship"]),
                    registration_number=f"REG{random.randint(100000, 999999)}",
                    gst_number=f"GST{random.randint(100000, 999999)}",
                    year_established=random.randint(1998, 2023),
                    website_url=f"https://www.{slug}.com",
                    alt_phone=self._random_phone(),
                    office_landline=f"022-{random.randint(200000, 899999)}",
                    address_line1=f"{random.randint(10, 140)} Recruiters Avenue",
                    address_line2=f"Office {random.randint(1, 50)}",
                    city=city,
                    state=state,
                    pin_code=str(random.randint(100000, 999999)),
                    country="India",
                    owner_name=f"{random.choice(self.first_names)} {random.choice(self.last_names)}",
                    owner_designation="Founder",
                    owner_phone=self._random_phone(),
                    owner_email=email,
                    owner_pan=f"PAN{random.randint(1000, 9999)}",
                    owner_aadhaar=f"{random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}",
                    consultancy_type=random.choice(consultancy_types),
                    industries_served=", ".join(random.sample(industries, k=3)),
                    service_charges=f"{random.randint(8, 18)}% of CTC",
                    areas_of_operation=", ".join(random.sample(cities, k=3)),
                    license_number=f"LIC{random.randint(10000, 99999)}",
                    contact_position="Account Manager",
                    plan_name=random.choice(plan_names),
                    plan_type=plan_type,
                    plan_start=plan_start,
                    plan_expiry=plan_expiry,
                    payment_status=random.choice(payment_status),
                    auto_renew=bool(random.getrandbits(1)),
                    commission_fixed_fee=random.randint(15000, 35000),
                    commission_percentage=random.randint(8, 15),
                    commission_milestone_notes="Stage-wise commission release",
                )
            )

        Consultancy.objects.bulk_create(consultancies, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Consultancies created: {len(consultancies)}"))

    def _seed_candidates(self, count):
        locations = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Gurugram", "Noida", "Bhubaneswar" , "Cuttack", "Rourkela", "Sambalpur", "Puri", "Konark", "Paradeep", "Balasore", "Jajpur", "Bhadrak", "Baripada"]
        industries = ["IT", "Finance", "Healthcare", "Retail", "Manufacturing", "Consulting"]
        education_levels = ["B.Tech", "BCA", "BBA", "MBA", "M.Tech", "B.Sc", "MCA"]
        employment_status = ["Employed", "Notice Period", "Actively Looking"]
        notice_periods = ["Immediate", "15 days", "30 days", "45 days", "60 days"]
        availability = ["Available", "Immediate", "Within 2 weeks", "Within 1 month"]

        consultancies = list(Consultancy.objects.values_list("id", flat=True))
        existing_emails = set(Candidate.objects.values_list("email", flat=True))
        candidates = []
        start_index = Candidate.objects.count() + 1

        for idx in range(count):
            first = random.choice(self.first_names)
            last = random.choice(self.last_names)
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{start_index + idx}@jobexhibition-demo.com"
            if email in existing_emails:
                email = f"candidate{start_index + idx}@jobexhibition-demo.com"
            existing_emails.add(email)

            city = random.choice(locations)
            skills = random.sample(self.skill_pool, k=5)
            secondary_skills = random.sample(self.skill_pool, k=3)
            experience_years = random.randint(0, 12)

            candidates.append(
                Candidate(
                    name=name,
                    email=email,
                    phone=self._random_phone(),
                    password=self.demo_password,
                    location=city,
                    address=f"{random.randint(10, 220)} {city} Residency",
                    account_type="Candidate",
                    profile_completion=random.randint(75, 100),
                    kyc_status="Verified",
                    account_status="Active",
                    date_of_birth=timezone.localdate() - timedelta(days=random.randint(22 * 365, 40 * 365)),
                    gender=random.choice(["Male", "Female", "Other"]),
                    preferred_job_location=", ".join(random.sample(locations, k=2)),
                    marital_status=random.choice(["Single", "Married"]),
                    nationality="Indian",
                    bio="Driven professional eager to contribute in dynamic teams.",
                    career_objective="Seeking growth opportunities with impact-driven organizations.",
                    skills=", ".join(skills),
                    secondary_skills=", ".join(secondary_skills),
                    alt_phone=self._random_phone(),
                    phone_verified=True,
                    email_verified=True,
                    experience_type="Professional",
                    employment_type=random.choice(["Full-time", "Part-time", "Contract"]),
                    experience=f"{experience_years} years",
                    total_experience=f"{experience_years} years",
                    current_job_status=random.choice(employment_status),
                    current_company=f"{random.choice(['Tech', 'Global', 'Prime', 'Nova'])} Corp",
                    current_salary=f"{random.randint(4, 12)} LPA",
                    current_position=random.choice(
                        ["Software Engineer", "Business Analyst", "Marketing Executive", "HR Associate", "Data Analyst"]
                    ),
                    expected_salary=f"{random.randint(6, 16)} LPA",
                    notice_period=random.choice(notice_periods),
                    preferred_industry=random.choice(industries),
                    willing_to_relocate=bool(random.getrandbits(1)),
                    education=random.choice(education_levels),
                    education_10th="CBSE 10th - 85%",
                    education_12th="CBSE 12th - 82%",
                    education_graduation=random.choice(education_levels),
                    education_post_graduation=random.choice(["MBA", "M.Tech", "MCA", ""]),
                    certifications="Scrum Master, AWS Practitioner",
                    languages="English, Hindi , Odia",
                    linkedin_url=f"https://linkedin.com/in/{first.lower()}{last.lower()}{start_index + idx}",
                    github_url=f"https://github.com/{first.lower()}{last.lower()}{start_index + idx}",
                    portfolio_url=f"https://portfolio.{first.lower()}{last.lower()}.com",
                    availability_status=random.choice(availability),
                    profile_visibility=True,
                    source_consultancy_id=random.choice(consultancies) if consultancies and random.random() > 0.6 else None,
                )
            )

        Candidate.objects.bulk_create(candidates, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Candidates created: {len(candidates)}"))

    def _seed_jobs(self, count):
        job_titles = [
            "Software Engineer",
            "Frontend Developer",
            "Backend Developer",
            "Data Analyst",
            "Product Manager",
            "HR Executive",
            "Marketing Specialist",
            "Sales Manager",
            "UI/UX Designer",
            "DevOps Engineer",
        ]
        categories = [
            "Engineering",
            "Product",
            "Human Resources",
            "Marketing",
            "Sales",
            "Design",
            "Operations",
            "Analytics",
        ]
        locations = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Remote", "Gurugram", "Noida", "Bhubaneswar" , "Cuttack", "Rourkela", "Sambalpur", "Puri", "Konark", "Paradeep", "Balasore", "Jajpur", "Bhadrak", "Baripada"]
        job_types = ["Full-time", "Part-time", "Contract", "Remote"]
        statuses = ["Approved", "Approved", "Approved", "Pending", "Rejected"]
        verifications = ["Verified", "Pending", "Flagged"]

        companies = list(Company.objects.values("name", "hr_name", "hr_email", "hr_phone"))
        if not companies:
            self.stdout.write(self.style.WARNING("Jobs skipped: no companies available."))
            return

        existing_job_ids = set(Job.objects.values_list("job_id", flat=True))
        jobs = []
        today = timezone.localdate()
        start_index = Job.objects.count() + 1

        for idx in range(count):
            title = random.choice(job_titles)
            company = random.choice(companies)
            job_id = self._generate_job_id(existing_job_ids, start_index + idx)
            skill_set = ", ".join(random.sample(self.skill_pool, k=6))
            posted_date = today - timedelta(days=random.randint(1, 180))

            jobs.append(
                Job(
                    job_id=job_id,
                    title=title,
                    company=company["name"],
                    category=random.choice(categories),
                    location=random.choice(locations),
                    job_type=random.choice(job_types),
                    salary=f"{random.randint(4, 18)} LPA",
                    experience=f"{random.randint(0, 8)} years",
                    skills=skill_set,
                    posted_date=posted_date,
                    status=random.choice(statuses),
                    lifecycle_status="Active",
                    applicants=random.randint(0, 120),
                    verification=random.choice(verifications),
                    featured=random.random() > 0.7,
                    recruiter_name=company.get("hr_name") or company["name"],
                    recruiter_email=company.get("hr_email") or f"hr@{job_id.lower()}.com",
                    recruiter_phone=company.get("hr_phone") or self._random_phone(),
                    summary=f"{title} role with growth-focused team at {company['name']}.",
                    description=(
                        f"We are hiring a {title} for {company['name']} in {random.choice(locations)}. "
                        "You will collaborate with cross-functional teams and deliver impact."
                    ),
                    requirements=f"Skills needed: {skill_set}. Strong communication required.",
                )
            )

        Job.objects.bulk_create(jobs, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Jobs created: {len(jobs)}"))

    @property
    def first_names(self):
        return [
            "Aarav",
            "Vivaan",
            "Binayak",
            "Aditya",
            "Vihaan",
            "Arjun",
            "Reyansh",
            "Ishaan",
            "Shaurya",
            "Ananya",
            "Diya",
            "Kavya",
            "Aisha",
            "Riya",
            "Meera",
            "Nisha",
            "Sara",
        ]

    @property
    def last_names(self):
        return [
            "Sharma",
            "Verma",
            "Sethy",
            "Dash",
            "Khan",
            "Kapoor",
            "Gupta",
            "Sahu",
            "sahoo",
            "Reddy",
            "Nayak",
            "Naik",
        ]

    @property
    def skill_pool(self):
        return [
            "Python",
            "Django",
            "React",
            "Node.js",
            "SQL",
            "AWS",
            "Docker",
            "Kubernetes",
            "Java",
            "JavaScript",
            "TypeScript",
            "Power BI",
            "Tableau",
            "Excel",
            "Figma",
            "Communication",
            "Leadership",
        ]

    def _random_phone(self):
        return f"+91-{random.randint(6000000000, 9999999999)}"

    def _generate_job_id(self, existing_ids, seed_value):
        while True:
            job_id = f"JOB{seed_value:05d}"
            if job_id not in existing_ids:
                existing_ids.add(job_id)
                return job_id
            seed_value += 1
