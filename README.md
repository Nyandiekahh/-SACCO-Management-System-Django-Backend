# 🏦 SACCO Management System

A comprehensive digital SACCO (Savings and Credit Cooperative) management system built with Django REST Framework and React. This system handles member applications, investments, loans, guarantors, transactions, and notifications with a complete admin panel.

## ✨ Features

### 🔐 Member Management
- **Application Process**: Complete KYC verification with document uploads
- **User Authentication**: JWT-based authentication with role-based access
- **Profile Management**: Comprehensive member profiles with employment/education details
- **Admin Approval**: Multi-step approval process with email notifications

### 💰 Investment Management
- **Share Capital**: Fixed amount contributions with configurable limits
- **Monthly Investments**: Flexible recurring investments
- **Special Deposits**: Additional investment categories
- **Investment Tracking**: Real-time balance updates and investment summaries
- **Rankings**: Member rankings based on total investments

### 🏦 Loan Management
- **Loan Applications**: Multi-type loan applications with eligibility checks
- **Guarantor System**: Multiple guarantors with percentage-based guarantees
- **Loan Disbursement**: Admin-controlled disbursement with transaction tracking
- **Repayment Management**: Payment processing with penalty calculations
- **Loan Scheduling**: Automatic repayment schedule generation

### 💳 Transaction System
- **Comprehensive Tracking**: All financial transactions logged with audit trails
- **Payment Processing**: Transaction code verification and admin confirmation
- **Balance Management**: Real-time balance calculations and reconciliation
- **Fee Management**: Configurable transaction fees and charges
- **Batch Processing**: Bulk transaction processing capabilities

### 📧 Notification System
- **Multi-Channel**: Email, SMS, and in-app notifications
- **Template Management**: Customizable notification templates
- **Bulk Notifications**: Mass communication to member groups
- **Delivery Tracking**: Email delivery status and read receipts

### ⚙️ Admin Configuration
- **SACCO Settings**: Configurable business rules and parameters
- **Loan Types**: Multiple loan products with different terms
- **Investment Types**: Flexible investment categories
- **Email Templates**: Customizable email communication templates
- **System Configuration**: Global system settings and maintenance

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Node.js 16+ (for React frontend)
- Redis (optional, for caching and background tasks)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sacco-management-system.git
cd sacco-management-system
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv sacco_env
source sacco_env/bin/activate  # On Windows: sacco_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and email credentials

# Run setup script
python setup.py

# Or run manual setup
python manage.py makemigrations
python manage.py migrate
python manage.py sacco_setup --with-samples

# Start development server
python manage.py runserver
```

### 3. Database Setup

Create a PostgreSQL database:

```sql
CREATE DATABASE sacco_db;
CREATE USER sacco_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sacco_db TO sacco_user;
```

Update your `.env` file:

```env
DB_NAME=sacco_db
DB_USER=sacco_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 4. Initial Setup

Run the setup command to create initial data:

```bash
python manage.py sacco_setup --with-samples
```

This will create:
- Admin user (admin/admin123)
- Default SACCO settings
- Sample loan and investment types
- Email templates
- Sample member data

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/token/refresh/` - Refresh access token

### User Management
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/update/` - Update user profile
- `POST /api/auth/password/change/` - Change password

### Applications
- `POST /api/applications/submit/` - Submit membership application
- `GET /api/applications/applications/` - List applications (admin)
- `POST /api/applications/{id}/approve/` - Approve application (admin)
- `POST /api/applications/{id}/reject/` - Reject application (admin)

### Investments
- `POST /api/investments/invest/` - Make investment
- `GET /api/investments/my-investments/` - Get user investments
- `POST /api/investments/{id}/confirm/` - Confirm investment (admin)
- `GET /api/investments/rankings/` - Investment rankings

### Loans
- `POST /api/loans/apply/` - Apply for loan
- `GET /api/loans/my-loans/` - Get user loans
- `POST /api/loans/applications/{id}/approve/` - Approve loan (admin)
- `POST /api/loans/payments/make/` - Make loan payment
- `POST /api/loans/payments/{id}/confirm/` - Confirm payment (admin)

### Transactions
- `GET /api/transactions/my-transactions/` - Get user transactions
- `GET /api/transactions/my-balance/` - Get user balance
- `POST /api/transactions/{id}/complete/` - Complete transaction (admin)

### Settings
- `GET /api/settings/sacco/` - Get SACCO settings
- `PUT /api/settings/sacco/update/` - Update SACCO settings (admin)
- `GET /api/settings/loan-types/` - Get loan types
- `GET /api/settings/investment-types/` - Get investment types

## 🏗️ Project Structure

```
sacco_project/
├── accounts/              # User management & authentication
│   ├── models.py         # CustomUser, UserProfile, UserActivity
│   ├── serializers.py    # User serializers
│   ├── views.py          # User views and endpoints
│   └── urls.py           # User URL configurations
├── applications/         # Member applications & KYC
│   ├── models.py         # MemberApplication, ApplicationDocument
│   ├── views.py          # Application processing views
│   └── urls.py           # Application URLs
├── investments/          # Investment management
│   ├── models.py         # Investment, InvestmentSummary
│   ├── views.py          # Investment processing views
│   └── urls.py           # Investment URLs
├── loans/               # Loan management
│   ├── models.py        # LoanApplication, Loan, LoanPayment
│   ├── views.py         # Loan processing views
│   └── urls.py          # Loan URLs
├── transactions/        # Financial transactions
│   ├── models.py        # Transaction, MemberBalance
│   ├── views.py         # Transaction processing views
│   └── urls.py          # Transaction URLs
├── sacco_settings/      # SACCO configuration
│   ├── models.py        # SaccoSettings, LoanType, InvestmentType
│   ├── views.py         # Settings management views
│   └── urls.py          # Settings URLs
├── notifications/       # Notification system
│   ├── models.py        # Notification, EmailNotification
│   ├── views.py         # Notification views
│   └── urls.py          # Notification URLs
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## 🎨 Frontend Development

The system is designed to work with a React frontend. The API provides all necessary endpoints for:

- User authentication and registration
- Member dashboard with investment and loan summaries
- Admin panels for managing applications, investments, and loans
- Real-time notifications and updates

### Key Frontend Components Needed

1. **Authentication**
   - Login/Register forms
   - Protected routes
   - JWT token management

2. **Member Dashboard**
   - Investment summary cards
   - Loan status displays
   - Transaction history
   - Notification center

3. **Investment Management**
   - Investment forms (share capital, monthly savings)
   - Investment history and tracking
   - Balance displays

4. **Loan Management**
   - Loan application forms
   - Guarantor selection interface
   - Loan repayment forms
   - Loan schedule displays

5. **Admin Panels**
   - Application review interface
   - Investment confirmation panels
   - Loan approval workflows
   - Transaction verification

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

```env
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=sacco_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### SACCO Settings

Configure your SACCO through the admin interface or API:

- **Basic Information**: Name, description, contact details
- **Membership Rules**: Minimum membership duration for loans
- **Investment Limits**: Share capital amounts, minimum investments
- **Loan Parameters**: Default interest rates, loan multipliers
- **Guarantor Requirements**: Minimum guarantor percentages

## 📱 Mobile API

The REST API is fully mobile-ready with:

- JWT authentication
- Paginated responses
- Error handling
- File upload support
- Real-time notifications

## 🔒 Security Features

- JWT-based authentication
- Role-based permissions (Admin/Member)
- File upload validation
- XSS protection
- CSRF protection
- Rate limiting
- Audit logging

## 📊 Reporting & Analytics

The system includes comprehensive reporting:

- Member investment summaries
- Loan performance reports
- Transaction history exports
- Financial statements
- Member rankings and statistics

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts
python manage.py test investments
python manage.py test loans

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## 🚀 Deployment

### Production Setup

1. **Environment Configuration**
   ```env
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   SECURE_SSL_REDIRECT=True
   SECURE_HSTS_SECONDS=31536000
   ```

2. **Database Migration**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

3. **Web Server Configuration**
   - Use Gunicorn for the Django application
   - Configure Nginx for static files and reverse proxy
   - Set up SSL certificates

4. **Background Tasks**
   - Configure Celery for email sending and background processing
   - Set up Redis for caching and task queues

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💬 Support

For support and questions:

- Create an issue on GitHub
- Email: support@yoursacco.com
- Documentation: [Link to detailed docs]

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Core member management
- ✅ Investment tracking
- ✅ Loan management
- ✅ Basic notifications

### Phase 2 (Upcoming)
- 📱 Mobile app development
- 🌐 SMS integration
- 📊 Advanced reporting
- 🔔 Real-time notifications

### Phase 3 (Future)
- 🤖 AI-powered credit scoring
- 📈 Investment recommendations
- 🏪 Merchant integration
- 💳 Digital wallet features

---

**Built with ❤️ for the cooperative movement**