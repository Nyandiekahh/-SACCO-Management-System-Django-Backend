from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, UserProfile, UserActivity


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'date_of_birth', 'id_number', 'next_of_kin_name',
            'next_of_kin_phone', 'next_of_kin_relationship', 'occupation',
            'monthly_income'
        ]


class CustomUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    membership_duration = serializers.ReadOnlyField()
    is_eligible_for_loan = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'user_type', 'is_approved', 'date_approved',
            'member_number', 'address', 'employment_status', 'school_name',
            'profile_image', 'id_document', 'id_with_photo', 'membership_duration',
            'is_eligible_for_loan', 'profile', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_type', 'is_approved', 'date_approved', 'member_number',
            'membership_duration', 'is_eligible_for_loan', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        user = CustomUser.objects.create_user(**validated_data)
        
        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)
        
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create profile
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    profile = UserProfileSerializer(required=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name',
            'last_name', 'phone_number', 'address', 'employment_status',
            'school_name', 'profile_image', 'id_document', 'id_with_photo', 'profile'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        profile_data = validated_data.pop('profile')
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(password=password, **validated_data)
        UserProfile.objects.create(user=user, **profile_data)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password')


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class AdminUserApprovalSerializer(serializers.ModelSerializer):
    approval_notes = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = ['is_approved', 'approval_notes']

    def update(self, instance, validated_data):
        approval_notes = validated_data.pop('approval_notes', '')
        is_approved = validated_data.get('is_approved', instance.is_approved)
        
        # Store approval notes for email notification
        instance._approval_notes = approval_notes
        instance._approval_status_changed = instance.is_approved != is_approved
        
        instance.is_approved = is_approved
        instance.save()
        
        return instance


class UserActivitySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = UserActivity
        fields = '__all__'


class UserStatsSerializer(serializers.Serializer):
    total_investments = serializers.DecimalField(max_digits=12, decimal_places=2)
    share_capital = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_investments = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_loans = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_loans = serializers.DecimalField(max_digits=12, decimal_places=2)
    loans_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    ranking = serializers.IntegerField()
    total_members = serializers.IntegerField()