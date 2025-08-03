from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

User = get_user_model()


class Transaction(models.Model):
    """
    Master transaction table for all financial transactions
    """
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('loan_payment', 'Loan Payment'),
        ('dividend_payment', 'Dividend Payment'),
        ('fee_payment', 'Fee Payment'),
        ('penalty_payment', 'Penalty Payment'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Balance Adjustment'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('reversed', 'Reversed'),
    )
    
    TRANSACTION_CATEGORIES = (
        ('investment', 'Investment'),
        ('loan', 'Loan'),
        ('fee', 'Fee'),
        ('penalty', 'Penalty'),
        ('dividend', 'Dividend'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
    )
    
    # Basic transaction info
    transaction_id = models.CharField(max_length=50, unique=True, blank=True)
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=15, choices=TRANSACTION_CATEGORIES)
    
    # Amount and currency
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='KES')
    
    # Transaction details
    description = models.TextField()
    reference_number = models.CharField(max_length=100, blank=True)
    external_reference = models.CharField(max_length=100, blank=True)
    
    # Status and processing
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Balance tracking
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Payment method and provider info
    payment_method = models.CharField(max_length=50, blank=True)
    payment_provider = models.CharField(max_length=50, blank=True)
    transaction_message = models.TextField(blank=True)
    
    # Processing details
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_transactions'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_notes = models.TextField(blank=True)
    
    # Related objects (generic foreign keys could be used here for flexibility)
    related_investment_id = models.PositiveIntegerField(null=True, blank=True)
    related_loan_id = models.PositiveIntegerField(null=True, blank=True)
    related_loan_payment_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Reversal tracking
    reversed_transaction = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversal_transactions'
    )
    reversal_reason = models.TextField(blank=True)
    
    # Timestamps
    transaction_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transaction'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['member', 'transaction_date']),
            models.Index(fields=['status', 'transaction_date']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['reference_number']),
        ]

    def __str__(self):
        return f"{self.transaction_id} - {self.member.username} - {self.get_transaction_type_display()} - ${self.amount}"

    def save(self, *args, **kwargs):
        # Generate transaction ID if not provided
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        
        super().save(*args, **kwargs)

    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        prefix_map = {
            'deposit': 'DEP',
            'withdrawal': 'WDR',
            'loan_disbursement': 'LDR',
            'loan_payment': 'LPY',
            'dividend_payment': 'DIV',
            'fee_payment': 'FEE',
            'penalty_payment': 'PEN',
            'transfer_in': 'TIN',
            'transfer_out': 'TOU',
            'adjustment': 'ADJ',
        }
        
        prefix = prefix_map.get(self.transaction_type, 'TXN')
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_part = str(uuid.uuid4())[:6].upper()
        
        return f"{prefix}-{timestamp}-{random_part}"

    def complete_transaction(self, processed_by=None, notes=""):
        """Mark transaction as completed and update balances"""
        if self.status != 'pending':
            raise ValueError("Only pending transactions can be completed")
        
        # Calculate new balance
        current_balance = self.get_member_balance()
        self.balance_before = current_balance
        
        if self.transaction_type in ['deposit', 'loan_disbursement', 'dividend_payment', 'transfer_in']:
            self.balance_after = current_balance + self.amount
        else:
            self.balance_after = current_balance - self.amount
        
        # Update status
        self.status = 'completed'
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        self.processing_notes = notes
        
        self.save()
        
        # Update member's account balance
        self.update_member_balance()

    def fail_transaction(self, processed_by=None, reason=""):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        self.processing_notes = reason
        self.save()

    def reverse_transaction(self, processed_by=None, reason=""):
        """Reverse a completed transaction"""
        if self.status != 'completed':
            raise ValueError("Only completed transactions can be reversed")
        
        # Create reversal transaction
        reversal = Transaction.objects.create(
            member=self.member,
            transaction_type=self.get_reverse_transaction_type(),
            category=self.category,
            amount=self.amount,
            description=f"Reversal of {self.transaction_id}: {reason}",
            reference_number=f"REV-{self.reference_number}",
            status='completed',
            processed_by=processed_by,
            processed_at=timezone.now(),
            processing_notes=f"Reversal: {reason}",
            reversed_transaction=self,
        )
        
        # Update original transaction
        self.status = 'reversed'
        self.reversal_reason = reason
        self.save()
        
        return reversal

    def get_reverse_transaction_type(self):
        """Get the reverse transaction type"""
        reverse_map = {
            'deposit': 'withdrawal',
            'withdrawal': 'deposit',
            'loan_disbursement': 'adjustment',  # Admin adjustment
            'loan_payment': 'adjustment',  # Admin adjustment
            'transfer_in': 'transfer_out',
            'transfer_out': 'transfer_in',
        }
        return reverse_map.get(self.transaction_type, 'adjustment')

    def get_member_balance(self):
        """Get member's current balance"""
        try:
            balance = MemberBalance.objects.get(member=self.member)
            return balance.current_balance
        except MemberBalance.DoesNotExist:
            return Decimal('0.00')

    def update_member_balance(self):
        """Update member's balance after transaction completion"""
        balance, created = MemberBalance.objects.get_or_create(
            member=self.member,
            defaults={'current_balance': Decimal('0.00')}
        )
        
        # Recalculate balance from all completed transactions
        total_credits = Transaction.objects.filter(
            member=self.member,
            status='completed',
            transaction_type__in=['deposit', 'loan_disbursement', 'dividend_payment', 'transfer_in']
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        total_debits = Transaction.objects.filter(
            member=self.member,
            status='completed',
            transaction_type__in=['withdrawal', 'loan_payment', 'fee_payment', 'penalty_payment', 'transfer_out']
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        balance.current_balance = total_credits - total_debits
        balance.last_transaction_date = timezone.now()
        balance.save()


class MemberBalance(models.Model):
    """
    Current balance for each member
    """
    member = models.OneToOneField(User, on_delete=models.CASCADE, related_name='balance')
    
    # Current balances by category
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Detailed breakdowns
    share_capital_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    savings_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    loan_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Pending amounts
    pending_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pending_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Metadata
    last_transaction_date = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'member_balance'
        verbose_name = 'Member Balance'
        verbose_name_plural = 'Member Balances'

    def __str__(self):
        return f"{self.member.username} - Balance: ${self.current_balance}"

    def update_balances(self):
        """Recalculate all balance components"""
        # Share capital balance
        from investments.models import Investment
        self.share_capital_balance = Investment.objects.filter(
            member=self.member,
            investment_type='share_capital',
            status='confirmed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        # Savings balance (monthly investments + special deposits)
        self.savings_balance = Investment.objects.filter(
            member=self.member,
            investment_type__in=['monthly_investment', 'special_deposit'],
            status='confirmed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        # Loan balance (outstanding loans)
        from loans.models import Loan
        self.loan_balance = Loan.objects.filter(
            borrower=self.member,
            status__in=['active', 'overdue']
        ).aggregate(total=models.Sum('balance_remaining'))['total'] or Decimal('0.00')
        
        # Pending amounts
        self.pending_deposits = Transaction.objects.filter(
            member=self.member,
            transaction_type='deposit',
            status='pending'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        self.pending_withdrawals = Transaction.objects.filter(
            member=self.member,
            transaction_type='withdrawal',
            status='pending'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        # Available balance (current balance minus pending withdrawals and loan obligations)
        self.available_balance = self.current_balance - self.pending_withdrawals
        
        self.save()


class TransactionFee(models.Model):
    """
    Transaction fees and charges
    """
    FEE_TYPES = (
        ('processing_fee', 'Processing Fee'),
        ('service_charge', 'Service Charge'),
        ('withdrawal_fee', 'Withdrawal Fee'),
        ('transfer_fee', 'Transfer Fee'),
        ('loan_processing_fee', 'Loan Processing Fee'),
        ('late_payment_fee', 'Late Payment Fee'),
        ('membership_fee', 'Membership Fee'),
        ('annual_fee', 'Annual Fee'),
    )
    
    CALCULATION_METHODS = (
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Amount'),
        ('tiered', 'Tiered/Slab Based'),
    )
    
    fee_type = models.CharField(max_length=25, choices=FEE_TYPES, unique=True)
    description = models.TextField()
    calculation_method = models.CharField(max_length=15, choices=CALCULATION_METHODS)
    
    # For fixed fees
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # For percentage fees
    percentage_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage rate (e.g., 2.5 for 2.5%)"
    )
    
    # Limits for percentage fees
    minimum_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    maximum_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Applicability
    is_active = models.BooleanField(default=True)
    applies_to_transaction_types = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated list of transaction types this fee applies to"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transaction_fee'
        verbose_name = 'Transaction Fee'
        verbose_name_plural = 'Transaction Fees'

    def __str__(self):
        return f"{self.get_fee_type_display()} - {self.get_calculation_method_display()}"

    def calculate_fee(self, amount):
        """Calculate fee for a given amount"""
        if not self.is_active:
            return Decimal('0.00')
        
        if self.calculation_method == 'fixed':
            return self.fixed_amount or Decimal('0.00')
        
        elif self.calculation_method == 'percentage':
            if not self.percentage_rate:
                return Decimal('0.00')
            
            fee = amount * (self.percentage_rate / 100)
            
            # Apply minimum fee
            if self.minimum_fee and fee < self.minimum_fee:
                fee = self.minimum_fee
            
            # Apply maximum fee
            if self.maximum_fee and fee > self.maximum_fee:
                fee = self.maximum_fee
            
            return fee
        
        # For tiered fees, would need additional logic
        return Decimal('0.00')


class TransactionBatch(models.Model):
    """
    Batch processing for multiple transactions
    """
    BATCH_TYPES = (
        ('dividend_payment', 'Dividend Payments'),
        ('fee_collection', 'Fee Collection'),
        ('salary_payment', 'Salary Payments'),
        ('bulk_transfer', 'Bulk Transfers'),
        ('interest_payment', 'Interest Payments'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('partially_completed', 'Partially Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    batch_id = models.CharField(max_length=50, unique=True, blank=True)
    batch_type = models.CharField(max_length=20, choices=BATCH_TYPES)
    description = models.TextField()
    
    # Batch details
    total_transactions = models.PositiveIntegerField(default=0)
    successful_transactions = models.PositiveIntegerField(default=0)
    failed_transactions = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Status and processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Processing details
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_batches')
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_batches'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_log = models.TextField(blank=True)

    class Meta:
        db_table = 'transaction_batch'
        verbose_name = 'Transaction Batch'
        verbose_name_plural = 'Transaction Batches'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.batch_id} - {self.get_batch_type_display()} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.batch_id:
            self.batch_id = self.generate_batch_id()
        super().save(*args, **kwargs)

    def generate_batch_id(self):
        """Generate unique batch ID"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        return f"BATCH-{timestamp}-{str(uuid.uuid4())[:8].upper()}"

    def start_processing(self, processed_by):
        """Start batch processing"""
        self.status = 'processing'
        self.processed_by = processed_by
        self.processing_started_at = timezone.now()
        self.save()

    def complete_processing(self):
        """Mark batch as completed"""
        self.status = 'completed' if self.failed_transactions == 0 else 'partially_completed'
        self.completed_at = timezone.now()
        self.save()

    def add_transaction(self, transaction):
        """Add transaction to this batch"""
        BatchTransaction.objects.create(
            batch=self,
            transaction=transaction
        )
        self.update_totals()

    def update_totals(self):
        """Update batch totals"""
        batch_transactions = self.batch_transactions.all()
        
        self.total_transactions = batch_transactions.count()
        self.successful_transactions = batch_transactions.filter(
            transaction__status='completed'
        ).count()
        self.failed_transactions = batch_transactions.filter(
            transaction__status='failed'
        ).count()
        self.total_amount = batch_transactions.aggregate(
            total=models.Sum('transaction__amount')
        )['total'] or Decimal('0.00')
        
        self.save(update_fields=[
            'total_transactions', 'successful_transactions', 
            'failed_transactions', 'total_amount'
        ])


class BatchTransaction(models.Model):
    """
    Link between batches and individual transactions
    """
    batch = models.ForeignKey(
        TransactionBatch,
        on_delete=models.CASCADE,
        related_name='batch_transactions'
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='batch_info'
    )
    
    # Processing order and status
    sequence_number = models.PositiveIntegerField()
    processing_notes = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'batch_transaction'
        verbose_name = 'Batch Transaction'
        verbose_name_plural = 'Batch Transactions'
        unique_together = ['batch', 'transaction']
        ordering = ['sequence_number']

    def __str__(self):
        return f"Batch {self.batch.batch_id} - Transaction {self.transaction.transaction_id}"


class RecurringTransaction(models.Model):
    """
    Templates for recurring transactions
    """
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    
    # Template details
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Transaction template
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    transaction_type = models.CharField(max_length=20, choices=Transaction.TRANSACTION_TYPES)
    category = models.CharField(max_length=15, choices=Transaction.TRANSACTION_CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Recurrence settings
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Next execution
    next_execution_date = models.DateField()
    last_execution_date = models.DateField(null=True, blank=True)
    
    # Status and tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    execution_count = models.PositiveIntegerField(default=0)
    max_executions = models.PositiveIntegerField(null=True, blank=True)
    
    # Auto-processing
    auto_execute = models.BooleanField(
        default=False,
        help_text="Automatically execute transactions without manual approval"
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_recurring_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recurring_transaction'
        verbose_name = 'Recurring Transaction'
        verbose_name_plural = 'Recurring Transactions'
        ordering = ['next_execution_date']

    def __str__(self):
        return f"{self.name} - {self.member.username} - {self.get_frequency_display()}"

    def execute_transaction(self):
        """Execute the recurring transaction"""
        if self.status != 'active':
            raise ValueError("Only active recurring transactions can be executed")
        
        # Create the transaction
        transaction = Transaction.objects.create(
            member=self.member,
            transaction_type=self.transaction_type,
            category=self.category,
            amount=self.amount,
            description=f"Recurring: {self.description}",
            reference_number=f"REC-{self.id}-{self.execution_count + 1}",
            status='pending' if not self.auto_execute else 'completed'
        )
        
        if self.auto_execute:
            transaction.complete_transaction()
        
        # Update execution tracking
        self.execution_count += 1
        self.last_execution_date = timezone.now().date()
        self.calculate_next_execution_date()
        
        # Check if recurring transaction should be completed
        if self.max_executions and self.execution_count >= self.max_executions:
            self.status = 'completed'
        elif self.end_date and self.next_execution_date > self.end_date:
            self.status = 'completed'
        
        self.save()
        return transaction

    def calculate_next_execution_date(self):
        """Calculate the next execution date"""
        from dateutil.relativedelta import relativedelta
        
        current_date = self.next_execution_date
        
        if self.frequency == 'daily':
            self.next_execution_date = current_date + relativedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_execution_date = current_date + relativedelta(weeks=1)
        elif self.frequency == 'monthly':
            self.next_execution_date = current_date + relativedelta(months=1)
        elif self.frequency == 'quarterly':
            self.next_execution_date = current_date + relativedelta(months=3)
        elif self.frequency == 'annually':
            self.next_execution_date = current_date + relativedelta(years=1)

    def pause(self):
        """Pause the recurring transaction"""
        self.status = 'paused'
        self.save()

    def resume(self):
        """Resume the recurring transaction"""
        if self.status == 'paused':
            self.status = 'active'
            self.save()

    def cancel(self):
        """Cancel the recurring transaction"""
        self.status = 'cancelled'
        self.save()


class TransactionReceipt(models.Model):
    """
    Digital receipts for transactions
    """
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='receipt'
    )
    
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    receipt_data = models.JSONField(default=dict)  # Store receipt details as JSON
    
    # PDF generation
    pdf_file = models.FileField(
        upload_to='receipts/',
        null=True,
        blank=True
    )
    
    # Email delivery
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction_receipt'
        verbose_name = 'Transaction Receipt'
        verbose_name_plural = 'Transaction Receipts'

    def __str__(self):
        return f"Receipt {self.receipt_number} for {self.transaction.transaction_id}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()
        super().save(*args, **kwargs)

    def generate_receipt_number(self):
        """Generate unique receipt number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        return f"RCP-{timestamp}-{str(uuid.uuid4())[:6].upper()}"

    def generate_pdf(self):
        """Generate PDF receipt (implementation would depend on PDF library)"""
        # This would integrate with a PDF generation library
        # like ReportLab or WeasyPrint
        pass

    def send_email_receipt(self):
        """Send receipt via email"""
        # This would integrate with the email system
        pass


class TransactionAuditLog(models.Model):
    """
    Audit log for transaction modifications
    """
    ACTION_TYPES = (
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
        ('cancelled', 'Cancelled'),
    )
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    
    action_type = models.CharField(max_length=15, choices=ACTION_TYPES)
    old_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    
    # User and system info
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Additional context
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction_audit_log'
        verbose_name = 'Transaction Audit Log'
        verbose_name_plural = 'Transaction Audit Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction.transaction_id} - {self.get_action_type_display()} by {self.performed_by}"