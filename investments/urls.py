from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'investments', views.InvestmentViewSet, basename='investment')
router.register(r'summaries', views.InvestmentSummaryViewSet, basename='summary')
router.register(r'targets', views.InvestmentTargetViewSet, basename='target')
router.register(r'transactions', views.InvestmentTransactionViewSet, basename='transaction')
router.register(r'dividends', views.DividendPaymentViewSet, basename='dividend')

urlpatterns = [
    # Investment submission
    path('invest/', views.CreateInvestmentView.as_view(), name='create-investment'),
    path('share-capital/', views.ShareCapitalInvestmentView.as_view(), name='share-capital-investment'),
    path('monthly-investment/', views.MonthlyInvestmentView.as_view(), name='monthly-investment'),
    
    # Investment management
    path('<int:pk>/confirm/', views.ConfirmInvestmentView.as_view(), name='confirm-investment'),
    path('<int:pk>/reject/', views.RejectInvestmentView.as_view(), name='reject-investment'),
    
    # Member investment dashboard
    path('my-investments/', views.MyInvestmentsView.as_view(), name='my-investments'),
    path('my-summary/', views.MyInvestmentSummaryView.as_view(), name='my-investment-summary'),
    
    # Investment statistics
    path('statistics/', views.InvestmentStatisticsView.as_view(), name='investment-statistics'),
    path('rankings/', views.InvestmentRankingsView.as_view(), name='investment-rankings'),
    
    # Admin endpoints
    path('admin/pending/', views.PendingInvestmentsView.as_view(), name='pending-investments'),
    path('admin/dashboard/', views.InvestmentDashboardView.as_view(), name='investment-dashboard'),
    path('admin/bulk-confirm/', views.BulkConfirmInvestmentsView.as_view(), name='bulk-confirm-investments'),
    
    # Dividend management
    path('dividends/calculate/<int:year>/', views.CalculateDividendsView.as_view(), name='calculate-dividends'),
    path('dividends/pay/', views.PayDividendsView.as_view(), name='pay-dividends'),
    
    # Reports
    path('reports/monthly/', views.MonthlyInvestmentReportView.as_view(), name='monthly-investment-report'),
    path('reports/member/<int:member_id>/', views.MemberInvestmentReportView.as_view(), name='member-investment-report'),
    
    # Include router URLs
    path('', include(router.urls)),
]