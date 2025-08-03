from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import json

User = get_user_model()


class Notification(models.Model):
    """
    In-app notifications for users
    """
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('reminder', 'Reminder'),
    )
    
    CATEGORIES = (
        ('application', 'Application'),
        ('investment', 'Investment'),
        ('loan', 'Loan'),
        ('payment', 'Payment'),
        ('system', 'System'),
        ('general', 'General'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    notification_type = models.CharField(max_length=15, choices=NOTIFICATION_TYPES, default='info')
    category = models.CharField(max_length=15, choices=CATEGORIES, default='general')
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Optional action button
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Related objects (for linking back to source)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['category', 'created_at']),
        ]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_notification(cls, recipient, title, message, notification_type='info', 
                          category='general', action_url='', action_text='', 
                          metadata=None, related_object=None, expires_days=None):
        """
        Create a new notification
        """
        expires_at = None
        if expires_days:
            expires_at = timezone.now() + timezone.timedelta(days=expires_days)
        
        related_object_type = None
        related_object_id = None
        if related_object:
            related_object_type = related_object.__class__.__name__
            related_object_id = related_object.id
        
        return cls.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            action_url=action_url,
            action_text=action_text,
            metadata=metadata or {},
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            expires_at=expires_at
        )

    @classmethod
    def cleanup_expired(cls):
        """Remove expired notifications"""
        cls.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()


class EmailNotification(models.Model):
    """
    Email notifications sent to users
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_notifications')
    recipient_email = models.EmailField()
    
    # Email content
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=100, blank=True)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    
    # Template context data
    template_context = models.JSONField(default=dict, blank=True)
    
    # Email metadata
    from_email = models.EmailField(default=settings.DEFAULT_FROM_EMAIL)
    reply_to = models.EmailField(blank=True)
    
    # Status and delivery
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    delivery_attempts = models.PositiveIntegerField(default=0)
    max_delivery_attempts = models.PositiveIntegerField(default=3)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    # Email provider info
    provider_message_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Related objects
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_notification'
        verbose_name = 'Email Notification'
        verbose_name_plural = 'Email Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['recipient', 'status']),
        ]

    def __str__(self):
        return f"{self.recipient_email} - {self.subject} - {self.get_status_display()}"

    def send_email(self):
        """Send the email notification"""
        if self.status != 'pending':
            raise ValueError("Only pending emails can be sent")
        
        try:
            # Increment delivery attempts
            self.delivery_attempts += 1
            self.last_attempt_at = timezone.now()
            
            # Send email
            success = send_mail(
                subject=self.subject,
                message=self.text_content,
                from_email=self.from_email,
                recipient_list=[self.recipient_email],
                html_message=self.html_content,
                fail_silently=False
            )
            
            if success:
                self.status = 'sent'
                self.sent_at = timezone.now()
                
                # Create in-app notification about email sent
                Notification.create_notification(
                    recipient=self.recipient,
                    title="Email Sent",
                    message=f"Email '{self.subject}' has been sent to {self.recipient_email}",
                    notification_type='info',
                    category='system'
                )
            else:
                self.status = 'failed'
                self.error_message = "Email sending failed"
            
            self.save()
            return success
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.save()
            
            # Check if we should retry
            if self.delivery_attempts < self.max_delivery_attempts:
                self.status = 'pending'
                self.save()
            
            return False

    @classmethod
    def create_from_template(cls, template_type, recipient, context_data, 
                           scheduled_for=None, priority='normal'):
        """
        Create email notification from template
        """
        from sacco_settings.models import EmailTemplate
        
        template = EmailTemplate.get_template(template_type)
        if not template:
            raise ValueError(f"Email template '{template_type}' not found")
        
        # Render template content
        subject = cls._render_template_string(template.subject, context_data)
        html_content = cls._render_template_string(template.body, context_data)
        
        # Create text version (strip HTML tags)
        import re
        text_content = re.sub('<[^<]+?>', '', html_content)
        
        return cls.objects.create(
            recipient=recipient,
            recipient_email=recipient.email,
            subject=subject,
            template_name=template_type,
            html_content=html_content,
            text_content=text_content,
            template_context=context_data,
            scheduled_for=scheduled_for,
            priority=priority
        )

    @staticmethod
    def _render_template_string(template_string, context):
        """Render template string with context variables"""
        from django.template import Template, Context
        
        template = Template(template_string)
        return template.render(Context(context))

    @classmethod
    def send_pending_emails(cls):
        """Send all pending emails that are due"""
        pending_emails = cls.objects.filter(
            status='pending',
            delivery_attempts__lt=models.F('max_delivery_attempts')
        ).filter(
            models.Q(scheduled_for__isnull=True) | 
            models.Q(scheduled_for__lte=timezone.now())
        )
        
        for email in pending_emails:
            email.send_email()


class NotificationPreference(models.Model):
    """
    User preferences for notifications
    """
    NOTIFICATION_METHODS = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_notifications_enabled = models.BooleanField(default=True)
    email_application_updates = models.BooleanField(default=True)
    email_investment_confirmations = models.BooleanField(default=True)
    email_loan_updates = models.BooleanField(default=True)
    email_payment_confirmations = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    email_system_updates = models.BooleanField(default=True)
    
    # SMS preferences
    sms_notifications_enabled = models.BooleanField(default=False)
    sms_urgent_only = models.BooleanField(default=True)
    sms_loan_reminders = models.BooleanField(default=True)
    sms_payment_confirmations = models.BooleanField(default=False)
    
    # In-app preferences
    in_app_notifications_enabled = models.BooleanField(default=True)
    in_app_auto_mark_read = models.BooleanField(default=False)
    
    # Frequency preferences
    digest_frequency = models.CharField(
        max_length=15,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('never', 'Never'),
        ],
        default='immediate'
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preference'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"{self.user.username} Notification Preferences"

    def should_send_email(self, notification_type):
        """Check if email should be sent for this notification type"""
        if not self.email_notifications_enabled:
            return False
        
        type_mapping = {
            'application': self.email_application_updates,
            'investment': self.email_investment_confirmations,
            'loan': self.email_loan_updates,
            'payment': self.email_payment_confirmations,
            'system': self.email_system_updates,
        }
        
        return type_mapping.get(notification_type, True)

    def should_send_sms(self, notification_type, is_urgent=False):
        """Check if SMS should be sent for this notification type"""
        if not self.sms_notifications_enabled:
            return False
        
        if self.sms_urgent_only and not is_urgent:
            return False
        
        return True

    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        current_time = timezone.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day quiet hours (e.g., 22:00 to 08:00)
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:
            # Overnight quiet hours (e.g., 22:00 to 08:00 next day)
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end


class NotificationTemplate(models.Model):
    """
    Templates for different types of notifications
    """
    TEMPLATE_TYPES = (
        ('application_approved', 'Application Approved'),
        ('application_rejected', 'Application Rejected'),
        ('application_more_info', 'Application - More Info Required'),
        ('investment_confirmed', 'Investment Confirmed'),
        ('investment_rejected', 'Investment Rejected'),
        ('loan_approved', 'Loan Approved'),
        ('loan_rejected', 'Loan Rejected'),
        ('loan_disbursed', 'Loan Disbursed'),
        ('loan_payment_due', 'Loan Payment Due'),
        ('loan_overdue', 'Loan Overdue'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('payment_rejected', 'Payment Rejected'),
        ('dividend_paid', 'Dividend Paid'),
        ('welcome_member', 'Welcome New Member'),
        ('password_reset', 'Password Reset'),
        ('account_locked', 'Account Locked'),
        ('system_maintenance', 'System Maintenance'),
    )
    
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES, unique=True)
    
    # In-app notification template
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    
    # Email subject template
    email_subject_template = models.CharField(max_length=255, blank=True)
    
    # SMS template
    sms_template = models.CharField(max_length=160, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=False)
    category = models.CharField(max_length=15, choices=Notification.CATEGORIES, default='general')
    
    # Action button config
    default_action_text = models.CharField(max_length=50, blank=True)
    default_action_url_pattern = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_template'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'

    def __str__(self):
        return f"{self.get_template_type_display()} Template"

    def render_notification(self, context_data):
        """Render notification content with context data"""
        from django.template import Template, Context
        
        title = Template(self.title_template).render(Context(context_data))
        message = Template(self.message_template).render(Context(context_data))
        
        action_url = ''
        if self.default_action_url_pattern:
            action_url = Template(self.default_action_url_pattern).render(Context(context_data))
        
        return {
            'title': title,
            'message': message,
            'action_text': self.default_action_text,
            'action_url': action_url,
            'category': self.category,
            'is_urgent': self.is_urgent
        }

    def render_email_subject(self, context_data):
        """Render email subject with context data"""
        if not self.email_subject_template:
            return None
        
        from django.template import Template, Context
        return Template(self.email_subject_template).render(Context(context_data))

    def render_sms(self, context_data):
        """Render SMS content with context data"""
        if not self.sms_template:
            return None
        
        from django.template import Template, Context
        return Template(self.sms_template).render(Context(context_data))

    @classmethod
    def get_template(cls, template_type):
        """Get active template by type"""
        try:
            return cls.objects.get(template_type=template_type, is_active=True)
        except cls.DoesNotExist:
            return None


class NotificationLog(models.Model):
    """
    Log of all notifications sent
    """
    ACTION_TYPES = (
        ('created', 'Created'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
        ('clicked', 'Clicked'),
    )
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True
    )
    email_notification = models.ForeignKey(
        EmailNotification,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True
    )
    
    action_type = models.CharField(max_length=15, choices=ACTION_TYPES)
    details = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # User context
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_log'
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.timestamp}"


class BulkNotification(models.Model):
    """
    Bulk notifications sent to multiple users
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    RECIPIENT_TYPES = (
        ('all_members', 'All Members'),
        ('approved_members', 'Approved Members Only'),
        ('specific_users', 'Specific Users'),
        ('user_group', 'User Group'),
        ('loan_defaulters', 'Loan Defaulters'),
        ('recent_investors', 'Recent Investors'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Targeting
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES)
    specific_recipients = models.ManyToManyField(
        User,
        blank=True,
        related_name='bulk_notifications_received'
    )
    
    # Delivery methods
    send_in_app = models.BooleanField(default=True)
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    
    # Email specific
    email_subject = models.CharField(max_length=255, blank=True)
    email_html_content = models.TextField(blank=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True)
    
    # Status and tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_bulk_notifications')
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_bulk_notifications'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bulk_notification'
        verbose_name = 'Bulk Notification'
        verbose_name_plural = 'Bulk Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def get_recipients(self):
        """Get list of recipients based on recipient type"""
        if self.recipient_type == 'all_members':
            return User.objects.filter(user_type='member')
        
        elif self.recipient_type == 'approved_members':
            return User.objects.filter(user_type='member', is_approved=True)
        
        elif self.recipient_type == 'specific_users':
            return self.specific_recipients.all()
        
        elif self.recipient_type == 'loan_defaulters':
            from loans.models import Loan
            defaulter_ids = Loan.objects.filter(
                status='defaulted'
            ).values_list('borrower_id', flat=True).distinct()
            return User.objects.filter(id__in=defaulter_ids)
        
        elif self.recipient_type == 'recent_investors':
            from investments.models import Investment
            recent_investor_ids = Investment.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30),
                status='confirmed'
            ).values_list('member_id', flat=True).distinct()
            return User.objects.filter(id__in=recent_investor_ids)
        
        return User.objects.none()

    def send_bulk_notification(self, sent_by):
        """Send the bulk notification to all recipients"""
        if self.status not in ['draft', 'scheduled']:
            raise ValueError("Only draft or scheduled notifications can be sent")
        
        recipients = self.get_recipients()
        self.total_recipients = recipients.count()
        self.status = 'sending'
        self.sent_by = sent_by
        self.sent_at = timezone.now()
        self.save()
        
        sent_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                # Create in-app notification
                if self.send_in_app:
                    Notification.create_notification(
                        recipient=recipient,
                        title=self.title,
                        message=self.message,
                        category='general',
                        related_object=self
                    )
                
                # Create email notification
                if self.send_email and recipient.email:
                    EmailNotification.objects.create(
                        recipient=recipient,
                        recipient_email=recipient.email,
                        subject=self.email_subject or self.title,
                        html_content=self.email_html_content or self.message,
                        text_content=self.message,
                        related_object_type='BulkNotification',
                        related_object_id=self.id
                    )
                
                # SMS would be implemented here if SMS service is configured
                
                sent_count += 1
                
            except Exception as e:
                failed_count += 1
                # Log the error
                NotificationLog.objects.create(
                    notification=None,
                    action_type='failed',
                    details=f"Failed to send bulk notification to {recipient.email}: {str(e)}",
                    metadata={'bulk_notification_id': self.id, 'recipient_id': recipient.id}
                )
        
        # Update final counts
        self.sent_count = sent_count
        self.failed_count = failed_count
        self.status = 'completed' if failed_count == 0 else 'failed'
        self.completed_at = timezone.now()
        self.save()

    def schedule_notification(self, scheduled_for):
        """Schedule the notification for later sending"""
        self.scheduled_for = scheduled_for
        self.status = 'scheduled'
        self.save()

    def cancel_notification(self):
        """Cancel the bulk notification"""
        if self.status in ['draft', 'scheduled']:
            self.status = 'cancelled'
            self.save()
        else:
            raise ValueError("Only draft or scheduled notifications can be cancelled")


class SMSNotification(models.Model):
    """
    SMS notifications (if SMS service is integrated)
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sms_notifications')
    phone_number = models.CharField(max_length=15)
    message = models.CharField(max_length=160)  # SMS character limit
    
    # Status and delivery
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Provider details
    provider_message_id = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    delivery_attempts = models.PositiveIntegerField(default=0)
    max_delivery_attempts = models.PositiveIntegerField(default=3)
    
    # Related objects
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sms_notification'
        verbose_name = 'SMS Notification'
        verbose_name_plural = 'SMS Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.message[:50]}... - {self.get_status_display()}"

    def send_sms(self):
        """Send SMS (implementation depends on SMS provider)"""
        # This would integrate with an SMS service provider
        # like Twilio, Africa's Talking, etc.
        pass


class NotificationSetting(models.Model):
    """
    Global notification settings for the SACCO
    """
    # Email settings
    email_notifications_enabled = models.BooleanField(default=True)
    default_sender_email = models.EmailField(blank=True)
    email_signature = models.TextField(blank=True)
    
    # SMS settings
    sms_notifications_enabled = models.BooleanField(default=False)
    sms_provider = models.CharField(max_length=50, blank=True)
    sms_sender_id = models.CharField(max_length=20, blank=True)
    
    # Batch processing settings
    batch_size = models.PositiveIntegerField(
        default=100,
        help_text="Number of notifications to process in each batch"
    )
    batch_interval_minutes = models.PositiveIntegerField(
        default=5,
        help_text="Interval between batch processing in minutes"
    )
    
    # Retry settings
    max_retry_attempts = models.PositiveIntegerField(default=3)
    retry_interval_minutes = models.PositiveIntegerField(default=30)
    
    # Cleanup settings
    auto_cleanup_enabled = models.BooleanField(default=True)
    cleanup_after_days = models.PositiveIntegerField(
        default=90,
        help_text="Days after which old notifications are cleaned up"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_setting'
        verbose_name = 'Notification Setting'
        verbose_name_plural = 'Notification Settings'

    def __str__(self):
        return "Notification Settings"

    def save(self, *args, **kwargs):
        # Ensure only one settings record exists
        if not self.pk and NotificationSetting.objects.exists():
            raise ValueError('Only one notification settings record is allowed')
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create notification settings"""
        settings, created = cls.objects.get_or_create(defaults={
            'email_notifications_enabled': True,
            'batch_size': 100,
            'batch_interval_minutes': 5,
            'max_retry_attempts': 3,
            'retry_interval_minutes': 30,
            'auto_cleanup_enabled': True,
            'cleanup_after_days': 90,
        })
        return settings