from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'applications', views.MemberApplicationViewSet, basename='application')
router.register(r'documents', views.ApplicationDocumentViewSet, basename='document')
router.register(r'follow-ups', views.ApplicationFollowUpViewSet, basename='followup')
router.register(r'comments', views.ApplicationCommentViewSet, basename='comment')

urlpatterns = [
    # Public application submission
    path('submit/', views.SubmitApplicationView.as_view(), name='submit-application'),
    
    # Application management
    path('<int:pk>/approve/', views.ApproveApplicationView.as_view(), name='approve-application'),
    path('<int:pk>/reject/', views.RejectApplicationView.as_view(), name='reject-application'),
    path('<int:pk>/request-info/', views.RequestMoreInfoView.as_view(), name='request-more-info'),
    
    # Document upload
    path('<int:application_id>/documents/upload/', views.UploadDocumentView.as_view(), name='upload-document'),
    
    # Admin dashboard
    path('admin/dashboard/', views.ApplicationDashboardView.as_view(), name='application-dashboard'),
    path('admin/pending/', views.PendingApplicationsView.as_view(), name='pending-applications'),
    path('admin/statistics/', views.ApplicationStatisticsView.as_view(), name='application-statistics'),
    
    # Include router URLs
    path('', include(router.urls)),
]