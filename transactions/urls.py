from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'balances', views.MemberBalanceViewSet, basename='balance')
router.register(r'fees', views.TransactionFeeViewSet, basename='fee')
router.register(r'batches', views.TransactionBatchViewSet, basename='batch')
router.register(r'recurring', views.RecurringTransactionViewSet, basename='recurring')
router.register(r'receipts', views.TransactionReceiptViewSet, basename='receipt')
router.register(r'audit-logs', views.TransactionAuditLogViewSet, basename='audit-log')

urlpatterns = [
    # Transaction processing
    path('deposit/', views.CreateDepositView.as_view(), name='create-deposit'),
    path('withdraw/', views.CreateWithdrawalView.as_view(), name='create-withdrawal'),
    path('<int:pk>/complete/', views.CompleteTransactionView.as_view(), name='complete-transaction'),
    path('<int:pk>/fail/', views.FailTransactionView.as_view(), name='fail-transaction'),
    path('<int:pk>/reverse/', views.ReverseTransactionView.as_view(), name='reverse-transaction'),
    
    # Member transaction dashboard
    path('my-transactions/', views.MyTransactionsView.as_view(), name='my-transactions'),
    path('my-balance/', views.MyBalanceView.as_view(), name='my-balance'),
    path('my-statement/', views.MyStatementView.as_view(), name='my-statement'),
    
    # Admin transaction management
    path('admin/pending/', views.PendingTransactionsView.as_view(), name='pending-transactions'),
    path('admin/dashboard/', views.TransactionDashboardView.as_view(), name='transaction-dashboard'),
    path('admin/bulk-process/', views.BulkProcessTransactionsView.as_view(), name='bulk-process-transactions'),
    
    # Batch processing
    path('batches/create/', views.CreateTransactionBatchView.as_view(), name='create-transaction-batch'),
    path('batches/<int:pk>/process/', views.ProcessTransactionBatchView.as_view(), name='process-transaction-batch'),
    
    # Recurring transactions
    path('recurring/create/', views.CreateRecurringTransactionView.as_view(), name='create-recurring-transaction'),
    path('recurring/<int:pk>/execute/', views.ExecuteRecurringTransactionView.as_view(), name='execute-recurring-transaction'),
    path('recurring/<int:pk>/pause/', views.PauseRecurringTransactionView.as_view(), name='pause-recurring-transaction'),
    path('recurring/<int:pk>/resume/', views.ResumeRecurringTransactionView.as_view(), name='resume-recurring-transaction'),
    
    # Fee management
    path('fees/calculate/', views.CalculateTransactionFeeView.as_view(), name='calculate-transaction-fee'),
    
    # Reports and analytics
    path('reports/daily/', views.DailyTransactionReportView.as_view(), name='daily-transaction-report'),
    path('reports/monthly/', views.MonthlyTransactionReportView.as_view(), name='monthly-transaction-report'),
    path('reports/member/<int:member_id>/', views.MemberTransactionReportView.as_view(), name='member-transaction-report'),
    path('analytics/cash-flow/', views.CashFlowAnalyticsView.as_view(), name='cash-flow-analytics'),
    path('analytics/transaction-trends/', views.TransactionTrendsView.as_view(), name='transaction-trends'),
    
    # Receipt management
    path('<int:transaction_id>/receipt/', views.GenerateReceiptView.as_view(), name='generate-receipt'),
    path('receipts/<int:pk>/download/', views.DownloadReceiptView.as_view(), name='download-receipt'),
    path('receipts/<int:pk>/email/', views.EmailReceiptView.as_view(), name='email-receipt'),
    
    # Balance management
    path('balances/update-all/', views.UpdateAllBalancesView.as_view(), name='update-all-balances'),
    path('balances/<int:member_id>/reconcile/', views.ReconcileBalanceView.as_view(), name='reconcile-balance'),
    
    # Include router URLs
    path('', include(router.urls)),
]