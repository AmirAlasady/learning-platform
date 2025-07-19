from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.static import serve
from django.conf import settings
import os
from django.http import HttpResponse, FileResponse

# Protected media view
#def protected_media_view(request, path):
#    if not request.user.is_authenticated:
#        return HttpResponse('Unauthorized', status=401)
#    # Add additional permission checks here if needed
#    return serve(request, path, document_root=settings.MEDIA_ROOT)
# In learning_platform/views.py - enhanced protected_media_view

"""
def protected_media_view(request, path):


    # do normal stuf here :-

    # -----------------------------------------------------
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    
    # Extract path components to determine content type
    path_parts = path.split('/')
    
    # ALLOW certificate downloads - this is the only content users can download
    if path_parts and path_parts[0] == 'certificates':
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    
    # For videos - add additional protection
    if path_parts and path_parts[0] == 'topics' and len(path_parts) > 1 and path_parts[1] == 'videos':
        # Get video filename
        video_filename = path_parts[-1]
        
        # Find the topic that uses this video
        from courses.models import Topic
        try:
            topic = Topic.objects.filter(VIDEO_CINTETN_FILE__contains=video_filename).first()
            
            if topic:
                # Check if user is enrolled in this course
                from subscribtion.models import Enrollment
                is_enrolled = Enrollment.objects.filter(
                    user=request.user,
                    course=topic.section.course,
                    enrolement_status='active'
                ).exists()
                
                if is_enrolled or request.user.is_staff:
                    # Stream the video with content-disposition headers to prevent download
                    response = FileResponse(
                        open(os.path.join(settings.MEDIA_ROOT, path), 'rb'),
                        content_type='video/mp4',
                    )
                    # Use inline disposition to prevent download prompts
                    response['Content-Disposition'] = 'inline'
                    response['X-Frame-Options'] = 'SAMEORIGIN'
                    # Disable the browser's ability to save the video
                    response['X-Content-Type-Options'] = 'nosniff'
                    # Try to prevent caching
                    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                    response['Pragma'] = 'no-cache'
                    return response
                else:
                    return HttpResponse('You are not enrolled in this course', status=403)
            else:
                return HttpResponse('Content not found', status=404)
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}', status=500)
    
    # For profile photos and other non-course content
    if path_parts and path_parts[0] in ['profile_photos', 'courses']:
        # Allow viewing but prevent downloading
        response = FileResponse(
            open(os.path.join(settings.MEDIA_ROOT, path), 'rb'),
        )
        response['Content-Disposition'] = 'inline'
        return response
    
    # Default deny for any other media
    return HttpResponse('Access denied', status=403)
"""

from django.http import HttpResponse, FileResponse
from django.views.static import serve
from django.conf import settings
import os

def protected_media_view(request, path):
    """
    Enhanced media protection handler that:
    1. Allows public access to course images and profile photos
    2. Prevents unauthorized access to other media types
    3. Allows certificate downloads
    4. Streams content with protective headers
    5. Verifies user enrollment for course content
    """
    # Extract path components to determine content type
    path_parts = path.split('/')
    
    # PUBLIC ACCESS: Course images and profile photos
    if path_parts and path_parts[0] in ['courses', 'profile_photos']:
        # Allow viewing but prevent downloading
        response = FileResponse(
            open(os.path.join(settings.MEDIA_ROOT, path), 'rb'),
        )
        response['Content-Disposition'] = 'inline'
        return response
    
    # Require authentication for other media types
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    
    # ALLOW certificate downloads
    if path_parts and path_parts[0] == 'certificates':
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    
    # For videos - add additional protection
    if path_parts and path_parts[0] == 'topics' and len(path_parts) > 1 and path_parts[1] == 'videos':
        # Get video filename
        video_filename = path_parts[-1]
        
        # Find the topic that uses this video
        from courses.models import Topic
        try:
            topic = Topic.objects.filter(VIDEO_CINTETN_FILE__contains=video_filename).first()
            
            if topic:
                # Check if user is enrolled in this course
                from subscribtion.models import Enrollment
                is_enrolled = Enrollment.objects.filter(
                    user=request.user,
                    course=topic.section.course,
                    enrolement_status='active'
                ).exists()
                
                if is_enrolled or request.user.is_staff:
                    # Stream the video with content-disposition headers to prevent download
                    response = FileResponse(
                        open(os.path.join(settings.MEDIA_ROOT, path), 'rb'),
                        content_type='video/mp4',
                    )
                    # Use inline disposition to prevent download prompts
                    response['Content-Disposition'] = 'inline'
                    response['X-Frame-Options'] = 'SAMEORIGIN'
                    # Disable the browser's ability to save the video
                    response['X-Content-Type-Options'] = 'nosniff'
                    # Try to prevent caching
                    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                    response['Pragma'] = 'no-cache'
                    return response
                else:
                    return HttpResponse('You are not enrolled in this course', status=403)
            else:
                return HttpResponse('Content not found', status=404)
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}', status=500)
    
    # Default deny for any other media
    return HttpResponse('Access denied', status=403)