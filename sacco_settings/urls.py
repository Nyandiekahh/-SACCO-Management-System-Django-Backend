from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'loan-types', views.LoanTypeViewSet, basename='loan-type')
router.register(r'investment-types', views.InvestmentTypeViewSet, basename='investment-type')
router.register(r'email-templates', views.EmailTemplateViewSet, basename='email-template')

urlpatterns = [
    # Main SACCO settings
    path('sacco/', views.SaccoSettingsView.as_view(), name='sacco-settings'),
    path('sacco/update/', views.UpdateSaccoSettingsView.as_view(), name='update-sacco-settings'),
    
    # System configuration
    path('system/', views.SystemConfigurationView.as_view(), name='system-configuration'),
    path('system/update/', views.UpdateSystemConfigurationView.as_view(), name='update-system-configuration'),
    
    # Loan type management
    path('loan-types/create/', views.CreateLoanTypeView.as_view(), name='create-loan-type'),
    path('loan-types/<int:pk>/update/', views.UpdateLoanTypeView.as_view(), name='update-loan-type'),
    path('loan-types/<int:pk>/toggle-active/', views.ToggleLoanTypeActiveView.as_view(), name='toggle-loan-type-active'),
    
    # Investment type management
    path('investment-types/create/', views.CreateInvestmentTypeView.as_view(), name='create-investment-type'),
    path('investment-types/<int:pk>/update/', views.UpdateInvestmentTypeView.as_view(), name='update-investment-type'),
    path('investment-types/<int:pk>/toggle-active/', views.ToggleInvestmentTypeActiveView.as_view(), name='toggle-investment-type-active'),
    
    # Email template management
    path('email-templates/<str:template_type>/', views.EmailTemplateDetailView.as_view(), name='email-template-detail'),
    path('email-templates/<str:template_type>/update/', views.UpdateEmailTemplateView.as_view(), name='update-email-template'),
    path('email-templates/<str:template_type>/test/', views.TestEmailTemplateView.as_view(), name='test-email-template'),
    
    # Settings export/import
    path('export/', views.ExportSettingsView.as_view(), name='export-settings'),
    path('import/', views.ImportSettingsView.as_view(), name='import-settings'),
    
    # Settings backup
    path('backup/', views.BackupSettingsView.as_view(), name='backup-settings'),
    path('restore/', views.RestoreSettingsView.as_view(), name='restore-settings'),
    
    # Include router URLs
    path('', include(router.urls)),
]