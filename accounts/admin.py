from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CustomUser, UserProfile, UserActivity


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        'username', 'email', 'full_name', 'user_type', 'is_approved', 
        'member_number', 'membership_duration', 'is_active', 'date_joined'
    ]
    list_filter = [
        'user_type', 'is_approved', 'is_active', 'is_staff', 'date_joined'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'member_number']
    readonly_fields = ['date_joined', 'last_login', 'member_number', 'membership_duration']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('SACCO Information', {
            'fields': (
                'user_type', 'is_approved', 'date_approved', 'member_number',
                'phone_number', 'address', 'employment_status', 'school_name'
            )
        }),
        ('KYC Documents', {
            'fields': ('profile_image', 'id_document', 'id_with_photo'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': (
                'email', 'first_name', 'last_name', 'phone_number',
                'user_type', 'address'
            )
        }),
    )
    
    actions = ['approve_members', 'deactivate_users', 'generate_member_numbers']
    
    def approve_members(self, request, queryset):
        updated = 0
        for user in queryset.filter(user_type='member', is_approved=False):
            user.is_approved = True
            user.save()
            updated += 1
        
        self.message_user(request, f'{updated} members approved successfully.')
    approve_members.short_description = 'Approve selected members'
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated successfully.')
    deactivate_users.short_description = 'Deactivate selected users'
    
    def generate_member_numbers(self, request, queryset):
        updated = 0
        for user in queryset.filter(is_approved=True, member_number__isnull=True):
            user.generate_member_number()
            updated += 1
        
        self.message_user(request, f'{updated} member numbers generated successfully.')
    generate_member_numbers.short_description = 'Generate member numbers'


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'id_number', 'date_of_birth', 'occupation', 
        'monthly_income', 'next_of_kin_name', 'created_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = [
        'user__username', 'user__email', 'id_number', 
        'next_of_kin_name', 'occupation'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'bio', 'date_of_birth', 'id_number')
        }),
        ('Employment/Education', {
            'fields': ('occupation', 'monthly_income')
        }),
        ('Next of Kin', {
            'fields': (
                'next_of_kin_name', 'next_of_kin_phone', 
                'next_of_kin_relationship'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'activity_type', 'description', 'ip_address', 'timestamp'
    ]
    list_filter = ['activity_type', 'timestamp']
    search_fields = ['user__username', 'activity_type', 'description']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'description')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# Customize admin site
admin.site.site_header = 'SACCO Management System'
admin.site.site_title = 'SACCO Admin'
admin.site.index_title = 'SACCO Administration'