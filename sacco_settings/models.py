from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class SaccoSettings(models.Model):
    """
    Main SACCO configuration settings
    """
    # Basic SACCO Information
    sacco_name = models.CharField(max_length=200, default="My SACCO")
    sacco_description = models.TextField(blank=True)
    sacco_logo = models.ImageField(upload_to='sacco/', null=True, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    
    # Contact Information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Membership Settings
    minimum_membership_months = models.PositiveIntegerField(
        default=3,
        help_text="Minimum months of membership required to apply for loans"
    )
    
    # Share Capital Settings
    share_capital_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=5000.00,
        validators=[MinValueValidator(0)],
        help_text="Fixed share capital amount per member"
    )
    
    # Loan Settings
    loan_multiplier = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=3.00,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Multiplier for calculating maximum loan amount based on investments"
    )
    
    default_loan_interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=12.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default annual interest rate for loans (%)"
    )
    
    maximum_loan_period_months = models.PositiveIntegerField(
        default=12,
        help_text="Maximum loan repayment period in months"
    )
    
    # Guarantor Settings
    require_guarantors = models.BooleanField(
        default=True,
        help_text="Whether loans require guarantors"
    )
    
    minimum_guarantor_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=25.00,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Minimum percentage a single guarantor can guarantee"
    )
    
    # Investment Settings
    allow_multiple_monthly_investments = models.BooleanField(
        default=True,
        help_text="Allow multiple monthly investments per month"
    )
    
    minimum_monthly_investment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0)],
        help_text="Minimum amount for monthly investments"
    )
    
    # System Settings
    auto_approve_deposits = models.BooleanField(
        default=False,
        help_text="Automatically approve deposit transactions"
    )
    
    send_email_notifications = models.BooleanField(
        default=True,
        help_text="Send email notifications for various activities"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'accounts.CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='settings_updates'
    )

    class Meta:
        db_table = 'sacco_settings'
        verbose_name = 'SACCO Settings'
        verbose_name_plural = 'SACCO Settings'

    def __str__(self):
        return f"{self.sacco_name} Settings"

    def save(self, *args, **kwargs):
        # Ensure only one settings record exists
        if not self.pk and SaccoSettings.objects.exists():
            raise ValidationError('Only one SACCO settings record is allowed')
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create SACCO settings"""
        settings, created = cls.objects.get_or_create(defaults={
            'sacco_name': 'My SACCO',
            'minimum_membership_months': 3,
            'share_capital_amount': 5000.00,
            'loan_multiplier': 3.00,
            'default_loan_interest_rate': 12.00,
            'maximum_loan_period_months': 12,
        })
        return settings


class LoanType(models.Model):
    """
    Different types of loans offered by the SACCO
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Annual interest rate (%)"
    )
    maximum_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Maximum loan amount for this type"
    )
    maximum_period_months = models.PositiveIntegerField(
        help_text="Maximum repayment period in months"
    )
    minimum_membership_months = models.PositiveIntegerField(
        default=3,
        help_text="Minimum membership required for this loan type"
    )
    requires_guarantor = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_type'
        verbose_name = 'Loan Type'
        verbose_name_plural = 'Loan Types'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.interest_rate}%"


class InvestmentType(models.Model):
    """
    Different types of investments in the SACCO
    """
    INVESTMENT_CATEGORIES = (
        ('share_capital', 'Share Capital'),
        ('monthly_investment', 'Monthly Investment'),
        ('special_deposit', 'Special Deposit'),
    )
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=INVESTMENT_CATEGORIES)
    description = models.TextField(blank=True)
    
    # For share capital - fixed amount
    fixed_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Fixed amount for share capital type investments"
    )
    
    # For monthly investments - minimum amount
    minimum_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum amount for flexible investments"
    )
    
    # Interest/dividend settings
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Annual interest/dividend rate (%)"
    )
    
    # Contribution to loan eligibility
    counts_for_loan_calculation = models.BooleanField(
        default=True,
        help_text="Whether this investment type counts towards loan eligibility"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'investment_type'
        verbose_name = 'Investment Type'
        verbose_name_plural = 'Investment Types'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class EmailTemplate(models.Model):
    """
    Email templates for different notifications
    """
    TEMPLATE_TYPES = (
        ('application_approved', 'Application Approved'),
        ('application_rejected', 'Application Rejected'),
        ('application_pending_info', 'Application Pending - More Info Required'),
        ('loan_approved', 'Loan Approved'),
        ('loan_rejected', 'Loan Rejected'),
        ('loan_disbursed', 'Loan Disbursed'),
        ('deposit_confirmed', 'Deposit Confirmed'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('welcome_member', 'Welcome New Member'),
        ('password_reset', 'Password Reset'),
    )
    
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField(help_text="Use {{variable_name}} for dynamic content")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_template'
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'

    def __str__(self):
        return f"{self.get_template_type_display()} Template"

    @classmethod
    def get_template(cls, template_type):
        """Get email template by type"""
        try:
            return cls.objects.get(template_type=template_type, is_active=True)
        except cls.DoesNotExist:
            return None


class SystemConfiguration(models.Model):
    """
    Additional system-wide configurations
    """
    # File upload settings
    max_file_size_mb = models.PositiveIntegerField(
        default=5,
        help_text="Maximum file size for uploads in MB"
    )
    
    allowed_file_types = models.CharField(
        max_length=200,
        default="jpg,jpeg,png,pdf",
        help_text="Comma-separated list of allowed file extensions"
    )
    
    # Security settings
    session_timeout_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Session timeout in minutes"
    )
    
    max_login_attempts = models.PositiveIntegerField(
        default=5,
        help_text="Maximum failed login attempts before account lockout"
    )
    
    account_lockout_duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Account lockout duration in minutes"
    )
    
    # Backup settings
    auto_backup_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic database backups"
    )
    
    backup_frequency_days = models.PositiveIntegerField(
        default=7,
        help_text="Backup frequency in days"
    )
    
    # Maintenance mode
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="Enable maintenance mode"
    )
    
    maintenance_message = models.TextField(
        blank=True,
        help_text="Message to display during maintenance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_configuration'
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configuration'

    def __str__(self):
        return "System Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one configuration record exists
        if not self.pk and SystemConfiguration.objects.exists():
            raise ValidationError('Only one system configuration record is allowed')
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get or create system configuration"""
        config, created = cls.objects.get_or_create(defaults={
            'max_file_size_mb': 5,
            'allowed_file_types': 'jpg,jpeg,png,pdf',
            'session_timeout_minutes': 60,
            'max_login_attempts': 5,
            'account_lockout_duration_minutes': 30,
        })
        return config