from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up SACCO system with initial data and configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-samples',
            action='store_true',
            help='Create sample data for testing',
        )
        parser.add_argument(
            '--reset-data',
            action='store_true',
            help='Reset all data (WARNING: This will delete existing data)',
        )
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@sacco.com',
            help='Admin user email address',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Admin user password',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🏦 Starting SACCO Management System Setup')
        )

        if options['reset_data']:
            if self.confirm_reset():
                self.reset_database()

        try:
            with transaction.atomic():
                self.create_superuser(options)
                self.create_sacco_settings()
                self.create_loan_types()
                self.create_investment_types()
                self.create_email_templates()
                self.create_notification_templates()
                self.create_transaction_fees()
                
                if options['with_samples']:
                    self.create_sample_data()

                self.stdout.write(
                    self.style.SUCCESS('✅ SACCO setup completed successfully!')
                )
                self.print_next_steps()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Setup failed: {str(e)}')
            )
            raise CommandError(f'Setup failed: {str(e)}')

    def confirm_reset(self):
        """Confirm database reset"""
        self.stdout.write(
            self.style.WARNING('⚠️  WARNING: This will delete ALL existing data!')
        )
        confirm = input('Type "RESET" to confirm: ')
        return confirm == 'RESET'

    def reset_database(self):
        """Reset database (for development only)"""
        self.stdout.write('🗑️  Resetting database...')
        
        # Import all models to clear
        from applications.models import MemberApplication
        from investments.models import Investment, InvestmentSummary
        from loans.models import Loan, LoanApplication
        from transactions.models import Transaction, MemberBalance
        from notifications.models import Notification, EmailNotification
        
        # Clear data in proper order
        models_to_clear = [
            Transaction, MemberBalance, Loan, LoanApplication,
            Investment, InvestmentSummary, MemberApplication,
            Notification, EmailNotification
        ]
        
        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'  Cleared {count} {model.__name__} records')

        # Clear non-admin users
        non_admin_users = User.objects.filter(user_type='member')
        count = non_admin_users.count()
        non_admin_users.delete()
        self.stdout.write(f'  Cleared {count} member users')

    def create_superuser(self, options):
        """Create admin superuser"""
        self.stdout.write('👤 Creating admin user...')
        
        admin_email = options['admin_email']
        admin_password = options['admin_password']
        
        if User.objects.filter(username='admin').exists():
            self.stdout.write('  Admin user already exists')
            return

        admin_user = User.objects.create_superuser(
            username='admin',
            email=admin_email,
            password=admin_password,
            first_name='System',
            last_name='Administrator',
            phone_number='+254700000000',
            user_type='admin',
            is_approved=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✅ Admin user created: {admin_user.username}')
        )

    def create_sacco_settings(self):
        """Create default SACCO settings"""
        self.stdout.write('⚙️  Creating SACCO settings...')
        
        from sacco_settings.models import SaccoSettings, SystemConfiguration
        
        sacco_settings, created = SaccoSettings.objects.get_or_create(
            defaults={
                'sacco_name': 'Digital SACCO',
                'sacco_description': 'A modern digital SACCO management system',
                'contact_email': 'info@digitalsacco.com',
                'contact_phone': '+254700000000',
                'address': 'Nairobi, Kenya',
                'minimum_membership_months': 3,
                'share_capital_amount': Decimal('5000.00'),
                'loan_multiplier': Decimal('3.00'),
                'default_loan_interest_rate': Decimal('12.00'),
                'maximum_loan_period_months': 12,
                'require_guarantors': True,
                'minimum_guarantor_percentage': Decimal('25.00'),
                'minimum_monthly_investment': Decimal('100.00'),
                'send_email_notifications': True,
            }
        )
        
        if created:
            self.stdout.write('  ✅ SACCO settings created')
        else:
            self.stdout.write('  ℹ️  SACCO settings already exist')

        # Create system configuration
        sys_config, created = SystemConfiguration.objects.get_or_create(
            defaults={
                'max_file_size_mb': 5,
                'allowed_file_types': 'jpg,jpeg,png,pdf',
                'session_timeout_minutes': 60,
                'max_login_attempts': 5,
                'account_lockout_duration_minutes': 30,
            }
        )
        
        if created:
            self.stdout.write('  ✅ System configuration created')

    def create_loan_types(self):
        """Create default loan types"""
        self.stdout.write('💰 Creating loan types...')
        
        from sacco_settings.models import LoanType
        
        loan_types = [
            {
                'name': 'Emergency Loan',
                'description': 'Quick loans for emergency situations',
                'interest_rate': Decimal('10.00'),
                'maximum_amount': Decimal('50000.00'),
                'maximum_period_months': 6,
                'minimum_membership_months': 3,
                'requires_guarantor': False,
            },
            {
                'name': 'Development Loan',
                'description': 'Loans for business and personal development',
                'interest_rate': Decimal('12.00'),
                'maximum_amount': Decimal('200000.00'),
                'maximum_period_months': 12,
                'minimum_membership_months': 6,
                'requires_guarantor': True,
            },
            {
                'name': 'Education Loan',
                'description': 'Loans for educational purposes',
                'interest_rate': Decimal('8.00'),
                'maximum_amount': Decimal('100000.00'),
                'maximum_period_months': 18,
                'minimum_membership_months': 3,
                'requires_guarantor': True,
            },
            {
                'name': 'Asset Purchase Loan',
                'description': 'Loans for purchasing assets',
                'interest_rate': Decimal('14.00'),
                'maximum_amount': Decimal('500000.00'),
                'maximum_period_months': 24,
                'minimum_membership_months': 12,
                'requires_guarantor': True,
            }
        ]
        
        created_count = 0
        for loan_type_data in loan_types:
            loan_type, created = LoanType.objects.get_or_create(
                name=loan_type_data['name'],
                defaults=loan_type_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} loan types')

    def create_investment_types(self):
        """Create default investment types"""
        self.stdout.write('📈 Creating investment types...')
        
        from sacco_settings.models import InvestmentType
        
        investment_types = [
            {
                'name': 'Share Capital',
                'category': 'share_capital',
                'description': 'Mandatory share capital contribution',
                'fixed_amount': Decimal('5000.00'),
                'interest_rate': Decimal('8.00'),
                'counts_for_loan_calculation': True,
            },
            {
                'name': 'Monthly Savings',
                'category': 'monthly_investment',
                'description': 'Flexible monthly savings account',
                'minimum_amount': Decimal('100.00'),
                'interest_rate': Decimal('6.00'),
                'counts_for_loan_calculation': True,
            },
            {
                'name': 'Special Deposit',
                'category': 'special_deposit',
                'description': 'Special purpose fixed deposits',
                'minimum_amount': Decimal('500.00'),
                'interest_rate': Decimal('4.00'),
                'counts_for_loan_calculation': False,
            },
            {
                'name': 'Holiday Savings',
                'category': 'monthly_investment',
                'description': 'Savings for holiday expenses',
                'minimum_amount': Decimal('200.00'),
                'interest_rate': Decimal('5.00'),
                'counts_for_loan_calculation': True,
            }
        ]
        
        created_count = 0
        for investment_type_data in investment_types:
            investment_type, created = InvestmentType.objects.get_or_create(
                name=investment_type_data['name'],
                defaults=investment_type_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} investment types')

    def create_email_templates(self):
        """Create default email templates"""
        self.stdout.write('📧 Creating email templates...')
        
        from sacco_settings.models import EmailTemplate
        
        templates = [
            {
                'template_type': 'application_approved',
                'subject': 'Welcome to {{sacco_name}} - Application Approved!',
                'body': '''Dear {{applicant_name}},

Congratulations! Your membership application has been approved.

Your member details:
- Member Number: {{member_number}}
- Approval Date: {{approval_date}}

You can now access all member services including:
- Making investments and deposits
- Applying for loans
- Viewing your account statement

Welcome to our SACCO family!

Best regards,
{{sacco_name}} Team''',
            },
            {
                'template_type': 'application_rejected',
                'subject': '{{sacco_name}} - Application Status Update',
                'body': '''Dear {{applicant_name}},

Thank you for your interest in joining {{sacco_name}}.

After careful review, we regret to inform you that your application has not been approved at this time.

Reason: {{rejection_reason}}

You are welcome to reapply after addressing the mentioned concerns. Please contact us if you need clarification.

Best regards,
{{sacco_name}} Team''',
            },
            {
                'template_type': 'loan_approved',
                'subject': 'Loan Approved - {{sacco_name}}',
                'body': '''Dear {{member_name}},

Great news! Your loan application has been approved.

Loan Details:
- Loan Amount: KES {{loan_amount}}
- Interest Rate: {{interest_rate}}% per annum
- Repayment Period: {{repayment_period}} months
- Monthly Payment: KES {{monthly_payment}}
- Total Repayment: KES {{total_repayment}}

The loan will be disbursed shortly. You will receive another notification once disbursement is complete.

Best regards,
{{sacco_name}} Team''',
            },
            {
                'template_type': 'loan_disbursed',
                'subject': 'Loan Disbursed - {{sacco_name}}',
                'body': '''Dear {{member_name}},

Your loan has been successfully disbursed.

Disbursement Details:
- Amount Disbursed: KES {{disbursed_amount}}
- Transaction Reference: {{transaction_reference}}
- Disbursement Date: {{disbursement_date}}
- First Payment Due: {{first_payment_date}}

Please ensure timely repayments to maintain a good credit record.

Best regards,
{{sacco_name}} Team''',
            },
            {
                'template_type': 'deposit_confirmed',
                'subject': 'Deposit Confirmed - {{sacco_name}}',
                'body': '''Dear {{member_name}},

Your deposit has been successfully confirmed and credited to your account.

Transaction Details:
- Amount: KES {{amount}}
- Investment Type: {{investment_type}}
- Transaction Reference: {{transaction_reference}}
- Date: {{transaction_date}}
- New Balance: KES {{new_balance}}

Thank you for your continued investment in {{sacco_name}}.

Best regards,
{{sacco_name}} Team''',
            }
        ]
        
        created_count = 0
        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} email templates')

    def create_notification_templates(self):
        """Create notification templates"""
        self.stdout.write('🔔 Creating notification templates...')
        
        from notifications.models import NotificationTemplate
        
        templates = [
            {
                'template_type': 'loan_payment_due',
                'title_template': 'Loan Payment Due',
                'message_template': 'Your loan payment of KES {{amount}} is due on {{due_date}}.',
                'category': 'loan',
                'is_urgent': True,
            },
            {
                'template_type': 'loan_overdue',
                'title_template': 'Loan Payment Overdue',
                'message_template': 'Your loan payment is overdue by {{days_overdue}} days. Please make payment immediately.',
                'category': 'loan',
                'is_urgent': True,
            },
            {
                'template_type': 'investment_confirmed',
                'title_template': 'Investment Confirmed',
                'message_template': 'Your investment of KES {{amount}} has been confirmed and added to your account.',
                'category': 'investment',
            },
            {
                'template_type': 'welcome_member',
                'title_template': 'Welcome to {{sacco_name}}!',
                'message_template': 'Welcome to our SACCO! Your member number is {{member_number}}. Start investing and enjoy our services.',
                'category': 'general',
            }
        ]
        
        created_count = 0
        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} notification templates')

    def create_transaction_fees(self):
        """Create default transaction fees"""
        self.stdout.write('💳 Creating transaction fees...')
        
        from transactions.models import TransactionFee
        
        fees = [
            {
                'fee_type': 'withdrawal_fee',
                'description': 'Fee charged on withdrawals',
                'calculation_method': 'percentage',
                'percentage_rate': Decimal('2.5'),
                'minimum_fee': Decimal('50.00'),
                'maximum_fee': Decimal('500.00'),
                'applies_to_transaction_types': 'withdrawal',
            },
            {
                'fee_type': 'loan_processing_fee',
                'description': 'One-time loan processing fee',
                'calculation_method': 'percentage',
                'percentage_rate': Decimal('3.0'),
                'minimum_fee': Decimal('200.00'),
                'maximum_fee': Decimal('2000.00'),
                'applies_to_transaction_types': 'loan_disbursement',
            },
            {
                'fee_type': 'membership_fee',
                'description': 'Annual membership fee',
                'calculation_method': 'fixed',
                'fixed_amount': Decimal('500.00'),
                'applies_to_transaction_types': 'fee_payment',
            }
        ]
        
        created_count = 0
        for fee_data in fees:
            fee, created = TransactionFee.objects.get_or_create(
                fee_type=fee_data['fee_type'],
                defaults=fee_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} transaction fees')

    def create_sample_data(self):
        """Create sample data for testing"""
        self.stdout.write('🧪 Creating sample data...')
        
        # Create sample members
        sample_users = [
            {
                'username': 'john_doe',
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_number': '+254701000001',
                'address': '123 Main Street, Nairobi',
                'employment_status': 'Software Engineer at Tech Corp',
            },
            {
                'username': 'mary_jane',
                'email': 'mary.jane@example.com',
                'first_name': 'Mary',
                'last_name': 'Jane',
                'phone_number': '+254701000002',
                'address': '456 Oak Avenue, Mombasa',
                'employment_status': 'Business Owner - Retail Shop',
            },
            {
                'username': 'peter_kim',
                'email': 'peter.kim@example.com',
                'first_name': 'Peter',
                'last_name': 'Kim',
                'phone_number': '+254701000003',
                'address': '789 Pine Road, Kisumu',
                'school_name': 'University of Nairobi - Computer Science',
            }
        ]
        
        created_users = 0
        for user_data in sample_users:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    password='password123',
                    is_approved=True,
                    user_type='member',
                    **user_data
                )
                created_users += 1
        
        self.stdout.write(f'  ✅ Created {created_users} sample members')
        
        if created_users > 0:
            self.stdout.write('  📝 Sample member credentials:')
            for user_data in sample_users[:created_users]:
                self.stdout.write(f'    {user_data["username"]} / password123')

    def print_next_steps(self):
        """Print next steps for the user"""
        self.stdout.write('\n📋 Next Steps:')
        self.stdout.write('1. Configure your .env file with database and email settings')
        self.stdout.write('2. Run: python manage.py runserver')
        self.stdout.write('3. Visit: http://localhost:8000/admin')
        self.stdout.write('4. Login with admin credentials')
        self.stdout.write('5. Customize SACCO settings as needed')
        self.stdout.write('\n🎉 Your SACCO Management System is ready to use!')