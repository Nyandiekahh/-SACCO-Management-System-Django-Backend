from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

User = get_user_model()


class LoanApplication(models.Model):
    """
    Loan applications submitted by members
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('cancelled', 'Cancelled'),
    )
    
    PURPOSE_CHOICES = (
        ('business', 'Business Investment'),
        ('education', 'Education'),
        ('emergency', 'Emergency'),
        ('personal', 'Personal Use'),
        ('agriculture', 'Agriculture'),
        ('housing', 'Housing/Rent'),
        ('medical', 'Medical'),
        ('other', 'Other'),
    )
    
    # Basic loan information
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_applications')
    loan_type = models.ForeignKey(
        'sacco_settings.LoanType',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    amount_requested = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))]
    )
    amount_approved = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    purpose_description = models.TextField()
    
    # Loan terms
    repayment_period_months = models.PositiveIntegerField()
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual interest rate (%)"
    )
    
    # Application status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    application_date = models.DateTimeField(auto_now_add=True)
    
    # Review details
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_loan_applications'
    )
    reviewed_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Disbursement details
    disbursed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disbursed_loans'
    )
    disbursement_date = models.DateTimeField(null=True, blank=True)
    disbursement_reference = models.CharField(max_length=100, blank=True)
    disbursement_transaction_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    disbursement_notes = models.TextField(blank=True)
    
    # Calculated fields
    monthly_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_interest = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_repayment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Supporting documents
    supporting_documents = models.FileField(
        upload_to='loan_documents/',
        null=True,
        blank=True
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_application'
        verbose_name = 'Loan Application'
        verbose_name_plural = 'Loan Applications'
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['status', 'application_date']),
        ]

    def __str__(self):
        return f"{self.applicant.username} - ${self.amount_requested} - {self.get_status_display()}"

    def calculate_loan_terms(self):
        """Calculate loan payment terms"""
        if not self.amount_approved or not self.interest_rate or not self.repayment_period_months:
            return
        
        principal = self.amount_approved
        monthly_rate = self.interest_rate / 100 / 12
        months = self.repayment_period_months
        
        if monthly_rate > 0:
            # Using compound interest formula
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        else:
            # Simple interest if rate is 0
            monthly_payment = principal / months
        
        self.monthly_payment = round(monthly_payment, 2)
        self.total_repayment = self.monthly_payment * months
        self.total_interest = self.total_repayment - principal
        
        self.save(update_fields=['monthly_payment', 'total_interest', 'total_repayment'])

    def check_eligibility(self):
        """Check if applicant is eligible for the loan"""
        errors = []
        
        # Check membership duration
        if not self.applicant.is_eligible_for_loan:
            from sacco_settings.models import SaccoSettings
            settings = SaccoSettings.get_settings()
            errors.append(f"Minimum membership of {settings.minimum_membership_months} months required")
        
        # Check investment-based loan limit
        try:
            summary = self.applicant.investment_summary
            if self.amount_requested > summary.maximum_loan_amount:
                errors.append(f"Maximum loan amount based on investments is ${summary.maximum_loan_amount}")
        except:
            errors.append("No investment summary found")
        
        # Check existing active loans
        active_loans = Loan.objects.filter(
            borrower=self.applicant,
            status__in=['active', 'overdue']
        )
        
        if active_loans.exists():
            errors.append("You have active loans that must be cleared first")
        
        # Check guarantor requirements if loan type requires it
        if self.loan_type and self.loan_type.requires_guarantor:
            guarantors = self.guarantors.filter(status='confirmed')
            total_guaranteed = guarantors.aggregate(
                total=models.Sum('guaranteed_amount')
            )['total'] or Decimal('0')
            
            if total_guaranteed < self.amount_requested:
                errors.append(f"Insufficient guarantor coverage. Required: ${self.amount_requested}, Guaranteed: ${total_guaranteed}")
        
        return errors

    def approve_loan(self, admin_user, approved_amount=None, interest_rate=None, notes=""):
        """Approve the loan application"""
        if self.status != 'pending':
            raise ValueError("Only pending applications can be approved")
        
        # Check eligibility
        eligibility_errors = self.check_eligibility()
        if eligibility_errors:
            raise ValueError(f"Eligibility check failed: {'; '.join(eligibility_errors)}")
        
        self.status = 'approved'
        self.amount_approved = approved_amount or self.amount_requested
        self.interest_rate = interest_rate or (self.loan_type.interest_rate if self.loan_type else None)
        self.reviewed_by = admin_user
        self.reviewed_date = timezone.now()
        self.review_notes = notes
        
        self.save()
        self.calculate_loan_terms()

    def reject_loan(self, admin_user, rejection_reason, notes=""):
        """Reject the loan application"""
        if self.status != 'pending':
            raise ValueError("Only pending applications can be rejected")
        
        self.status = 'rejected'
        self.rejection_reason = rejection_reason
        self.reviewed_by = admin_user
        self.reviewed_date = timezone.now()
        self.review_notes = notes
        
        self.save()

    def disburse_loan(self, admin_user, disbursement_reference, transaction_cost=None, notes=""):
        """Disburse the approved loan"""
        if self.status != 'approved':
            raise ValueError("Only approved loans can be disbursed")
        
        self.status = 'disbursed'
        self.disbursed_by = admin_user
        self.disbursement_date = timezone.now()
        self.disbursement_reference = disbursement_reference
        self.disbursement_transaction_cost = transaction_cost or Decimal('0')
        self.disbursement_notes = notes
        
        self.save()
        
        # Create the actual loan record
        loan = Loan.objects.create(
            application=self,
            borrower=self.applicant,
            principal_amount=self.amount_approved,
            interest_rate=self.interest_rate,
            repayment_period_months=self.repayment_period_months,
            monthly_payment=self.monthly_payment,
            total_interest=self.total_interest,
            total_amount=self.total_repayment,
            disbursement_date=self.disbursement_date,
            disbursement_reference=self.disbursement_reference,
            status='active'
        )
        
        return loan


class LoanGuarantor(models.Model):
    """
    Guarantors for loan applications
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn'),
    )
    
    loan_application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='guarantors'
    )
    guarantor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='guaranteed_loans'
    )
    
    guaranteed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    guaranteed_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))]
    )
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Guarantor response
    response_date = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)
    
    # Liability tracking
    is_liable = models.BooleanField(default=True)
    liability_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_guarantor'
        verbose_name = 'Loan Guarantor'
        verbose_name_plural = 'Loan Guarantors'
        unique_together = ['loan_application', 'guarantor']

    def __str__(self):
        return f"{self.guarantor.username} guaranteeing ${self.guaranteed_amount} for {self.loan_application.applicant.username}"

    def confirm_guarantee(self, notes=""):
        """Guarantor confirms to guarantee the loan"""
        self.status = 'confirmed'
        self.response_date = timezone.now()
        self.response_notes = notes
        self.save()

    def decline_guarantee(self, notes=""):
        """Guarantor declines to guarantee the loan"""
        self.status = 'declined'
        self.response_date = timezone.now()
        self.response_notes = notes
        self.save()

    def validate_guarantee_amount(self):
        """Validate that guarantee amount doesn't exceed loan amount"""
        if self.guaranteed_amount > self.loan_application.amount_requested:
            raise ValueError("Guaranteed amount cannot exceed loan amount")
        
        # Check total guarantees don't exceed 100%
        total_guarantees = LoanGuarantor.objects.filter(
            loan_application=self.loan_application
        ).exclude(id=self.id).aggregate(
            total=models.Sum('guaranteed_amount')
        )['total'] or Decimal('0')
        
        if (total_guarantees + self.guaranteed_amount) > self.loan_application.amount_requested:
            raise ValueError("Total guarantees exceed loan amount")

    def save(self, *args, **kwargs):
        # Calculate percentage
        if self.loan_application.amount_requested > 0:
            self.guaranteed_percentage = (self.guaranteed_amount / self.loan_application.amount_requested) * 100
        
        # Validate guarantee amount
        self.validate_guarantee_amount()
        
        super().save(*args, **kwargs)


class Loan(models.Model):
    """
    Active/disbursed loans
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paid_off', 'Paid Off'),
        ('overdue', 'Overdue'),
        ('defaulted', 'Defaulted'),
        ('written_off', 'Written Off'),
    )
    
    application = models.OneToOneField(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='loan'
    )
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    loan_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Loan details
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    repayment_period_months = models.PositiveIntegerField()
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2)
    total_interest = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment tracking
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_remaining = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Dates
    disbursement_date = models.DateTimeField()
    disbursement_reference = models.CharField(max_length=100)
    expected_completion_date = models.DateField()
    actual_completion_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    next_payment_date = models.DateField()
    last_payment_date = models.DateField(null=True, blank=True)
    
    # Penalties and fees
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_penalties_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan'
        verbose_name = 'Loan'
        verbose_name_plural = 'Loans'
        ordering = ['-disbursement_date']
        indexes = [
            models.Index(fields=['borrower', 'status']),
            models.Index(fields=['status', 'next_payment_date']),
        ]

    def __str__(self):
        return f"{self.loan_number} - {self.borrower.username} - ${self.principal_amount}"

    def save(self, *args, **kwargs):
        # Generate loan number
        if not self.loan_number:
            self.loan_number = self.generate_loan_number()
        
        # Calculate balance
        self.balance_remaining = self.total_amount - self.amount_paid
        
        # Calculate expected completion date
        if not self.expected_completion_date:
            from dateutil.relativedelta import relativedelta
            self.expected_completion_date = (self.disbursement_date + relativedelta(months=self.repayment_period_months)).date()
        
        # Set next payment date if not set
        if not self.next_payment_date:
            from dateutil.relativedelta import relativedelta
            self.next_payment_date = (self.disbursement_date + relativedelta(months=1)).date()
        
        super().save(*args, **kwargs)

    def generate_loan_number(self):
        """Generate unique loan number"""
        year = timezone.now().year
        
        # Get the last loan number for this year
        last_loan = Loan.objects.filter(
            loan_number__startswith=f'LN-{year}'
        ).order_by('-loan_number').first()
        
        if last_loan:
            try:
                last_number = int(last_loan.loan_number.split('-')[-1])
                new_number = last_number + 1
            except:
                new_number = 1
        else:
            new_number = 1
        
        return f'LN-{year}-{new_number:04d}'

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if self.status in ['paid_off', 'written_off']:
            return 0
        
        today = timezone.now().date()
        if today > self.next_payment_date:
            return (today - self.next_payment_date).days
        return 0

    @property
    def is_overdue(self):
        """Check if loan is overdue"""
        return self.days_overdue > 0

    def update_status(self):
        """Update loan status based on payments and dates"""
        if self.balance_remaining <= 0:
            self.status = 'paid_off'
            self.actual_completion_date = timezone.now().date()
        elif self.is_overdue:
            if self.days_overdue > 90:  # Consider defaulted after 90 days
                self.status = 'defaulted'
            else:
                self.status = 'overdue'
        else:
            self.status = 'active'
        
        self.save(update_fields=['status', 'actual_completion_date'])


class LoanPayment(models.Model):
    """
    Loan repayment records
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    )
    
    PAYMENT_TYPES = (
        ('regular', 'Regular Payment'),
        ('partial', 'Partial Payment'),
        ('full', 'Full Payment'),
        ('penalty', 'Penalty Payment'),
    )
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    payment_type = models.CharField(max_length=15, choices=PAYMENT_TYPES, default='regular')
    
    # Transaction details
    transaction_reference = models.CharField(max_length=100)
    transaction_message = models.TextField(
        blank=True,
        help_text="Full transaction message from payment provider"
    )
    payment_method = models.CharField(max_length=50, blank=True)
    
    # Status and confirmation
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_loan_payments'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Payment allocation
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    payment_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_payment'
        verbose_name = 'Loan Payment'
        verbose_name_plural = 'Loan Payments'
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.loan.loan_number} - ${self.amount} - {self.get_status_display()}"

    def confirm_payment(self, admin_user, admin_notes=""):
        """Confirm the loan payment"""
        if self.status != 'pending':
            raise ValueError("Only pending payments can be confirmed")
        
        # Calculate payment allocation
        self.allocate_payment()
        
        # Update payment status
        self.status = 'confirmed'
        self.confirmed_by = admin_user
        self.confirmed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()
        
        # Update loan totals
        self.update_loan_balance()
        
        # Update next payment date
        self.update_next_payment_date()

    def reject_payment(self, admin_user, rejection_reason, admin_notes=""):
        """Reject the loan payment"""
        if self.status != 'pending':
            raise ValueError("Only pending payments can be rejected")
        
        self.status = 'rejected'
        self.confirmed_by = admin_user
        self.confirmed_at = timezone.now()
        self.rejection_reason = rejection_reason
        self.admin_notes = admin_notes
        self.save()

    def allocate_payment(self):
        """Allocate payment between penalty, interest, and principal"""
        remaining_amount = self.amount
        
        # First, pay penalties
        pending_penalties = self.loan.penalty_amount - self.loan.total_penalties_paid
        if pending_penalties > 0 and remaining_amount > 0:
            penalty_payment = min(pending_penalties, remaining_amount)
            self.penalty_amount = penalty_payment
            remaining_amount -= penalty_payment
        
        # Then, pay interest (simplified allocation)
        if remaining_amount > 0:
            # Calculate remaining interest
            total_interest_due = self.loan.total_interest
            interest_paid = LoanPayment.objects.filter(
                loan=self.loan,
                status='confirmed'
            ).aggregate(total=models.Sum('interest_amount'))['total'] or Decimal('0')
            
            remaining_interest = total_interest_due - interest_paid
            
            if remaining_interest > 0:
                interest_payment = min(remaining_interest, remaining_amount)
                self.interest_amount = interest_payment
                remaining_amount -= interest_payment
        
        # Finally, pay principal
        if remaining_amount > 0:
            self.principal_amount = remaining_amount

    def update_loan_balance(self):
        """Update loan balance after payment confirmation"""
        # Update loan amounts paid
        self.loan.amount_paid += self.amount
        self.loan.total_penalties_paid += self.penalty_amount
        
        # Update last payment date
        self.loan.last_payment_date = self.payment_date.date()
        
        # Update loan status
        self.loan.update_status()

    def update_next_payment_date(self):
        """Update next payment date for the loan"""
        if self.loan.status == 'paid_off':
            return
        
        # Move next payment date by one month
        from dateutil.relativedelta import relativedelta
        self.loan.next_payment_date = self.loan.next_payment_date + relativedelta(months=1)
        self.loan.save(update_fields=['next_payment_date'])


class LoanSchedule(models.Model):
    """
    Loan repayment schedule
    """
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedule')
    payment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    
    # Scheduled amounts
    scheduled_payment = models.DecimalField(max_digits=12, decimal_places=2)
    principal_portion = models.DecimalField(max_digits=12, decimal_places=2)
    interest_portion = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Running balance
    beginning_balance = models.DecimalField(max_digits=12, decimal_places=2)
    ending_balance = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Actual payment tracking
    actual_payment = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    payment_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loan_schedule'
        verbose_name = 'Loan Schedule'
        verbose_name_plural = 'Loan Schedules'
        unique_together = ['loan', 'payment_number']
        ordering = ['loan', 'payment_number']

    def __str__(self):
        return f"{self.loan.loan_number} - Payment {self.payment_number}"

    @classmethod
    def generate_schedule(cls, loan):
        """Generate repayment schedule for a loan"""
        from dateutil.relativedelta import relativedelta
        
        # Clear existing schedule
        cls.objects.filter(loan=loan).delete()
        
        balance = loan.principal_amount
        payment_date = loan.disbursement_date.date()
        monthly_rate = loan.interest_rate / 100 / 12
        
        schedule_items = []
        
        for payment_num in range(1, loan.repayment_period_months + 1):
            payment_date = payment_date + relativedelta(months=1)
            
            # Calculate interest and principal portions
            interest_portion = balance * monthly_rate
            principal_portion = loan.monthly_payment - interest_portion
            
            # Adjust last payment to clear remaining balance
            if payment_num == loan.repayment_period_months:
                principal_portion = balance
                scheduled_payment = interest_portion + principal_portion
            else:
                scheduled_payment = loan.monthly_payment
            
            ending_balance = balance - principal_portion
            
            schedule_items.append(cls(
                loan=loan,
                payment_number=payment_num,
                due_date=payment_date,
                scheduled_payment=scheduled_payment,
                principal_portion=principal_portion,
                interest_portion=interest_portion,
                beginning_balance=balance,
                ending_balance=ending_balance
            ))
            
            balance = ending_balance
        
        # Bulk create schedule items
        cls.objects.bulk_create(schedule_items)
        
        return schedule_items


class LoanPenalty(models.Model):
    """
    Penalties applied to overdue loans
    """
    PENALTY_TYPES = (
        ('late_payment', 'Late Payment Fee'),
        ('overdue_interest', 'Overdue Interest'),
        ('processing_fee', 'Processing Fee'),
        ('other', 'Other'),
    )
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='penalties')
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Calculation basis
    days_overdue = models.PositiveIntegerField(default=0)
    penalty_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Penalty rate used for calculation"
    )
    
    description = models.TextField()
    applied_by = models.ForeignKey(User, on_delete=models.CASCADE)
    applied_date = models.DateTimeField(auto_now_add=True)
    
    is_waived = models.BooleanField(default=False)
    waived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waived_penalties'
    )
    waived_date = models.DateTimeField(null=True, blank=True)
    waiver_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'loan_penalty'
        verbose_name = 'Loan Penalty'
        verbose_name_plural = 'Loan Penalties'
        ordering = ['-applied_date']

    def __str__(self):
        return f"{self.loan.loan_number} - {self.get_penalty_type_display()} - ${self.amount}"

    def waive_penalty(self, admin_user, reason=""):
        """Waive the penalty"""
        self.is_waived = True
        self.waived_by = admin_user
        self.waived_date = timezone.now()
        self.waiver_reason = reason
        self.save()
        
        # Update loan penalty amount
        self.loan.penalty_amount = self.loan.penalties.filter(
            is_waived=False
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        self.loan.save(update_fields=['penalty_amount'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update loan penalty amount
        if not self.is_waived:
            self.loan.penalty_amount = self.loan.penalties.filter(
                is_waived=False
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
            self.loan.save(update_fields=['penalty_amount'])


class LoanCollateral(models.Model):
    """
    Collateral for secured loans
    """
    COLLATERAL_TYPES = (
        ('property', 'Property/Real Estate'),
        ('vehicle', 'Vehicle'),
        ('equipment', 'Equipment/Machinery'),
        ('savings', 'Savings/Deposits'),
        ('shares', 'Shares/Securities'),
        ('other', 'Other'),
    )
    
    loan_application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='collateral'
    )
    
    collateral_type = models.CharField(max_length=20, choices=COLLATERAL_TYPES)
    description = models.TextField()
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Documentation
    ownership_documents = models.FileField(
        upload_to='collateral_docs/',
        null=True,
        blank=True
    )
    valuation_report = models.FileField(
        upload_to='collateral_valuations/',
        null=True,
        blank=True
    )
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_collateral'
        verbose_name = 'Loan Collateral'
        verbose_name_plural = 'Loan Collateral'

    def __str__(self):
        return f"{self.loan_application.applicant.username} - {self.get_collateral_type_display()} - ${self.estimated_value}"

    def verify_collateral(self, admin_user, notes=""):
        """Verify the collateral"""
        self.is_verified = True
        self.verified_by = admin_user
        self.verification_date = timezone.now()
        self.verification_notes = notes
        self.save()


class LoanComment(models.Model):
    """
    Comments and notes on loans
    """
    COMMENT_TYPES = (
        ('general', 'General Comment'),
        ('payment_reminder', 'Payment Reminder'),
        ('follow_up', 'Follow Up'),
        ('collection', 'Collection Note'),
        ('system', 'System Generated'),
    )
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='comments')
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='general')
    comment = models.TextField()
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_private = models.BooleanField(
        default=True,
        help_text="Private comments are only visible to admins"
    )
    
    # For follow-up tracking
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = 'loan_comment'
        verbose_name = 'Loan Comment'
        verbose_name_plural = 'Loan Comments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan.loan_number} - {self.get_comment_type_display()}"