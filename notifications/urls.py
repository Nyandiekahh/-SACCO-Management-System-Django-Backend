from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'email-notifications', views.EmailNotificationViewSet, basename='email-notification')
router.register(r'bulk-notifications', views.BulkNotificationViewSet, basename='bulk-notification')
router.register(r'sms-notifications', views.SMSNotificationViewSet, basename='sms-notification')
router.register(r'templates', views.NotificationTemplateViewSet, basename='notification-template')
router.register(r'logs', views.NotificationLogViewSet, basename='notification-log')

urlpatterns = [
    # User notification management
    path('my-notifications/', views.MyNotificationsView.as_view(), name='my-notifications'),
    path('unread-count/', views.UnreadNotificationCountView.as_view(), name='unread-notification-count'),
    path('<int:pk>/mark-read/', views.MarkNotificationReadView.as_view(), name='mark-notification-read'),
    path('mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark-all-notifications-read'),
    
    # Notification preferences
    path('preferences/', views.NotificationPreferencesView.as_view(), name='notification-preferences'),
    path('preferences/update/', views.UpdateNotificationPreferencesView.as_view(), name='update-notification-preferences'),
    
    # Email notifications
    path('email/send/', views.SendEmailNotificationView.as_view(), name='send-email-notification'),
    path('email/send-pending/', views.SendPendingEmailsView.as_view(), name='send-pending-emails'),
    path('email/<int:pk>/resend/', views.ResendEmailNotificationView.as_view(), name='resend-email-notification'),
    
    # Bulk notifications
    path('bulk/create/', views.CreateBulkNotificationView.as_view(), name='create-bulk-notification'),
    path('bulk/<int:pk>/send/', views.SendBulkNotificationView.as_view(), name='send-bulk-notification'),
    path('bulk/<int:pk>/schedule/', views.ScheduleBulkNotificationView.as_view(), name='schedule-bulk-notification'),
    path('bulk/<int:pk>/cancel/', views.CancelBulkNotificationView.as_view(), name='cancel-bulk-notification'),
    
    # SMS notifications
    path('sms/send/', views.SendSMSNotificationView.as_view(), name='send-sms-notification'),
    path('sms/send-pending/', views.SendPendingSMSView.as_view(), name='send-pending-sms'),
    
    # Notification templates
    path('templates/<str:template_type>/', views.NotificationTemplateDetailView.as_view(), name='notification-template-detail'),
    path('templates/<str:template_type>/preview/', views.PreviewNotificationTemplateView.as_view(), name='preview-notification-template'),
    
    # Admin notification management
    path('admin/dashboard/', views.NotificationDashboardView.as_view(), name='notification-dashboard'),
    path('admin/analytics/', views.NotificationAnalyticsView.as_view(), name='notification-analytics'),
    path('admin/failed-notifications/', views.FailedNotificationsView.as_view(), name='failed-notifications'),
    
    # Notification settings
    path('settings/', views.NotificationSettingsView.as_view(), name='notification-settings'),
    path('settings/update/', views.UpdateNotificationSettingsView.as_view(), name='update-notification-settings'),
    
    # Cleanup and maintenance
    path('cleanup/expired/', views.CleanupExpiredNotificationsView.as_view(), name='cleanup-expired-notifications'),
    path('cleanup/old/', views.CleanupOldNotificationsView.as_view(), name='cleanup-old-notifications'),
    
    # Webhook endpoints (for email/SMS providers)
    path('webhooks/email-delivery/', views.EmailDeliveryWebhookView.as_view(), name='email-delivery-webhook'),
    path('webhooks/sms-delivery/', views.SMSDeliveryWebhookView.as_view(), name='sms-delivery-webhook'),
    
    # Include router URLs
    path('', include(router.urls)),
]