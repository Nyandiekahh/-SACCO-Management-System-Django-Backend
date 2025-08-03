from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MemberApplication(models.Model):
    """
    Member application for joining the SACCO
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('more_info_required', 'More Information Required'),
    )
    
    EMPLOYMENT_STATUS_CHOICES = (
        ('employed', 'Employed'),
        ('self_employed', 'Self Employed'),
        ('student', 'Student'),
        ('unemployed', 'Unemployed'),
        ('retired', 'Retired'),
    )
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    date_of_birth = models.DateField()
    id_number = models.CharField(max_length=20, unique=True)
    
    # Employment/Education Information
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES)
    employer_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    school_name = models.CharField(max_length=200, blank=True)
    course_of_study = models.CharField(max_length=100, blank=True)
    year_of_study = models.CharField(max_length=20, blank=True)
    
    # Next of Kin Information
    next_of_kin_name = models.CharField(max_length=100)
    next_of_kin_phone = models.CharField(max_length=15)
    next_of_kin_relationship = models.CharField(max_length=50)
    next_of_kin_address = models.TextField()
    
    # KYC Documents
    profile_image = models.ImageField(upload_to='applications/profiles/')
    id_document = models.ImageField(upload_to='applications/ids/')
    id_with_photo = models.ImageField(upload_to='applications/id_photos/')
    
    # Application Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    application_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_applications'
    )
    
    # Admin notes and feedback
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    required_information = models.TextField(
        blank=True,
        help_text="Information required from applicant"
    )
    
    # Created user (set when approved)
    created_user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application'
    )
    
    # Additional fields
    referral_member = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals',
        help_text="Member who referred this applicant"
    )
    
    terms_accepted = models.BooleanField(default=False)
    privacy_accepted = models.BooleanField(default=False)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'member_application'
        verbose_name = 'Member Application'
        verbose_name_plural = 'Member Applications'
        ordering = ['-application_date']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_status_display()}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def days_since_application(self):
        return (timezone.now() - self.application_date).days

    def approve_application(self, admin_user, admin_notes=""):
        """
        Approve the application and create user account
        """
        if self.status != 'pending':
            raise ValueError("Only pending applications can be approved")
        
        # Create username from email
        username = self.email.split('@')[0]
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user account
        user = User.objects.create_user(
            username=username,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            phone_number=self.phone_number,
            address=self.address,
            employment_status=f"{self.get_employment_status_display()}",
            school_name=self.school_name,
            profile_image=self.profile_image,
            id_document=self.id_document,
            id_with_photo=self.id_with_photo,
            is_approved=True,
            user_type='member'
        )
        
        # Create user profile
        from accounts.models import UserProfile
        UserProfile.objects.create(
            user=user,
            date_of_birth=self.date_of_birth,
            id_number=self.id_number,
            next_of_kin_name=self.next_of_kin_name,
            next_of_kin_phone=self.next_of_kin_phone,
            next_of_kin_relationship=self.next_of_kin_relationship,
            occupation=self.job_title or self.course_of_study,
            monthly_income=self.monthly_income
        )
        
        # Update application
        self.status = 'approved'
        self.reviewed_date = timezone.now()
        self.reviewed_by = admin_user
        self.admin_notes = admin_notes
        self.created_user = user
        self.save()
        
        return user

    def reject_application(self, admin_user, rejection_reason, admin_notes=""):
        """
        Reject the application
        """
        if self.status != 'pending':
            raise ValueError("Only pending applications can be rejected")
        
        self.status = 'rejected'
        self.reviewed_date = timezone.now()
        self.reviewed_by = admin_user
        self.rejection_reason = rejection_reason
        self.admin_notes = admin_notes
        self.save()

    def request_more_info(self, admin_user, required_information, admin_notes=""):
        """
        Request more information from applicant
        """
        if self.status != 'pending':
            raise ValueError("Can only request more info for pending applications")
        
        self.status = 'more_info_required'
        self.reviewed_date = timezone.now()
        self.reviewed_by = admin_user
        self.required_information = required_information
        self.admin_notes = admin_notes
        self.save()


class ApplicationDocument(models.Model):
    """
    Additional documents uploaded by applicants
    """
    DOCUMENT_TYPES = (
        ('payslip', 'Payslip'),
        ('bank_statement', 'Bank Statement'),
        ('employment_letter', 'Employment Letter'),
        ('student_id', 'Student ID'),
        ('additional_id', 'Additional ID Document'),
        ('other', 'Other'),
    )
    
    application = models.ForeignKey(
        MemberApplication,
        on_delete=models.CASCADE,
        related_name='additional_documents'
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='applications/documents/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'application_document'
        verbose_name = 'Application Document'
        verbose_name_plural = 'Application Documents'

    def __str__(self):
        return f"{self.application.full_name} - {self.get_document_type_display()}"


class ApplicationFollowUp(models.Model):
    """
    Follow-up communications with applicants
    """
    COMMUNICATION_TYPES = (
        ('email', 'Email'),
        ('phone', 'Phone Call'),
        ('sms', 'SMS'),
        ('in_person', 'In Person'),
    )
    
    application = models.ForeignKey(
        MemberApplication,
        on_delete=models.CASCADE,
        related_name='follow_ups'
    )
    communication_type = models.CharField(max_length=15, choices=COMMUNICATION_TYPES)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    response_received = models.BooleanField(default=False)
    response_date = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'application_follow_up'
        verbose_name = 'Application Follow Up'
        verbose_name_plural = 'Application Follow Ups'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.application.full_name} - {self.subject}"


class ApplicationComment(models.Model):
    """
    Internal comments on applications by admin users
    """
    application = models.ForeignKey(
        MemberApplication,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    comment = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(
        default=True,
        help_text="Private comments are only visible to admins"
    )

    class Meta:
        db_table = 'application_comment'
        verbose_name = 'Application Comment'
        verbose_name_plural = 'Application Comments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment on {self.application.full_name} by {self.created_by.username}"