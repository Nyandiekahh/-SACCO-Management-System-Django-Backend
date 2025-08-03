#!/usr/bin/env python3
"""
SACCO Management System Setup Script
This script helps set up the Django project with initial data
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.core.management.base import BaseCommand


def setup_django():
    """Setup Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sacco_project.settings')
    django.setup()


def create_superuser():
    """Create admin superuser"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(username='admin').exists():
        print("Creating admin superuser...")
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@sacco.com',
            password='admin123',
            first_name='System',
            last_name='Administrator',
            phone_number='+254700000000',
            user_type='admin'
        )
        print(f"Admin user created: {admin_user.username}")
    else:
        print("Admin user already exists")


def create_default_settings():
    """Create default SACCO settings"""
    from sacco_settings.models import SaccoSettings, LoanType, InvestmentType, EmailTemplate
    
    print("Creating default SACCO settings...")
    
    # Create main SACCO settings
    sacco_settings, created = SaccoSettings.objects.get_or_create(
        defaults={
            'sacco_name': 'My SACCO',
            'sacco_description': 'A modern digital SACCO for our community',
            'contact_email': 'info@mysacco.com',
            'contact_phone': '+254700000000',
            'minimum_membership_months': 3,
            'share_capital_amount': 5000.00,
            'loan_multiplier': 3.00,
            'default_loan_interest_rate': 12.00,
            'maximum_loan_period_months': 12,
            'require_guarantors': True,
            'minimum_guarantor_percentage': 25.00,
            'minimum_monthly_investment': 100.00,
            'send_email_notifications': True,
        }
    )
    
    if created:
        print("Default SACCO settings created")
    else:
        print("SACCO settings already exist")
    
    # Create default loan types
    loan_types = [
        {
            'name': 'Emergency Loan',
            'description': 'Quick loans for emergency situations',
            'interest_rate': 10.00,
            'maximum_amount': 50000.00,
            'maximum_period_months': 6,
            'minimum_membership_months': 3,
            'requires_guarantor': False,
        },
        {
            'name': 'Development Loan',
            'description': 'Loans for business and personal development',
            'interest_rate': 12.00,
            'maximum_amount': 200000.00,
            'maximum_period_months': 12,
            'minimum_membership_months': 6,
            'requires_guarantor': True,
        },
        {
            'name': 'Education Loan',
            'description': 'Loans for educational purposes',
            'interest_rate': 8.00,
            'maximum_amount': 100000.00,
            'maximum_period_months': 18,
            'minimum_membership_months': 3,
            'requires_guarantor': True,
        }
    ]
    
    for loan_type_data in loan_types:
        loan_type, created = LoanType.objects.get_or_create(
            name=loan_type_data['name'],
            defaults=loan_type_data
        )
        if created:
            print(f"Created loan type: {loan_type.name}")
    
    # Create default investment types
    investment_types = [
        {
            'name': 'Share Capital',
            'category': 'share_capital',
            'description': 'Fixed share capital contribution',
            'fixed_amount': 5000.00,
            'interest_rate': 8.00,
            'counts_for_loan_calculation': True,
        },
        {
            'name': 'Monthly Savings',
            'category': 'monthly_investment',
            'description': 'Flexible monthly savings',
            'minimum_amount': 100.00,
            'interest_rate': 6.00,
            'counts_for_loan_calculation': True,
        },
        {
            'name': 'Special Deposit',
            'category': 'special_deposit',
            'description': 'Special purpose deposits',
            'minimum_amount': 500.00,
            'interest_rate': 4.00,
            'counts_for_loan_calculation': False,
        }
    ]
    
    for investment_type_data in investment_types:
        investment_type, created = InvestmentType.objects.get_or_create(
            name=investment_type_data['name'],
            defaults=investment_type_data
        )
        if created:
            print(f"Created investment type: {investment_type.name}")
    
    # Create default email templates
    email_templates = [
        {
            'template_type': 'application_approved',
            'subject': 'Welcome to {{sacco_name}} - Application Approved!',
            'body': '''
            Dear {{applicant_name}},
            
            Congratulations! Your membership application to {{sacco_name}} has been approved.
            
            Your member number is: {{member_number}}
            
            You can now:
            - Make investments
            - Apply for loans
            - Access all member services
            
            Welcome to our SACCO family!
            
            Best regards,
            {{sacco_name}} Team
            ''',
        },
        {
            'template_type': 'application_rejected',
            'subject': '{{sacco_name}} - Application Update',
            'body': '''
            Dear {{applicant_name}},
            
            Thank you for your interest in joining {{sacco_name}}.
            
            After careful review, we regret to inform you that your application has not been approved at this time.
            
            Reason: {{rejection_reason}}
            
            You are welcome to reapply after addressing the mentioned concerns.
            
            Best regards,
            {{sacco_name}} Team
            ''',
        },
        {
            'template_type': 'loan_approved',
            'subject': 'Loan Approved - {{sacco_name}}',
            'body': '''
            Dear {{member_name}},
            
            Good news! Your loan application has been approved.
            
            Loan Details:
            - Amount: {{loan_amount}}
            - Interest Rate: {{interest_rate}}%
            - Repayment Period: {{repayment_period}} months
            - Monthly Payment: {{monthly_payment}}
            
            The loan will be disbursed once all requirements are met.
            
            Best regards,
            {{sacco_name}} Team
            ''',
        },
        {
            'template_type': 'deposit_confirmed',
            'subject': 'Deposit Confirmed - {{sacco_name}}',
            'body': '''
            Dear {{member_name}},
            
            Your deposit has been confirmed and added to your account.
            
            Transaction Details:
            - Amount: {{amount}}
            - Transaction Reference: {{transaction_reference}}
            - New Balance: {{new_balance}}
            
            Thank you for your continued trust in {{sacco_name}}.
            
            Best regards,
            {{sacco_name}} Team
            ''',
        }
    ]
    
    for template_data in email_templates:
        template, created = EmailTemplate.objects.get_or_create(
            template_type=template_data['template_type'],
            defaults=template_data
        )
        if created:
            print(f"Created email template: {template.get_template_type_display()}")


def create_sample_data():
    """Create sample data for testing"""
    from django.contrib.auth import get_user_model
    from applications.models import MemberApplication
    from decimal import Decimal
    import random
    
    User = get_user_model()
    
    print("Creating sample member data...")
    
    # Create sample members
    sample_members = [
        {
            'username': 'john_doe',
            'email': 'john.doe@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+254701000001',
            'address': '123 Main Street, Nairobi',
            'employment_status': 'Employed at ABC Company',
        },
        {
            'username': 'jane_smith',
            'email': 'jane.smith@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '+254701000002',
            'address': '456 Oak Avenue, Mombasa',
            'employment_status': 'Self Employed - Small Business',
        },
        {
            'username': 'peter_wilson',
            'email': 'peter.wilson@example.com',
            'first_name': 'Peter',
            'last_name': 'Wilson',
            'phone_number': '+254701000003',
            'address': '789 Pine Road, Kisumu',
            'school_name': 'University of Nairobi',
        }
    ]
    
    for member_data in sample_members:
        if not User.objects.filter(username=member_data['username']).exists():
            user = User.objects.create_user(
                password='password123',
                is_approved=True,
                user_type='member',
                **member_data
            )
            print(f"Created sample member: {user.username}")


def run_migrations():
    """Run database migrations"""
    print("Running database migrations...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    execute_from_command_line(['manage.py', 'migrate'])


def collect_static():
    """Collect static files"""
    print("Collecting static files...")
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])


def main():
    """Main setup function"""
    print("🏦 SACCO Management System Setup")
    print("=" * 40)
    
    # Setup Django
    setup_django()
    
    # Run migrations
    run_migrations()
    
    # Create initial data
    create_superuser()
    create_default_settings()
    
    # Ask if user wants sample data
    create_samples = input("\nDo you want to create sample data for testing? (y/n): ").lower().strip()
    if create_samples == 'y':
        create_sample_data()
    
    # Collect static files
    collect_static()
    
    print("\n✅ Setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Copy .env.example to .env and update with your settings")
    print("2. Update database credentials in .env")
    print("3. Configure email settings in .env")
    print("4. Run: python manage.py runserver")
    print("5. Visit: http://localhost:8000/admin (admin/admin123)")
    print("\n🎉 Your SACCO Management System is ready!")


if __name__ == '__main__':
    main()