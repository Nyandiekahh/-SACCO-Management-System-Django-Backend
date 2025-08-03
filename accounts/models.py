from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    USER_TYPES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='member')
    is_approved = models.BooleanField(default=False)
    date_approved = models.DateTimeField(null=True, blank=True)
    member_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # Profile fields
    address = models.TextField(blank=True)
    employment_status = models.CharField(max_length=100, blank=True)
    school_name = models.CharField(max_length=200, blank=True)
    
    # KYC Documents
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    id_document = models.ImageField(upload_to='ids/', null=True, blank=True)
    id_with_photo = models.ImageField(upload_to='id_photos/', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number']

    class Meta:
        db_table = 'custom_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} - {self.email}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def membership_duration(self):
        """Calculate membership duration in months"""
        if not self.date_approved:
            return 0
        duration = timezone.now() - self.date_approved
        return duration.days // 30

    @property
    def is_eligible_for_loan(self):
        """Check if user meets minimum membership requirements"""
        from sacco_settings.models import SaccoSettings
        try:
            settings = SaccoSettings.objects.first()
            if settings and settings.minimum_membership_months:
                return self.membership_duration >= settings.minimum_membership_months
        except:
            pass
        return False

    def generate_member_number(self):
        """Generate unique member number"""
        if not self.member_number:
            # Format: SACCO-YYYY-NNNN
            current_year = timezone.now().year
            last_member = CustomUser.objects.filter(
                member_number__isnull=False
            ).order_by('-id').first()
            
            if last_member and last_member.member_number:
                try:
                    last_number = int(last_member.member_number.split('-')[-1])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.member_number = f"SACCO-{current_year}-{new_number:04d}"
            self.save(update_fields=['member_number'])

    def save(self, *args, **kwargs):
        # Set date_approved when user is approved
        if self.is_approved and not self.date_approved:
            self.date_approved = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Generate member number after saving
        if self.is_approved and not self.member_number:
            self.generate_member_number()


class UserProfile(models.Model):
    """
    Extended profile information for users
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    id_number = models.CharField(max_length=20, unique=True)
    next_of_kin_name = models.CharField(max_length=100, blank=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True)
    next_of_kin_relationship = models.CharField(max_length=50, blank=True)
    
    # Additional KYC fields
    occupation = models.CharField(max_length=100, blank=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} Profile"


class UserActivity(models.Model):
    """
    Track user activities and login history
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_activity'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"