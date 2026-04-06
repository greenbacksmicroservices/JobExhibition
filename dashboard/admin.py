from django.contrib import admin

from .models import (
    Advertisement,
    AdminProfile,
    AssignedJob,
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateProject,
    CandidateResume,
    CandidateSkill,
    Company,
    Consultancy,
    ConsultancyKycDocument,
    Feedback,
    Interview,
    Message,
    MessageThread,
    PaymentEventLog,
    PasswordResetToken,
    SubscriptionPayment,
)

admin.site.register(Company)
admin.site.register(Consultancy)
admin.site.register(Candidate)
admin.site.register(CandidateResume)
admin.site.register(CandidateCertification)
admin.site.register(CandidateEducation)
admin.site.register(CandidateExperience)
admin.site.register(CandidateSkill)
admin.site.register(CandidateProject)
admin.site.register(Interview)
admin.site.register(Feedback)
admin.site.register(Advertisement)
admin.site.register(AssignedJob)
admin.site.register(MessageThread)
admin.site.register(Message)
admin.site.register(PasswordResetToken)
admin.site.register(ConsultancyKycDocument)
admin.site.register(AdminProfile)
admin.site.register(SubscriptionPayment)
admin.site.register(PaymentEventLog)
