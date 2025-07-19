from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .models import User, Profile
from subscribtion.models import *

def signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Simple validation
        if password1 != password2:
            return render(request, 'accounts/signup.html', {'error': 'Passwords do not match'})
            
        if User.objects.filter(email=email).exists():
            return render(request, 'accounts/signup.html', {'error': 'Email already exists'})
            
        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/signup.html', {'error': 'Username already exists'})
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password1,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create profile
        Profile.objects.create(user=user)
        
        # Log in user
        auth_login(request, user)
        return redirect('index')
    
    return render(request, 'accounts/signup.html')

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('index')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'accounts/login.html')


# profile is unique to oeach user as set internally in the user app
def validate_image_file(profile_photo):
    allowed_mimetypes = ['image/jpeg', 'image/png', 'image/jpg']
    return profile_photo.content_type in allowed_mimetypes and profile_photo.size <= 36700160  # 35MB limit

def profile(request):
    if not request.user.is_authenticated:
       return redirect('login')
       
    if request.method == "POST":
        PIC = request.FILES.get('profile_photo')
        if PIC:
            if validate_image_file(PIC):
                try:
                    user_profile = Profile.objects.get(user=request.user)
                except Profile.DoesNotExist:
                    # Profile doesn't exist, create a new one
                    user_profile = Profile.objects.create(user=request.user)
                # Update profile photo in either case
                user_profile.profile_photo = PIC
                user_profile.save()
                
    user_x = request.user
    current_user = request.user.username

    try:
        user_profile = Profile.objects.get(user=user_x)
        profile_photo_url = user_profile.profile_photo.url if user_profile.profile_photo else None
    except:
        profile_photo_url = None 
    
    # Get user's enrolled courses
    # Active enrollments - not completed
    active_enrollments = Enrollment.objects.filter(
        user=user_x,
        completed_at__isnull=True,
        enrolement_status='active'
    ).select_related('course', 'course__category')
    
    # Completed enrollments
    completed_enrollments = Enrollment.objects.filter(
        user=user_x,
        completed_at__isnull=False
    ).select_related('course', 'course__category')
    
    # Add progress information to active enrollments
    for enrollment in active_enrollments:
        try:
            progress = CourseProgress.objects.get(enrollment_model=enrollment)
            enrollment.progress = progress
        except CourseProgress.DoesNotExist:
            # Create default progress
            progress = CourseProgress.objects.create(
                enrollment_model=enrollment,
                progress_percentage=0.0,
                completed=False
            )
            enrollment.progress = progress
    
    # Add certificate information to completed enrollments
    for enrollment in completed_enrollments:
        try:
            certificate = Certificate.objects.get(enrollment=enrollment)
            enrollment.certificate = certificate
        except Certificate.DoesNotExist:
            enrollment.certificate = None
    
    context = {
        "user_x": user_x,
        "current_user": current_user,
        "profile_photo_url": profile_photo_url,
        "active_enrollments": active_enrollments,
        "completed_enrollments": completed_enrollments,
    }
    return render(request, 'accounts/profile.html', context)



@login_required
def logout(request):
    auth_logout(request)
    return redirect('login')

@login_required
def change_email(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=request.user.email, password=password)
        if user is not None:
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                return render(request, 'accounts/profile.html', {'error': 'Email already exists'})
            
            user.email = new_email
            user.save()
            return redirect('profile')
        else:
            return render(request, 'accounts/profile.html', {'error': 'Invalid password'})
    
    return redirect('profile')

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = authenticate(request, email=request.user.email, password=current_password)
        if user is not None:
            if new_password != confirm_password:
                return render(request, 'accounts/profile.html', {'error': 'Passwords do not match'})
            
            user.set_password(new_password)
            user.save()
            auth_login(request, user)
            return redirect('profile')
        else:
            return render(request, 'accounts/profile.html', {'error': 'Invalid current password'})
    
    return redirect('profile')

@login_required
def change_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('new_username')
        password = request.POST.get('password')
        
        user = authenticate(request, email=request.user.email, password=password)
        if user is not None:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                return render(request, 'accounts/profile.html', {'error': 'Username already exists'})
            
            user.username = new_username
            user.save()
            return redirect('profile')
        else:
            return render(request, 'accounts/profile.html', {'error': 'Invalid password'})
    
    return redirect('profile')

@login_required
def change_first_name(request):
    if request.method == 'POST':
        new_first_name = request.POST.get('new_first_name')
        
        user = request.user
        user.first_name = new_first_name
        user.save()
        return redirect('profile')
    
    return redirect('profile')

@login_required
def change_last_name(request):
    if request.method == 'POST':
        new_last_name = request.POST.get('new_last_name')
        
        user = request.user
        user.last_name = new_last_name
        user.save()
        return redirect('profile')
    
    return redirect('profile')

