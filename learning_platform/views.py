from django.http import HttpResponse, FileResponse, HttpResponseForbidden
from django.views.static import serve
from django.conf import settings
import os
import time
import secrets

def protected_media_view(request, path):
    """
    This is the FINAL, CORRECTED version. It fixes the video loading bug by
    removing the aggressive single-use token logic and relying only on the
    short expiration time, which is the correct and robust approach.
    """
    path_parts = path.split('/')
    
    # Public access for images
    if path_parts and path_parts[0] in ['courses', 'profile_photos']:
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    
    # Authentication required for everything else
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    
    # Certificate downloads
    if path_parts and path_parts[0] == 'certificates':
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    
    # Video streaming with token validation
    if path_parts and path_parts[0] == 'topics' and len(path_parts) > 1 and path_parts[1] == 'videos':
        
        # --- TOKEN VALIDATION LOGIC ---
        
        provided_token = request.GET.get('token')
        token_data = request.session.get('video_token_data')

        if not provided_token or not token_data:
            return HttpResponseForbidden("Access denied (token missing).")
            
        if time.time() > token_data.get('expires', 0):
            return HttpResponseForbidden("Access link has expired.")

        if not secrets.compare_digest(provided_token, token_data.get('token')):
            return HttpResponseForbidden("Access denied (invalid token).")

        # --- START OF THE CRITICAL FIX ---
        # The line that deleted the token (`del request.session['video_token_data']`)
        # has been REMOVED. This allows the browser to make multiple necessary
        # requests within the short time window to load the video correctly.
        # --- END OF THE CRITICAL FIX ---

        video_filename = path_parts[-1]
        
        from courses.models import Topic
        try:
            topic = Topic.objects.filter(VIDEO_CINTETN_FILE__contains=video_filename).first()
            if topic:
                from subscribtion.models import Enrollment
                is_enrolled = Enrollment.objects.filter(user=request.user, course=topic.section.course).exists()
                if is_enrolled or request.user.is_staff:
                    response = FileResponse(open(os.path.join(settings.MEDIA_ROOT, path), 'rb'), content_type='video/mp4')
                    response['Accept-Ranges'] = 'bytes' # For seeking
                    response['Content-Disposition'] = 'inline'
                    return response
                else:
                    return HttpResponse('Not enrolled in this course.', status=403)
            else:
                return HttpResponse('Content not found.', status=404)
        except Exception as e:
            return HttpResponse(f'An error occurred: {str(e)}', status=500)
    
    # Default deny
    return HttpResponse('Access denied.', status=403)