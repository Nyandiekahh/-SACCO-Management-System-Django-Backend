from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class Investment(models.Model):
    """
    Individual investment records for members
    """
    INVESTMENT_TYPES = (
        ('share_capital', 'Share Capital'),
        ('monthly_investment', 'Monthly Investment'),
        ('special_deposit', 'Special Deposit'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    )
    
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPES)
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Transaction details
    transaction_reference = models.CharField(max_length=100, blank=True)
    transaction_message = models.TextField(
        blank=True,
        help_text="Full transaction message from payment provider"
    )
    payment_method = models.CharField(max_length=50, blank=True)
    
    # Status and approval
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_investments'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'investment'
        verbose_name = 'Investment'
        verbose_name_plural = 'Investments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', 'investment_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.member.username} - {self.get_investment_type_display()} - ${self.amount}"

    def confirm_investment(self, admin_user, admin_notes=""):
        """
        Confirm the investment
        """
        if self.status != 'pending':
            raise ValueError("Only pending investments can be confirmed")
        
        self.status = 'confirmed'
        self.confirmed_by = admin_user
        self.confirmed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()
        
        # Create investment summary record or update existing
        InvestmentSummary.update_member_summary(self.member)

    def reject_investment(self, admin_user, rejection_reason, admin_notes=""):
        """
        Reject the investment
        """
        if self.status != 'pending':
            raise ValueError("Only pending investments can be rejected")
        
        self.status = 'rejected'
        self.confirmed_by = admin_user
        self.confirmed_at = timezone.now()
        self.rejection_reason = rejection_reason
        self.admin_notes = admin_notes
        self.save()

    @property
    def is_share_capital(self):
        return self.investment_type == 'share_capital'

    @property
    def is_monthly_investment(self):
        return self.investment_type == 'monthly_investment'

    def validate_share_capital_limit(self):
        """
        Validate share capital doesn't exceed the set limit
        """
        if self.is_share_capital:
            from sacco_settings.models import SaccoSettings
            settings = SaccoSettings.get_settings()
            
            existing_share_capital = Investment.objects.filter(
                member=self.member,
                investment_type='share_capital',
                status='confirmed'
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
            
            total_after_this = existing_share_capital + self.amount
            
            if total_after_this > settings.share_capital_amount:
                raise ValueError(
                    f"Share capital limit of ${settings.share_capital_amount} exceeded. "
                    f"Current: ${existing_share_capital}, Attempting: ${self.amount}"
                )

    def save(self, *args, **kwargs):
        # Validate share capital limit before saving
        if self.is_share_capital and self.status == 'pending':
            self.validate_share_capital_limit()
        
        super().save(*args, **kwargs)


class InvestmentSummary(models.Model):
    """
    Summary of member's investments by type
    """
    member = models.OneToOneField(User, on_delete=models.CASCADE, related_name='investment_summary')
    
    # Share capital totals
    total_share_capital = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Monthly investment totals
    total_monthly_investments = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Special deposits totals
    total_special_deposits = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Overall totals
    total_investments = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Loan eligibility calculation
    loan_eligible_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Amount eligible for loan calculation"
    )
    
    maximum_loan_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Maximum loan amount based on investments"
    )
    
    # Statistics
    first_investment_date = models.DateTimeField(null=True, blank=True)
    last_investment_date = models.DateTimeField(null=True, blank=True)
    total_investment_count = models.PositiveIntegerField(default=0)
    
    # Rankings
    ranking_by_total = models.PositiveIntegerField(null=True, blank=True)
    ranking_by_share_capital = models.PositiveIntegerField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'investment_summary'
        verbose_name = 'Investment Summary'
        verbose_name_plural = 'Investment Summaries'

    def __str__(self):
        return f"{self.member.username} Investment Summary - Total: ${self.total_investments}"

    @classmethod
    def update_member_summary(cls, member):
        """
        Update or create investment summary for a member
        """
        # Get all confirmed investments
        investments = Investment.objects.filter(
            member=member,
            status='confirmed'
        )
        
        # Calculate totals by type
        share_capital = investments.filter(
            investment_type='share_capital'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        monthly_investments = investments.filter(
            investment_type='monthly_investment'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        special_deposits = investments.filter(
            investment_type='special_deposit'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        total_investments = share_capital + monthly_investments + special_deposits
        
        # Calculate loan eligible amount (only share capital and monthly investments)
        loan_eligible_amount = share_capital + monthly_investments
        
        # Calculate maximum loan amount
        from sacco_settings.models import SaccoSettings
        settings = SaccoSettings.get_settings()
        maximum_loan_amount = loan_eligible_amount * settings.loan_multiplier
        
        # Get investment dates
        first_investment = investments.order_by('created_at').first()
        last_investment = investments.order_by('-created_at').first()
        
        # Update or create summary
        summary, created = cls.objects.update_or_create(
            member=member,
            defaults={
                'total_share_capital': share_capital,
                'total_monthly_investments': monthly_investments,
                'total_special_deposits': special_deposits,
                'total_investments': total_investments,
                'loan_eligible_amount': loan_eligible_amount,
                'maximum_loan_amount': maximum_loan_amount,
                'first_investment_date': first_investment.created_at if first_investment else None,
                'last_investment_date': last_investment.created_at if last_investment else None,
                'total_investment_count': investments.count(),
            }
        )
        
        return summary

    @classmethod
    def update_all_rankings(cls):
        """
        Update rankings for all members
        """
        # Ranking by total investments
        summaries = cls.objects.filter(
            total_investments__gt=0
        ).order_by('-total_investments')
        
        for rank, summary in enumerate(summaries, 1):
            summary.ranking_by_total = rank
            summary.save(update_fields=['ranking_by_total'])
        
        # Ranking by share capital
        summaries = cls.objects.filter(
            total_share_capital__gt=0
        ).order_by('-total_share_capital')
        
        for rank, summary in enumerate(summaries, 1):
            summary.ranking_by_share_capital = rank
            summary.save(update_fields=['ranking_by_share_capital'])


class InvestmentTarget(models.Model):
    """
    Investment targets set by members or admins
    """
    TARGET_TYPES = (
        ('personal', 'Personal Target'),
        ('sacco_wide', 'SACCO-wide Target'),
    )
    
    PERIOD_TYPES = (
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annual'),
    )
    
    target_type = models.CharField(max_length=15, choices=TARGET_TYPES)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Target amount and period
    target_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    period_type = models.CharField(max_length=15, choices=PERIOD_TYPES)
    
    # For personal targets
    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='investment_targets'
    )
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Progress tracking
    current_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_targets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'investment_target'
        verbose_name = 'Investment Target'
        verbose_name_plural = 'Investment Targets'
        ordering = ['-created_at']

    def __str__(self):
        if self.target_type == 'personal':
            return f"{self.member.username} - {self.name}"
        return f"SACCO Target - {self.name}"

    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.target_amount > 0:
            return min((self.current_amount / self.target_amount) * 100, 100)
        return 0

    @property
    def remaining_amount(self):
        """Calculate remaining amount to reach target"""
        return max(self.target_amount - self.current_amount, Decimal('0'))

    @property
    def is_achieved(self):
        """Check if target is achieved"""
        return self.current_amount >= self.target_amount

    def update_progress(self):
        """Update current progress for this target"""
        if self.target_type == 'personal' and self.member:
            # Calculate investments within the target period
            investments = Investment.objects.filter(
                member=self.member,
                status='confirmed',
                created_at__date__gte=self.start_date,
                created_at__date__lte=self.end_date
            )
            
            self.current_amount = investments.aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
        elif self.target_type == 'sacco_wide':
            # Calculate all member investments within the target period
            investments = Investment.objects.filter(
                status='confirmed',
                created_at__date__gte=self.start_date,
                created_at__date__lte=self.end_date
            )
            
            self.current_amount = investments.aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
        
        self.save(update_fields=['current_amount'])


class InvestmentTransaction(models.Model):
    """
    Detailed transaction log for investments
    """
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('interest', 'Interest Payment'),
        ('dividend', 'Dividend Payment'),
        ('fee', 'Fee Deduction'),
    )
    
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investment_transactions')
    investment = models.ForeignKey(
        Investment, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        null=True,
        blank=True
    )
    
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Balance tracking
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # Transaction details
    reference_number = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Related transaction (for transfers)
    related_transaction = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Processing details
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_investment_transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'investment_transaction'
        verbose_name = 'Investment Transaction'
        verbose_name_plural = 'Investment Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', 'created_at']),
            models.Index(fields=['reference_number']),
        ]

    def __str__(self):
        return f"{self.member.username} - {self.get_transaction_type_display()} - ${self.amount}"

    def save(self, *args, **kwargs):
        # Generate reference number if not provided
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        
        super().save(*args, **kwargs)

    def generate_reference_number(self):
        """Generate unique reference number"""
        import uuid
        return f"INV-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"


class DividendPayment(models.Model):
    """
    Annual dividend payments to members
    """
    year = models.PositiveIntegerField()
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dividend_payments')
    
    # Dividend calculation basis
    share_capital_amount = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_investment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_eligible_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Dividend rates
    share_capital_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_investment_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Calculated dividends
    share_capital_dividend = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_investment_dividend = models.DecimalField(max_digits=12, decimal_places=2)
    total_dividend = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment details
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Admin details
    calculated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='calculated_dividends'
    )
    paid_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_dividends'
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dividend_payment'
        verbose_name = 'Dividend Payment'
        verbose_name_plural = 'Dividend Payments'
        unique_together = ['year', 'member']
        ordering = ['-year', 'member__username']

    def __str__(self):
        return f"{self.member.username} - {self.year} Dividend - ${self.total_dividend}"

    @classmethod
    def calculate_dividends_for_year(cls, year, share_capital_rate, monthly_investment_rate, calculated_by):
        """
        Calculate dividends for all eligible members for a given year
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Get all members with investments
            members_with_investments = User.objects.filter(
                investments__status='confirmed',
                investments__created_at__year__lte=year,
                is_approved=True
            ).distinct()
            
            dividend_payments = []
            
            for member in members_with_investments:
                # Get member's investment summary up to the end of the year
                summary = InvestmentSummary.objects.filter(member=member).first()
                
                if not summary:
                    continue
                
                # Calculate dividends
                share_capital_dividend = (summary.total_share_capital * share_capital_rate / 100)
                monthly_investment_dividend = (summary.total_monthly_investments * monthly_investment_rate / 100)
                total_dividend = share_capital_dividend + monthly_investment_dividend
                
                if total_dividend > 0:
                    dividend_payment, created = cls.objects.update_or_create(
                        year=year,
                        member=member,
                        defaults={
                            'share_capital_amount': summary.total_share_capital,
                            'monthly_investment_amount': summary.total_monthly_investments,
                            'total_eligible_amount': summary.total_share_capital + summary.total_monthly_investments,
                            'share_capital_rate': share_capital_rate,
                            'monthly_investment_rate': monthly_investment_rate,
                            'share_capital_dividend': share_capital_dividend,
                            'monthly_investment_dividend': monthly_investment_dividend,
                            'total_dividend': total_dividend,
                            'calculated_by': calculated_by,
                        }
                    )
                    dividend_payments.append(dividend_payment)
            
            return dividend_payments