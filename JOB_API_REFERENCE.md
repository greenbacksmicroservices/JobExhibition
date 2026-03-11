# Job Exhibition - API Reference for Jobs

## Overview
Jobs displayed in the Candidate Panel are publicly available through these APIs. These can be used to display jobs on your website.

---

## 1. **Admin/Internal Job APIs** (For administrative management)

### List All Jobs
- **Endpoint:** `/api/jobs/list/`
- **Method:** GET
- **Name:** `api_jobs_list`
- **Purpose:** Retrieve all jobs (admin only)
- **Authentication:** Required (Admin login)

### Create Job
- **Endpoint:** `/api/jobs/create/`
- **Method:** POST
- **Name:** `api_jobs_create`
- **Purpose:** Create a new job (admin only)
- **Authentication:** Required (Admin login)

### Update Job
- **Endpoint:** `/api/jobs/<str:job_id>/update/`
- **Method:** POST/PUT
- **Name:** `api_jobs_update`
- **Parameters:** 
  - `job_id` (path parameter): The unique job ID
- **Purpose:** Update existing job
- **Authentication:** Required (Admin login)

### Delete Job
- **Endpoint:** `/api/jobs/<str:job_id>/delete/`
- **Method:** DELETE/POST
- **Name:** `api_jobs_delete`
- **Parameters:** 
  - `job_id` (path parameter): The unique job ID
- **Purpose:** Delete a job
- **Authentication:** Required (Admin login)

### Export Jobs
- **Endpoint:** `/api/jobs/export/`
- **Method:** GET/POST
- **Name:** `api_jobs_export`
- **Purpose:** Export jobs data in CSV/Excel format
- **Authentication:** Required (Admin login)

---

## 2. **Candidate-Facing APIs**

### Candidate Applications
- **Endpoint:** `/candidate/api/applications/`
- **Method:** GET
- **Name:** `candidate_api_applications`
- **Purpose:** Get list of job applications for logged-in candidate
- **Authentication:** Required (Candidate login)
- **Returns:** JSON with candidate applications

### Candidate Metrics
- **Endpoint:** `/candidate/api/metrics/`
- **Method:** GET
- **Name:** `candidate_api_metrics`
- **Purpose:** Get metrics (applied jobs, interviews, etc.)
- **Authentication:** Required (Candidate login)
- **Returns:** JSON with candidate activity metrics

### Toggle Save Job
- **Endpoint:** `/candidate/api/saved-jobs/toggle/`
- **Method:** POST
- **Name:** `candidate_api_toggle_saved_job`
- **Purpose:** Save or unsave a job
- **Authentication:** Required (Candidate login)
- **Parameters:**
  - `job_id` (POST): Job ID to toggle
  - `mode` (POST): "save" or "unsave"
- **Returns:** JSON with save status

---

## 3. **Job Display in Candidate Panel** (What jobs are shown)

### URL for Candidate Job Search
- **Endpoint:** `/candidate/job-search/`
- **Method:** GET
- **View:** `candidate_job_search_view`
- **Purpose:** Display all approved jobs to candidates with search & filter
- **Authentication:** Required (Candidate login)
- **Query Parameters (Filters):**
  - `search`: Search by job title or company name
  - `location`: Filter by location
  - `salary`: Filter by salary range
  - `experience`: Filter by experience level
  - `skills`: Filter by required skills
  - `job_type`: Filter by job type (Full-time, Part-time, etc.)
  - `sort`: Sorting option ("latest" or "salary_high")

### Job Detail Page
- **Endpoint:** `/candidate/job-search/<str:job_id>/`
- **Method:** GET
- **View:** `candidate_job_detail_view`
- **Purpose:** Display detailed information for a specific job
- **Authentication:** Required (Candidate login)
- **Parameters:**
  - `job_id` (path parameter): Unique job identifier

---

## 4. **Saved Jobs API**

### View Saved Jobs
- **Endpoint:** `/candidate/saved-jobs/`
- **Method:** GET
- **View:** `candidate_saved_jobs_view`
- **Purpose:** Display jobs saved by the candidate
- **Authentication:** Required (Candidate login)

---

## 5. **Database Query for Approved Jobs**

To fetch approved jobs programmatically (backend):

```python
from dashboard.models import Job

# Get all approved jobs
approved_jobs = Job.objects.filter(status="Approved")

# Each job has these fields:
# - job_id: Unique identifier
# - title: Job title
# - company: Company name
# - location: Job location
# - salary: Salary information
# - experience: Required experience
# - skills: Required skills
# - job_type: Employment type
# - created_at: Job creation date
```

---

## 6. **Complete Job Fields Available**

From the Job model in your database:
- `job_id` - Unique identifier
- `title` - Job title/position
- `company` - Company name
- `location` - Job location
- `salary` - Salary range
- `experience` - Required experience level
- `skills` - Required skills (comma-separated or list)
- `job_type` - Employment type (Full-time, Part-time, Contract, etc.)
- `description` - Full job description
- `requirements` - Job requirements
- `benefits` - Job benefits
- `status` - Job status (only "Approved" jobs are shown to candidates)
- `created_at` - Job creation timestamp
- `media_file` - Attached media/images
- `applicants` - Number of applicants
- `lifecycle_status` - Current lifecycle status
- `summary` - Job summary

---

## 7. **To Display Jobs on Your Website**

### Option A: Using the Candidate Panel API
1. Integrate the candidate job search API endpoints
2. Add authentication mechanism
3. Parse JSON responses
4. Display on your website

### Option B: Create a Custom Public API
You may need to create a **public, un-authenticated API endpoint** like:
```
/api/public/jobs/
```

This would allow:
- Public job listings without login
- Website integration without candidate authentication
- Better SEO and visibility

---

## 8. **Notes**

- ✅ **Only "Approved" jobs** are visible to candidates
- ✅ Jobs can be filtered by: title, location, salary, experience, skills, job type
- ✅ Jobs can be sorted by: latest or salary (high to low)
- ✅ Match scoring is available for recommended jobs
- ✅ Candidates can save jobs for later
- ✅ All endpoints require proper authentication/authorization

---

## 9. **Recommendation**

Since you want to display jobs on your website without candidate login, I recommend:

**Create a new public API endpoint:**
- `GET /api/public/jobs/` - List all approved jobs (no auth required)
- `GET /api/public/jobs/<job_id>/` - Get job details (no auth required)

This would allow your website to fetch and display jobs independently without requiring candidates to be logged in to your dashboard.

Would you like me to create these public API endpoints for you?
