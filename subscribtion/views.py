from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from courses.models import Course
from subscribtion.models import Enrollment, CourseProgress, TopicProgress
from utils import create_course_progress

# Import the ZainCash utilities
from zaincash import create_transaction, verify_transaction, decode_redirect_token

@login_required
def initiate_payment(request, course_id):
    """
    Initiate payment process for a course.
    Creates a ZainCash transaction and redirects to their payment page.
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "You are already enrolled in this course.")
        return redirect('course_detail', course_id=course_id)
    
    # Generate the redirect URL for ZainCash callback
    redirect_url = request.build_absolute_uri(reverse('payment_callback'))
    
    # Store payment information in session for later verification
    request.session['payment_info'] = {
        'course_id': course_id,
        'amount': float(course.price),
        'timestamp': timezone.now().isoformat(),
    }
    
    # Create a transaction with ZainCash
    order_id = f"course_{course_id}_{request.user.id}_{int(timezone.now().timestamp())}"
    service_type = f"Course: {course.title[:30]}..."  # Limit length
    
    try:
        # Call ZainCash API to create transaction
        result = create_transaction(
            amount=course.price,
            order_id=order_id,
            service_type=service_type,
            redirect_url=redirect_url
        )
        
        if 'id' in result:
            # Store the transaction ID in session
            request.session['payment_info']['transaction_id'] = result['id']
            request.session['payment_info']['order_id'] = order_id
            
            # Redirect to ZainCash payment page
            return redirect(result['payment_url'])
        else:
            # Failed to create transaction
            messages.error(request, f"Failed to initiate payment: {result.get('msg', 'Unknown error')}")
            return redirect('course_detail', course_id=course_id)
    
    except Exception as e:
        messages.error(request, f"Error initiating payment: {str(e)}")
        return redirect('course_detail', course_id=course_id)

@csrf_exempt
def payment_callback(request):
    """
    Handle the callback from ZainCash after payment.
    ZainCash will redirect the user to this URL with a token parameter.
    """
    token = request.GET.get('token')
    
    if not token:
        messages.error(request, "Payment was cancelled or failed.")
        return redirect('profile')  # Redirect to profile or course list
    
    # Decode the token to get transaction status
    transaction_data = decode_redirect_token(token)
    
    # Get payment info from session
    payment_info = request.session.get('payment_info', {})
    course_id = payment_info.get('course_id')
    
    if not course_id:
        messages.error(request, "Payment session expired or invalid.")
        return redirect('profile')
    
    # Check transaction status
    if transaction_data.get('status') == 'success':
        # Verify the transaction matches our records
        if str(transaction_data.get('orderid')) == str(payment_info.get('order_id')):
            # Create enrollment
            try:
                course = Course.objects.get(id=course_id)
                
                # Check if user is already enrolled
                enrollment, created = Enrollment.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={
                        'enrolement_status': 'active'
                    }
                )
                
                if created:
                    # Create progress records
                    create_course_progress(enrollment)
                    messages.success(request, f"You have successfully enrolled in {course.title}!")
                else:
                    messages.info(request, f"You were already enrolled in {course.title}.")
                
                # Clear payment info from session
                if 'payment_info' in request.session:
                    del request.session['payment_info']
                
                return redirect('course_detail', course_id=course_id)
            
            except Course.DoesNotExist:
                messages.error(request, "Course not found.")
                return redirect('profile')
        else:
            messages.error(request, "Order ID mismatch. Payment verification failed.")
    elif transaction_data.get('status') == 'failed':
        messages.error(request, f"Payment failed: {transaction_data.get('msg', 'Unknown error')}")
    elif transaction_data.get('status') == 'pending':
        messages.warning(request, "Payment is pending. We'll notify you when it's completed.")
    else:
        messages.error(request, "Payment status unknown.")
    
    # Clear payment info from session
    if 'payment_info' in request.session:
        del request.session['payment_info']
    
    return redirect('profile')

def check_transaction_status(request, transaction_id):
    """
    Manually check the status of a transaction.
    This can be useful for pending transactions.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'})
    
    try:
        # Verify transaction
        result = verify_transaction(transaction_id)
        
        if result.get('status') == 'success':
            # Process successful payment
            # This logic should be similar to the success case in payment_callback
            pass
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# In subscribtion/views.py

def mark_topic_as_completed(request, topic_id):
    """
    This is the FINAL, DEFINITIVE version of the function. It fixes the critical bug
    where the course would show 100% but not be marked as 'completed' in the database,
    and also fixes the optional content lockout.
    """
    # Self-contained imports to prevent NameErrors
    from utils import create_course_progress
    from courses.models import Topic, Section, Course
    from .models import Enrollment, CourseProgress, SectionProgress, TopicProgress
    from django.contrib import messages
    from django.utils import timezone

    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('course_list')
    
    topic = get_object_or_404(Topic, id=topic_id)
    section = topic.section
    course = section.course
    
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('course_detail', course_id=course.id)
    
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
        section_progress = SectionProgress.objects.get(course_progress=course_progress, section=section)
        topic_progress, created = TopicProgress.objects.get_or_create(section_progress=section_progress, topic=topic)
    except (CourseProgress.DoesNotExist, SectionProgress.DoesNotExist):
        create_course_progress(enrollment)
        return redirect('study_course', course_id=course.id)
    
    # This check has been moved down to allow marking optional topics as complete
    # after the main course is finished.
    if course.course_type == 'locked' and not topic_progress.is_active and not enrollment.completed_at:
        messages.error(request, "You must complete previous topics first.")
        return redirect('study_course', course_id=course.id)
    
    if not topic_progress.completed:
        topic_progress.completed = True
        topic_progress.save()
        messages.success(request, f"Topic '{topic.title}' marked as completed!")
    
    # --- UNIFIED COMPLETION LOGIC ---
    
    # Step 1: Check for SECTION completion
    section_completed = False
    required_topics = Topic.objects.filter(section=section, is_required=True)
    if required_topics.exists():
        completed_required_count = TopicProgress.objects.filter(section_progress=section_progress, topic__in=required_topics, completed=True).count()
        if completed_required_count >= required_topics.count():
            section_completed = True
    else:
        all_topics_count = Topic.objects.filter(section=section).count()
        completed_count = TopicProgress.objects.filter(section_progress=section_progress, completed=True).count()
        if all_topics_count > 0 and completed_count >= all_topics_count:
            section_completed = True
            
    if section_completed != section_progress.completed:
        section_progress.completed = section_completed
        section_progress.save()
    
    # Step 2: Check for COURSE completion
    course_completed = False
    required_sections = Section.objects.filter(course=course, is_required=True)
    if required_sections.exists():
        completed_required_sections_count = SectionProgress.objects.filter(course_progress=course_progress, section__in=required_sections, completed=True).count()
        if completed_required_sections_count >= required_sections.count():
            course_completed = True
    else:
        all_sections_count = Section.objects.filter(course=course).count()
        completed_sections_count = SectionProgress.objects.filter(course_progress=course_progress, completed=True).count()
        if all_sections_count > 0 and completed_sections_count >= all_sections_count:
            course_completed = True
            
    # --- START OF THE CRITICAL FIX ---
    # The logic is now unified into a single if/else block to prevent contradictions.
    
    if course_completed:
        # If the course is now complete, FORCE the state to 100% and done.
        # This block is the single source of truth for a completed course.
        course_progress.completed = True
        course_progress.progress_percentage = 100
        
        # Only update timestamp and show the "Congratulations" message ONCE.
        if not enrollment.completed_at:
            enrollment.completed_at = timezone.now()
            enrollment.save()
            messages.success(request, f"Congratulations! You have completed the course '{course.title}'!")
    else:
        # If the course is NOT yet complete, ensure the 'completed' flag is False
        # and calculate the real percentage based on required topics.
        course_progress.completed = False
        all_required_topics = Topic.objects.filter(section__course=course, is_required=True)
        if all_required_topics.exists():
            total_count = all_required_topics.count()
            completed_count = TopicProgress.objects.filter(section_progress__course_progress=course_progress, topic__in=all_required_topics, completed=True).count()
        else:
            total_count = Topic.objects.filter(section__course=course).count()
            completed_count = TopicProgress.objects.filter(section_progress__course_progress=course_progress, completed=True).count()
        course_progress.progress_percentage = (completed_count / total_count) * 100 if total_count > 0 else 0
    
    # Save the final, correct state of the course progress record.
    course_progress.save()
    
    # --- END OF THE CRITICAL FIX ---
    
    # Step 4: Activate next content (for LOCKED courses)
    if course.course_type == 'locked' and not enrollment.completed_at:
        # This logic now only runs if the course isn't finished,
        # preventing it from trying to activate content after completion.
        if section_completed:
            next_section = Section.objects.filter(course=course, created_at__gt=section.created_at).order_by('created_at').first()
            if next_section:
                next_sp, created = SectionProgress.objects.get_or_create(course_progress=course_progress, section=next_section)
                if not next_sp.is_active:
                    next_sp.is_active = True
                    next_sp.save()
                first_topic = Topic.objects.filter(section=next_section).order_by('created_at').first()
                if first_topic:
                    first_tp, created = TopicProgress.objects.get_or_create(section_progress=next_sp, topic=first_topic)
                    if not first_tp.is_active:
                        first_tp.is_active = True
                        first_tp.save()
        else:
            next_topic = Topic.objects.filter(section=section, created_at__gt=topic.created_at).order_by('created_at').first()
            if next_topic:
                next_tp, created = TopicProgress.objects.get_or_create(section_progress=section_progress, topic=next_topic)
                if not next_tp.is_active:
                    next_tp.is_active = True
                    next_tp.save()

    # Step 5: FINAL, UNCONDITIONAL REDIRECTION
    # After all logic is done, ALWAYS return to the main study page.
    return redirect('study_course', course_id=course.id)








from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
import logging

from courses.models import Topic, Section
from subscribtion.models import Enrollment, CourseProgress, SectionProgress, TopicProgress

# Set up logging
logger = logging.getLogger(__name__)

@login_required
def mark_topic_as_completed_debug(request, topic_id):
    """
    Super simplified debug version to help identify issues
    """
    # Start logging information
    debug_info = []
    debug_info.append(f"Starting debug function with topic_id={topic_id}")
    
    # 1. Get the topic, section, and course
    try:
        topic = Topic.objects.get(id=topic_id)
        debug_info.append(f"Found topic: {topic.title} (id={topic.id})")
        
        section = topic.section
        debug_info.append(f"Topic belongs to section: {section.title} (id={section.id})")
        
        course = section.course
        debug_info.append(f"Section belongs to course: {course.title} (id={course.id})")
    except Exception as e:
        debug_info.append(f"ERROR: Failed to get topic info: {str(e)}")
        return HttpResponse("<br>".join(debug_info))
    
    # 2. Check if user is enrolled
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
        debug_info.append(f"User is enrolled in course (enrollment id={enrollment.id})")
    except Enrollment.DoesNotExist:
        debug_info.append("ERROR: User is not enrolled in this course")
        return HttpResponse("<br>".join(debug_info))
    
    # 3. Get progression records
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
        debug_info.append(f"Found course progress (id={course_progress.id})")
        
        section_progress = SectionProgress.objects.get(
            course_progress=course_progress,
            section=section
        )
        debug_info.append(f"Found section progress (id={section_progress.id}, completed={section_progress.completed})")
        
        topic_progress = TopicProgress.objects.get(
            section_progress=section_progress,
            topic=topic
        )
        debug_info.append(f"Found topic progress (id={topic_progress.id}, completed={topic_progress.completed}, is_active={topic_progress.is_active})")
    except Exception as e:
        debug_info.append(f"ERROR in getting progress records: {str(e)}")
        return HttpResponse("<br>".join(debug_info))
    
    # 4. Mark topic as completed
    if not topic_progress.completed:
        topic_progress.completed = True
        topic_progress.save()
        debug_info.append(f"Marked topic as completed")
    else:
        debug_info.append(f"Topic was already marked as completed")
    
    # 5. Check if all topics in section are completed
    try:
        # Get all topics in section
        section_topics = Topic.objects.filter(section=section)
        debug_info.append(f"Section has {section_topics.count()} total topics")
        
        # Get completed topics in section
        section_completed_topics = TopicProgress.objects.filter(
            section_progress=section_progress,
            completed=True
        )
        debug_info.append(f"User has completed {section_completed_topics.count()} topics in this section")
        
        # Check if section is completed
        section_completed = (section_completed_topics.count() == section_topics.count())
        debug_info.append(f"Is section completed? {section_completed}")
    except Exception as e:
        debug_info.append(f"ERROR checking section completion: {str(e)}")
        return HttpResponse("<br>".join(debug_info))
    
    # 6. If section is completed, activate next section
    if section_completed and not section_progress.completed:
        try:
            # Mark current section as completed
            section_progress.completed = True
            section_progress.save()
            debug_info.append(f"Marked section as completed")
            
            # Find next section
            next_section = Section.objects.filter(
                course=course,
                created_at__gt=section.created_at
            ).order_by('created_at').first()
            
            if next_section:
                debug_info.append(f"Found next section: {next_section.title} (id={next_section.id})")
                
                # Activate next section
                next_section_progress, created = SectionProgress.objects.get_or_create(
                    course_progress=course_progress,
                    section=next_section,
                    defaults={
                        'progress_percentage': 0.0,
                        'completed': False,
                        'is_active': True
                    }
                )
                
                if created:
                    debug_info.append(f"Created new section progress record (id={next_section_progress.id})")
                else:
                    next_section_progress.is_active = True
                    next_section_progress.save()
                    debug_info.append(f"Updated existing section progress record (id={next_section_progress.id})")
                
                # Activate first topic in next section
                first_topic = Topic.objects.filter(section=next_section).order_by('created_at').first()
                if first_topic:
                    debug_info.append(f"Found first topic in next section: {first_topic.title} (id={first_topic.id})")
                    
                    first_topic_progress, created = TopicProgress.objects.get_or_create(
                        section_progress=next_section_progress,
                        topic=first_topic,
                        defaults={
                            'completed': False,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        debug_info.append(f"Created new topic progress record (id={first_topic_progress.id})")
                    else:
                        first_topic_progress.is_active = True
                        first_topic_progress.save()
                        debug_info.append(f"Updated existing topic progress record (id={first_topic_progress.id})")
                else:
                    debug_info.append("ERROR: Could not find first topic in next section")
            else:
                debug_info.append("No next section found - this was the last section")
        except Exception as e:
            debug_info.append(f"ERROR activating next section: {str(e)}")
            return HttpResponse("<br>".join(debug_info))
    
    # Return all debug info as a simple HTML response
    return HttpResponse("<br>".join(debug_info))

# free enrollemnt :--------
@login_required
def enroll_free_course(request, course_id):
    """
    Handle enrollment for free courses without payment gateway.
    Directly enrolls the user if the course price is 0.
    """
    # Get the course
    course = get_object_or_404(Course, id=course_id)
    
    # Verify the course is actually free
    if course.price > 0:
        messages.error(request, "This course requires payment to enroll.")
        return redirect('course_detail', course_id=course_id)
    
    # Check if user is already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "You are already enrolled in this course.")
        return redirect('course_detail', course_id=course_id)
    
    # Create enrollment for free course
    enrollment = Enrollment.objects.create(
        user=request.user,
        course=course,
        enrolement_status='active'
    )
    
    # Create progress records
    #create_course_progress(enrollment)
    messages.success(request, f"You have successfully enrolled in the free course: {course.title}!")
    
    # Redirect back to course detail
    return redirect('course_detail', course_id=course_id)

@login_required
def debug_video_view(request, topic_id):
    """
    Debug view for testing video completion
    """
    # Get the topic
    topic = get_object_or_404(Topic, id=topic_id)
    section = topic.section
    course = section.course
    
    # Check if user is enrolled
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('course_detail', course_id=course.id)
    
    # Get progression data
    from subscribtion.models import CourseProgress, SectionProgress, TopicProgress
    
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
        section_progress = SectionProgress.objects.get(
            course_progress=course_progress,
            section=section
        )
        topic_progress, created = TopicProgress.objects.get_or_create(
            section_progress=section_progress,
            topic=topic,
            defaults={
                'completed': False,
                'is_active': True
            }
        )
    except Exception as e:
        messages.error(request, f"Error loading progress: {str(e)}")
        return redirect('course_detail', course_id=course.id)
    
    # Render debug template
    context = {
        'topic': topic,
        'section': section,
        'course': course,
        'enrollment': enrollment,
        'topic_progress': topic_progress,
    }
    
    return render(request, 'debug_video.html', context)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse

from courses.models import Topic, Section
from subscribtion.models import Enrollment, CourseProgress, SectionProgress, TopicProgress

@login_required
def super_detailed_debug(request, topic_id):
    """
    Super detailed debug function that focuses on the next section activation logic
    """
    debug_info = []
    debug_info.append(f"STARTING SUPER DETAILED DEBUG FOR TOPIC ID {topic_id}")
    debug_info.append("=" * 80)
    
    # Get the topic, section, and course
    try:
        topic = Topic.objects.get(id=topic_id)
        debug_info.append(f"Found topic: {topic.title} (id={topic.id})")
        
        section = topic.section
        debug_info.append(f"Topic belongs to section: {section.title} (id={section.id})")
        
        course = section.course
        debug_info.append(f"Section belongs to course: {course.title} (id={course.id})")
    except Exception as e:
        debug_info.append(f"ERROR: Failed to get topic info: {str(e)}")
        return HttpResponse("<br>".join(debug_info))
    
    # Check if user is enrolled
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
        debug_info.append(f"User is enrolled in course (enrollment id={enrollment.id})")
    except Enrollment.DoesNotExist:
        debug_info.append("ERROR: User is not enrolled in this course")
        return HttpResponse("<br>".join(debug_info))
    
    # Get progression records
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
        debug_info.append(f"Found course progress (id={course_progress.id})")
        
        section_progress = SectionProgress.objects.get(
            course_progress=course_progress,
            section=section
        )
        debug_info.append(f"Found section progress (id={section_progress.id}, completed={section_progress.completed}, is_active={section_progress.is_active})")
        
        topic_progress = TopicProgress.objects.get(
            section_progress=section_progress,
            topic=topic
        )
        debug_info.append(f"Found topic progress (id={topic_progress.id}, completed={topic_progress.completed}, is_active={topic_progress.is_active})")
    except Exception as e:
        debug_info.append(f"ERROR in getting progress records: {str(e)}")
        return HttpResponse("<br>".join(debug_info))
    
    # Mark topic as completed if not already
    if not topic_progress.completed:
        topic_progress.completed = True
        topic_progress.save()
        debug_info.append(f"Marked topic as completed")
    else:
        debug_info.append(f"Topic was already marked as completed")
    
    # Check section completion
    debug_info.append("\nCHECKING SECTION COMPLETION:")
    debug_info.append("-" * 50)
    
    try:
        # Get all topics in section
        section_topics = Topic.objects.filter(section=section)
        debug_info.append(f"Section has {section_topics.count()} total topics:")
        
        # List all topics in the section
        for idx, t in enumerate(section_topics):
            debug_info.append(f"  {idx+1}. Topic: {t.title} (id={t.id})")
        
        # Get completed topics in section
        section_completed_topics = TopicProgress.objects.filter(
            section_progress=section_progress,
            completed=True
        )
        debug_info.append(f"User has completed {section_completed_topics.count()} topics in this section:")
        
        # List all completed topics
        for idx, tp in enumerate(section_completed_topics):
            debug_info.append(f"  {idx+1}. Completed Topic: {tp.topic.title} (id={tp.topic.id})")
        
        # Check if section is completed
        section_completed = (section_completed_topics.count() == section_topics.count())
        debug_info.append(f"Is section completed? {section_completed}")
        
        # Mark section as completed if needed
        debug_info.append(f"Was section already marked as completed in DB? {section_progress.completed}")
        
        section_progress.completed = section_completed
        section_progress.save()
        debug_info.append(f"Updated section completed status to: {section_completed}")
    except Exception as e:
        debug_info.append(f"ERROR checking section completion: {str(e)}")
        return HttpResponse("<br>".join(debug_info))
    
    # NEXT SECTION ACTIVATION
    debug_info.append("\nCHECKING NEXT SECTION ACTIVATION:")
    debug_info.append("-" * 50)
    
    if section_completed:
        try:
            debug_info.append("Section is completed, looking for next section...")
            
            # Find next section
            all_sections = Section.objects.filter(course=course).order_by('created_at')
            debug_info.append(f"Course has {all_sections.count()} total sections:")
            
            # List all sections in the course
            for idx, s in enumerate(all_sections):
                debug_info.append(f"  {idx+1}. Section: {s.title} (id={s.id}, created_at={s.created_at})")
            
            next_section = Section.objects.filter(
                course=course,
                created_at__gt=section.created_at
            ).order_by('created_at').first()
            
            if next_section:
                debug_info.append(f"Found next section: {next_section.title} (id={next_section.id})")
                
                # Check if next section is already active
                try:
                    existing_next_section_progress = SectionProgress.objects.get(
                        course_progress=course_progress,
                        section=next_section
                    )
                    debug_info.append(f"Next section already has progress record (id={existing_next_section_progress.id}, is_active={existing_next_section_progress.is_active}, completed={existing_next_section_progress.completed})")
                    
                    # Update the next section progress to be active
                    existing_next_section_progress.is_active = True
                    existing_next_section_progress.save()
                    debug_info.append(f"Updated next section progress to be active")
                    
                except SectionProgress.DoesNotExist:
                    debug_info.append(f"No existing progress record for next section, creating new one...")
                    
                    # Create new section progress for next section
                    next_section_progress = SectionProgress.objects.create(
                        course_progress=course_progress,
                        section=next_section,
                        progress_percentage=0.0,
                        completed=False,
                        is_active=True
                    )
                    debug_info.append(f"Created new section progress record (id={next_section_progress.id})")
                
                # Reload to confirm
                next_section_progress = SectionProgress.objects.get(
                    course_progress=course_progress,
                    section=next_section
                )
                debug_info.append(f"Confirmed next section progress: is_active={next_section_progress.is_active}")
                
                # Now activate first topic in next section
                debug_info.append("\nACTIVATING FIRST TOPIC IN NEXT SECTION:")
                debug_info.append("-" * 50)
                
                # Find the first topic in the next section
                first_topics = Topic.objects.filter(section=next_section).order_by('created_at')
                
                if first_topics.exists():
                    first_topic = first_topics.first()
                    debug_info.append(f"Found first topic in next section: {first_topic.title} (id={first_topic.id})")
                    
                    # Check if this topic already has a progress record
                    try:
                        existing_topic_progress = TopicProgress.objects.get(
                            section_progress=next_section_progress,
                            topic=first_topic
                        )
                        debug_info.append(f"First topic already has progress record (id={existing_topic_progress.id}, is_active={existing_topic_progress.is_active}, completed={existing_topic_progress.completed})")
                        
                        # Update the topic progress to be active
                        existing_topic_progress.is_active = True
                        existing_topic_progress.save()
                        debug_info.append(f"Updated first topic progress to be active")
                        
                    except TopicProgress.DoesNotExist:
                        debug_info.append(f"No existing progress record for first topic, creating new one...")
                        
                        # Create new topic progress
                        first_topic_progress = TopicProgress.objects.create(
                            section_progress=next_section_progress,
                            topic=first_topic,
                            completed=False,
                            is_active=True
                        )
                        debug_info.append(f"Created new topic progress record (id={first_topic_progress.id})")
                    
                    # Reload to confirm
                    first_topic_progress = TopicProgress.objects.get(
                        section_progress=next_section_progress,
                        topic=first_topic
                    )
                    debug_info.append(f"Confirmed first topic progress: is_active={first_topic_progress.is_active}")
                    
                else:
                    debug_info.append("ERROR: No topics found in the next section!")
            else:
                debug_info.append("No next section found - this might be the last section")
                
                # List all sections with their sequence
                debug_info.append("Listing all sections by created_at to verify:")
                all_sections = Section.objects.filter(course=course).order_by('created_at')
                for idx, s in enumerate(all_sections):
                    debug_info.append(f"  {idx+1}. Section: {s.title} (id={s.id}, created_at={s.created_at})")
                
                current_section_index = list(s.id for s in all_sections).index(section.id)
                debug_info.append(f"Current section index: {current_section_index} of {all_sections.count()-1}")
        except Exception as e:
            debug_info.append(f"ERROR in next section activation: {str(e)}")
            import traceback
            debug_info.append(traceback.format_exc())
    else:
        debug_info.append("Section is NOT completed, no need to activate next section")
    
    # Return all debug info as a simple HTML response
    return HttpResponse("<br>".join(debug_info))










# certificate generation
# Add these imports to subscribtion/views.py

import os
from django.conf import settings
from .models import Certificate
import os
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

# Import these for PDF generation
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image

@login_required
def generate_certificate(request, course_id):
    """Generate a certificate for a completed course"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('study_course', course_id=course_id)
    
    # Get the course
    course = get_object_or_404(Course, id=course_id)
    
    # Verify user is enrolled
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('course_detail', course_id=course_id)
    
    # Verify course completion
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
        
        # Calculate completion percentage
        total_topics = Topic.objects.filter(section__course=course).count()
        if total_topics == 0:
            messages.error(request, "This course has no topics to complete.")
            return redirect('study_course', course_id=course_id)
        
        completed_topics = TopicProgress.objects.filter(
            section_progress__course_progress=course_progress,
            completed=True
        ).count()
        
        completion_percentage = (completed_topics / total_topics) * 100
        
        # Check if all topics are completed
        if completion_percentage < 100 and not course_progress.completed:
            messages.error(request, "You must complete all topics before receiving a certificate.")
            return redirect('study_course', course_id=course_id)
        
    except CourseProgress.DoesNotExist:
        messages.error(request, "No progress record found for this course.")
        return redirect('study_course', course_id=course_id)
    
    # Check if a certificate already exists
    try:
        certificate = Certificate.objects.get(enrollment=enrollment)
        messages.info(request, "You already have a certificate for this course.")
        return redirect('view_certificate', certificate_id=certificate.certificate_id)
    except Certificate.DoesNotExist:
        # Create a new certificate
        certificate = Certificate(enrollment=enrollment)
        certificate.save()
        
        # Generate the PDF certificate
        certificate_path = os.path.join(settings.MEDIA_ROOT, 'certificates', f'{certificate.certificate_id}.pdf')
        os.makedirs(os.path.dirname(certificate_path), exist_ok=True)
        
        # Create the certificate PDF
        create_certificate_pdf(certificate, certificate_path)
        
        # Save the file path to the certificate
        certificate.pdf_file = f'certificates/{certificate.certificate_id}.pdf'
        certificate.save()
        
        # Update enrollment status - don't unenroll but mark as completed
        enrollment.completed_at = timezone.now()
        enrollment.save()
        
        # Mark course progress as completed
        course_progress.completed = True
        course_progress.progress_percentage = 100
        course_progress.save()
        
        messages.success(request, f"Congratulations! Your certificate for {course.title} has been generated.")

        return redirect('view_certificate', certificate_id=certificate.certificate_id)

@login_required
def view_certificate(request, certificate_id):
    """View a certificate"""
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)
    
    # Security check - make sure the certificate belongs to the user
    if certificate.user != request.user:
        messages.error(request, "You are not authorized to view this certificate.")
        return redirect('profile')
    
    context = {
        'certificate': certificate,
        'course': certificate.course,
        'issue_date': certificate.issued_on,
    }
    
    return render(request, 'certificate_view.html', context)



@login_required
def download_certificate(request, certificate_id):
    """
    Allow downloading of certificates with proper security checks
    This is the ONLY content users are allowed to download
    """
    # Get the certificate
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)
    
    # Check if user is the certificate owner or staff
    if certificate.user.id != request.user.id and not request.user.is_staff:
        return HttpResponse('Unauthorized', status=403)
    
    # Serve the certificate file
    if certificate.pdf_file:
        # Open the file in binary mode
        try:
            response = FileResponse(
                open(certificate.pdf_file.path, 'rb'),
                content_type='application/pdf'
            )
            
            # Set to attachment (forces download)
            filename = os.path.basename(certificate.pdf_file.name)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Include headers for caching and for ensuring it's downloadable
            response['Cache-Control'] = 'no-cache'
            
            return response
        except FileNotFoundError:
            return HttpResponse('Certificate file not found', status=404)
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}', status=500)
    
    return HttpResponse('Certificate file not found', status=404)

def create_certificate_pdf(certificate, output_path):
    """Create a PDF certificate for the user"""
    # Get data for the certificate
    user = certificate.user
    course = certificate.course
    issue_date = certificate.issued_on.strftime("%B %d, %Y")
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CertificateTitle',
        fontName='Helvetica-Bold',
        fontSize=24,
        alignment=1,  # center aligned
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='CertificateSubtitle',
        fontName='Helvetica',
        fontSize=18,
        alignment=1,
        spaceAfter=30
    ))
    styles.add(ParagraphStyle(
        name='CertificateName',
        fontName='Helvetica-Bold',
        fontSize=22,
        alignment=1,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='CertificateText',
        fontName='Helvetica',
        fontSize=16,
        alignment=1,
        leading=20
    ))
    styles.add(ParagraphStyle(
        name='CertificateFooter',
        fontName='Helvetica',
        fontSize=12,
        alignment=1,
        textColor=colors.gray
    ))
    
    # Create the content
    content = []
    
    # Logo placeholder (you would replace this with your actual logo)
    # logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo.png')
    # if os.path.exists(logo_path):
    #     logo = Image(logo_path, width=2*inch, height=1*inch)
    #     content.append(logo)
    
    # Add a spacer
    content.append(Spacer(1, 0.5*inch))
    
    # Certificate title
    title = Paragraph("Certificate of Completion", styles['CertificateTitle'])
    content.append(title)
    
    # Add a spacer
    content.append(Spacer(1, 0.25*inch))
    
    # Subtitle
    subtitle = Paragraph("This is to certify that", styles['CertificateSubtitle'])
    content.append(subtitle)
    
    # Student name
    student_name = user.get_full_name() if user.get_full_name() else user.username
    name = Paragraph(student_name, styles['CertificateName'])
    content.append(name)
    
    # Certificate text
    cert_text = Paragraph(
        f"has successfully completed the course<br/>"
        f"<b>{course.title}</b>",
        styles['CertificateText']
    )
    content.append(cert_text)
    
    # Add a spacer
    content.append(Spacer(1, 0.5*inch))
    
    # Date and signature
    date_text = Paragraph(f"Issued on: {issue_date}", styles['CertificateText'])
    content.append(date_text)
    
    # Add a spacer
    content.append(Spacer(1, 0.25*inch))
    
    # Signature line
    content.append(Paragraph("_______________________", styles['CertificateText']))
    content.append(Paragraph("Course Instructor", styles['CertificateText']))
    
    # Add a spacer
    content.append(Spacer(1, 0.5*inch))
    
    # Certificate ID
    cert_id = Paragraph(f"Certificate ID: {certificate.certificate_id}", styles['CertificateFooter'])
    content.append(cert_id)
    
    # Build the PDF document
    doc.build(content)