from rest_framework import generics, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal

from .models import CustomUser, UserProfile, UserActivity
from .serializers import (
    CustomUserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordChangeSerializer, AdminUserApprovalSerializer, UserActivitySerializer,
    UserStatsSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Log the registration
        UserActivity.objects.create(
            user=user,
            activity_type='registration',
            description='User registered successfully',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'user': CustomUserSerializer(user).data,
            'message': 'Registration successful. Your application is under review.'
        }, status=status.HTTP_201_CREATED)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLoginView(TokenObtainPairView):
    """Enhanced login view with activity logging"""
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user = serializer.validated_data['user']
        
        if not user.is_approved and user.user_type == 'member':
            return Response({
                'error': 'Your account is pending approval'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Log the login
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            description='User logged in successfully',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': CustomUserSerializer(user).data
        }, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLogoutView(APIView):
    """User logout endpoint"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Log the logout
            UserActivity.objects.create(
                user=request.user,
                activity_type='logout',
                description='User logged out successfully',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordChangeView(generics.UpdateAPIView):
    """Password change endpoint"""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Log password change
        UserActivity.objects.create(
            user=user,
            activity_type='password_change',
            description='Password changed successfully',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordResetView(APIView):
    """Password reset request endpoint"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email)
            
            # In a real implementation, you would:
            # 1. Generate a password reset token
            # 2. Send an email with the reset link
            # 3. Store the token with expiration
            
            # For now, just log the attempt
            UserActivity.objects.create(
                user=user,
                activity_type='password_reset_request',
                description='Password reset requested',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Password reset instructions sent to your email'
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists or not
            return Response({
                'message': 'If the email exists, password reset instructions have been sent'
            }, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordResetConfirmView(APIView):
    """Password reset confirmation endpoint"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # This would handle the actual password reset with token validation
        # Implementation depends on your token strategy
        return Response({
            'message': 'Password reset functionality not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


class UserProfileView(generics.RetrieveAPIView):
    """Get user profile"""
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileUpdateView(generics.UpdateAPIView):
    """Update user profile"""
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        # Log profile update
        UserActivity.objects.create(
            user=request.user,
            activity_type='profile_update',
            description='Profile updated successfully',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return response

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminUserListView(generics.ListAPIView):
    """Admin view to list all users"""
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user_type', 'is_approved', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'member_number']
    ordering_fields = ['date_joined', 'username', 'is_approved']
    ordering = ['-date_joined']

    def get_queryset(self):
        if not self.request.user.user_type == 'admin':
            return CustomUser.objects.none()
        return CustomUser.objects.all()


class AdminUserApprovalView(generics.UpdateAPIView):
    """Admin endpoint to approve/reject users"""
    serializer_class = AdminUserApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.user_type == 'admin':
            return CustomUser.objects.none()
        return CustomUser.objects.all()

    def update(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Store approval status change flag
        approval_status_changed = getattr(user, '_approval_status_changed', False)
        approval_notes = getattr(user, '_approval_notes', '')
        
        updated_user = serializer.save()
        
        # Log the approval/rejection
        action = 'approved' if updated_user.is_approved else 'rejected'
        UserActivity.objects.create(
            user=updated_user,
            activity_type=f'account_{action}',
            description=f'Account {action} by admin: {approval_notes}',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # TODO: Send email notification about approval/rejection
        
        return Response({
            'user': CustomUserSerializer(updated_user).data,
            'message': f'User {action} successfully'
        })

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserDashboardView(APIView):
    """User dashboard with summary information"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Basic user info
        dashboard_data = {
            'user': CustomUserSerializer(user).data,
            'membership_status': {
                'is_approved': user.is_approved,
                'member_number': user.member_number,
                'membership_duration': user.membership_duration,
                'date_approved': user.date_approved,
            }
        }
        
        # Investment summary
        try:
            from investments.models import InvestmentSummary
            investment_summary = InvestmentSummary.objects.get(member=user)
            dashboard_data['investments'] = {
                'total_investments': investment_summary.total_investments,
                'share_capital': investment_summary.total_share_capital,
                'monthly_investments': investment_summary.total_monthly_investments,
                'loan_eligible_amount': investment_summary.loan_eligible_amount,
                'maximum_loan_amount': investment_summary.maximum_loan_amount,
                'ranking': investment_summary.ranking_by_total,
            }
        except:
            dashboard_data['investments'] = {
                'total_investments': Decimal('0.00'),
                'share_capital': Decimal('0.00'),
                'monthly_investments': Decimal('0.00'),
                'loan_eligible_amount': Decimal('0.00'),
                'maximum_loan_amount': Decimal('0.00'),
                'ranking': None,
            }
        
        # Loan summary
        try:
            from loans.models import Loan
            active_loans = Loan.objects.filter(borrower=user, status__in=['active', 'overdue'])
            total_loan_balance = active_loans.aggregate(
                total=Sum('balance_remaining')
            )['total'] or Decimal('0.00')
            
            dashboard_data['loans'] = {
                'active_loans_count': active_loans.count(),
                'total_loan_balance': total_loan_balance,
                'has_overdue_loans': active_loans.filter(status='overdue').exists(),
            }
        except:
            dashboard_data['loans'] = {
                'active_loans_count': 0,
                'total_loan_balance': Decimal('0.00'),
                'has_overdue_loans': False,
            }
        
        # Recent transactions
        try:
            from transactions.models import Transaction
            recent_transactions = Transaction.objects.filter(
                member=user
            ).order_by('-created_at')[:5]
            
            dashboard_data['recent_transactions'] = [
                {
                    'id': txn.id,
                    'type': txn.transaction_type,
                    'amount': txn.amount,
                    'status': txn.status,
                    'date': txn.created_at,
                    'description': txn.description,
                }
                for txn in recent_transactions
            ]
        except:
            dashboard_data['recent_transactions'] = []
        
        # Notifications count
        try:
            from notifications.models import Notification
            unread_notifications = Notification.objects.filter(
                recipient=user, is_read=False
            ).count()
            dashboard_data['unread_notifications'] = unread_notifications
        except:
            dashboard_data['unread_notifications'] = 0
        
        return Response(dashboard_data)


class UserStatsView(APIView):
    """Detailed user statistics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided and user is admin, get stats for that user
        if pk and request.user.user_type == 'admin':
            try:
                target_user = CustomUser.objects.get(pk=pk)
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            target_user = request.user
        
        # Calculate comprehensive stats
        stats = self.calculate_user_stats(target_user)
        
        return Response(UserStatsSerializer(stats).data)

    def calculate_user_stats(self, user):
        """Calculate comprehensive user statistics"""
        stats = {}
        
        # Investment stats
        try:
            from investments.models import Investment, InvestmentSummary
            
            confirmed_investments = Investment.objects.filter(
                member=user, status='confirmed'
            )
            
            stats['total_investments'] = confirmed_investments.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            stats['share_capital'] = confirmed_investments.filter(
                investment_type='share_capital'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            stats['monthly_investments'] = confirmed_investments.filter(
                investment_type='monthly_investment'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Get ranking
            try:
                summary = InvestmentSummary.objects.get(member=user)
                stats['ranking'] = summary.ranking_by_total or 0
            except:
                stats['ranking'] = 0
                
        except:
            stats.update({
                'total_investments': Decimal('0.00'),
                'share_capital': Decimal('0.00'),
                'monthly_investments': Decimal('0.00'),
                'ranking': 0,
            })
        
        # Loan stats
        try:
            from loans.models import Loan
            
            all_loans = Loan.objects.filter(borrower=user)
            active_loans = all_loans.filter(status__in=['active', 'overdue'])
            
            stats['total_loans'] = all_loans.aggregate(
                total=Sum('principal_amount')
            )['total'] or Decimal('0.00')
            
            stats['active_loans'] = active_loans.aggregate(
                total=Sum('balance_remaining')
            )['total'] or Decimal('0.00')
            
            stats['loans_paid'] = all_loans.filter(status='paid_off').aggregate(
                total=Sum('principal_amount')
            )['total'] or Decimal('0.00')
            
        except:
            stats.update({
                'total_loans': Decimal('0.00'),
                'active_loans': Decimal('0.00'),
                'loans_paid': Decimal('0.00'),
            })
        
        # Get total member count for ranking context
        stats['total_members'] = CustomUser.objects.filter(
            user_type='member', is_approved=True
        ).count()
        
        return stats


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user management"""
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user_type', 'is_approved', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']

    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return CustomUser.objects.all()
        else:
            # Regular users can only see their own profile
            return CustomUser.objects.filter(id=self.request.user.id)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get user statistics"""
        user = self.get_object()
        if request.user.user_type != 'admin' and request.user != user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        view = UserStatsView()
        stats = view.calculate_user_stats(user)
        return Response(UserStatsSerializer(stats).data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user activity logs"""
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['activity_type', 'user']
    ordering = ['-timestamp']

    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return UserActivity.objects.all()
        else:
            # Regular users can only see their own activities
            return UserActivity.objects.filter(user=self.request.user)