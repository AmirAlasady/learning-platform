# accounts/api_views.py
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from .serializers import (
    PasswordResetSerializer,
    UserProfileSerializer, 
    EmailChangeSerializer, 
    UsernameChangeSerializer,
)
from .models import User, Profile

def validate_image_file(profile_photo):
    allowed_mimetypes = ['image/jpeg', 'image/png', 'image/jpg']
    return profile_photo.content_type in allowed_mimetypes and profile_photo.size <= 36700160  # 35MB limit

class UserProfileView(RetrieveUpdateAPIView):
    """
    API endpoint for retrieving and updating user profile information.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Return the user object, not just the profile photo URL
        return self.request.user

    def perform_update(self, serializer):
        # Save the user data
        user = serializer.save()

        # Handle profile data if it's in the request
        profile_data = self.request.data.get('profile', {})
        profile_photo = self.request.FILES.get('profile_photo')

        if profile_data or profile_photo:
            try:
                profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=user)

            # Handle profile photo if it's in the request
            if profile_photo and validate_image_file(profile_photo):
                profile.profile_photo = profile_photo
                profile.save()

class EmailChangeView(APIView):
    """
    API endpoint for changing user email address.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.email = serializer.validated_data['new_email']
            user.save()
            return Response({"detail": "Email changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UsernameChangeView(APIView):
    """
    API endpoint for changing username.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UsernameChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.username = serializer.validated_data['new_username']
            user.save()
            return Response({"detail": "Username changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameChangeView(APIView):
    """
    API endpoint for changing first name and last name.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        if not first_name and not last_name:
            return Response(
                {"detail": "At least one of first_name or last_name must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()

        return Response({"detail": "Name updated successfully."}, status=status.HTTP_200_OK)

class ProfilePhotoUploadView(APIView):
    """
    API endpoint for uploading profile photo.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if 'profile_photo' not in request.FILES:
            return Response(
                {"detail": "No image file provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        # Create profile if it doesn't exist
        profile, created = Profile.objects.get_or_create(user=user)
        profile.profile_photo = request.FILES['profile_photo']
        profile.save()

        return Response({"detail": "Profile photo uploaded successfully."}, status=status.HTTP_200_OK)

class PasswordResetView(APIView):
    """
    API endpoint for resetting password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']

            # Set the new password
            user.set_password(new_password)
            user.save()

            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
