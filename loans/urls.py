from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'applications', views.LoanApplicationViewSet, basename='loan-application')
router.register(r'loans', views.LoanViewSet, basename='loan')
router.register(r'payments', views.LoanPaymentViewSet, basename='loan-payment')
router.register(r'guarantors', views.LoanGuarantorViewSet, basename='guarantor')
router.register(r'schedules', views.LoanScheduleViewSet, basename='schedule')
router.register(r'penalties', views.LoanPenaltyViewSet, basename='penalty')
router.register(r'collateral', views.LoanCollateralViewSet, basename='collateral')
router.register(r'comments', views.LoanCommentViewSet, basename='loan-comment')

urlpatterns = [
    # Loan application process
    path('apply/', views.ApplyForLoanView.as_view(), name='apply-for-loan'),
    path('applications/<int:pk>/approve/', views.ApproveLoanView.as_view(), name='approve-loan'),
    path('applications/<int:pk>/reject/', views.RejectLoanView.as_view(), name='reject-loan'),
    path('applications/<int:pk>/disburse/', views.DisburseLoanView.as_view(), name='disburse-loan'),
    
    # Guarantor management
    path('applications/<int:application_id>/guarantors/add/', views.AddGuarantorView.as_view(), name='add-guarantor'),
    path('guarantors/<int:pk>/confirm/', views.ConfirmGuaranteeView.as_view(), name='confirm-guarantee'),
    path('guarantors/<int:pk>/decline/', views.DeclineGuaranteeView.as_view(), name='decline-guarantee'),
    
    # Loan payments
    path('payments/make/', views.MakeLoanPaymentView.as_view(), name='make-loan-payment'),
    path('payments/<int:pk>/confirm/', views.ConfirmLoanPaymentView.as_view(), name='confirm-loan-payment'),
    path('payments/<int:pk>/reject/', views.RejectLoanPaymentView.as_view(), name='reject-loan-payment'),
    
    # Member loan dashboard
    path('my-loans/', views.MyLoansView.as_view(), name='my-loans'),
    path('my-guarantees/', views.MyGuaranteesView.as_view(), name='my-guarantees'),
    path('my-loan-history/', views.MyLoanHistoryView.as_view(), name='my-loan-history'),
    
    # Loan management
    path('<int:pk>/schedule/', views.LoanScheduleView.as_view(), name='loan-schedule'),
    path('<int:pk>/generate-schedule/', views.GenerateLoanScheduleView.as_view(), name='generate-loan-schedule'),
    path('<int:pk>/apply-penalty/', views.ApplyLoanPenaltyView.as_view(), name='apply-loan-penalty'),
    path('<int:pk>/waive-penalty/', views.WaiveLoanPenaltyView.as_view(), name='waive-loan-penalty'),
    
    # Eligibility check
    path('check-eligibility/', views.CheckLoanEligibilityView.as_view(), name='check-loan-eligibility'),
    path('calculator/', views.LoanCalculatorView.as_view(), name='loan-calculator'),
    
    # Admin endpoints
    path('admin/pending-applications/', views.PendingLoanApplicationsView.as_view(), name='pending-loan-applications'),
    path('admin/pending-payments/', views.PendingLoanPaymentsView.as_view(), name='pending-loan-payments'),
    path('admin/overdue-loans/', views.OverdueLoansView.as_view(), name='overdue-loans'),
    path('admin/dashboard/', views.LoanDashboardView.as_view(), name='loan-dashboard'),
    path('admin/bulk-penalties/', views.BulkApplyPenaltiesView.as_view(), name='bulk-apply-penalties'),
    
    # Reports
    path('reports/loan-performance/', views.LoanPerformanceReportView.as_view(), name='loan-performance-report'),
    path('reports/defaulters/', views.LoanDefaultersReportView.as_view(), name='loan-defaulters-report'),
    path('reports/collections/', views.LoanCollectionsReportView.as_view(), name='loan-collections-report'),
    
    # Include router URLs
    path('', include(router.urls)),
]