# accounts/serializers.py
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import User, Profile

class UserCreateSerializer(BaseUserCreateSerializer):
    """
    Serializer for user creation that extends Djoser's UserCreateSerializer.
    Customized for our User model with email as the login field.
    """
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ['id', 'email', 'username', 'password', 'first_name', 'last_name']

class UserSerializer(BaseUserSerializer):
    """
    Serializer for retrieving user information that extends Djoser's UserSerializer.
    """
    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active']
        read_only_fields = ['id', 'is_active']

# serializers.py
class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the user profile, including the profile photo.
    """
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['profile_photo', 'profile_photo_url']

    def get_profile_photo_url(self, obj):
        if obj.profile_photo:
            return obj.profile_photo.url
        return None

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer that includes both user and profile information.
    """
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'profile']
        read_only_fields = ['id', 'email']

    def get_profile(self, obj):
        try:
            profile = Profile.objects.get(user=obj)
            return ProfileSerializer(profile).data
        except Profile.DoesNotExist:
            return None

class EmailChangeSerializer(serializers.Serializer):
    """
    Serializer for changing user email address with current password verification.
    """
    current_password = serializers.CharField(style={'input_type': 'password'})
    new_email = serializers.EmailField()

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_email(self, value):
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

class UsernameChangeSerializer(serializers.Serializer):
    """
    Serializer for changing username with current password verification.
    """
    current_password = serializers.CharField(style={'input_type': 'password'})
    new_username = serializers.CharField(max_length=50)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_username(self, value):
        user = self.context['request'].user
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for resetting password with current password verification.
    """
    current_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(style={'input_type': 'password'})
    confirm_password = serializers.CharField(style={'input_type': 'password'})

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match."})
        return data
