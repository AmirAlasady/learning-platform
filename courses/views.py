# views.py
from pyexpat.errors import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from accounts.models import *
from .models import *
from subscribtion.models import *
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import Course, Chategory, Section, Topic
from subscribtion.models import Enrollment, CourseProgress, SectionProgress, TopicProgress
from utils import create_course_progress

# Removed invalid line causing syntax errors
from django.contrib import messages
def index(request): 
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')






def course_list(request):
    """
    View for listing all courses with filtering and search functionality
    """
    # Get all courses initially
    courses = Course.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        courses = courses.filter(category_id=category_id)
    
    # Course type filter
    course_type = request.GET.get('course_type')
    if course_type in [Course.LOCKED, Course.MANAGED, Course.UNLOCKED]:
        courses = courses.filter(course_type=course_type)
    
    # Course level filter
    course_level = request.GET.get('course_level')
    if course_level in [Course.BEGINNER, Course.INTERMEDIATE, Course.ADVANCED, Course.GENERAL]:
        courses = courses.filter(course_level=course_level)
    
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price:
        courses = courses.filter(price__gte=min_price)
    if max_price:
        courses = courses.filter(price__lte=max_price)
    
    # Get all categories for filter dropdown
    categories = Chategory.objects.all()
    
    # Pagination
    paginator = Paginator(courses, 12)  # Show 12 courses per page
    page = request.GET.get('page')
    
    try:
        courses_paginated = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        courses_paginated = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        courses_paginated = paginator.page(paginator.num_pages)
    
    # For logged in users, add enrollment status
    if request.user.is_authenticated:
        enrolled_courses = request.user.enrolled_courses.values_list('course_id', flat=True)
        
        # Add additional data for the template to use
        for course in courses_paginated:
            course.is_enrolled = course.id in enrolled_courses
            
            # If enrolled, get progress information
            if course.is_enrolled:
                enrollment = Enrollment.objects.get(user=request.user, course=course)
                try:
                    course.progress = enrollment.progress.progress_percentage
                    course.completed = enrollment.progress.completed
                except CourseProgress.DoesNotExist:
                    course.progress = 0
                    course.completed = False
                
                course.enrollment_status = enrollment.enrolement_status
    
    context = {
        'courses': courses_paginated,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_course_type': course_type,
        'selected_course_level': course_level,
        'min_price': min_price,
        'max_price': max_price,
        'course_type_choices': Course.COURSE_TYPE_CHOICES,
        'course_level_choices': Course.COURSE_LEVEL_CHOICES,
    }
    
    return render(request, 'course_list.html', context)

# Update the course_detail view in courses/views.py to include related courses and reviews

def course_detail(request, course_id):
    """
    View for showing detailed information about a specific course
    Enhanced with related courses and reviews
    """
    course = get_object_or_404(Course, id=course_id)
    sections = Section.objects.filter(course=course).order_by('created_at')
    
    # Get total topics count
    total_topics_count = Topic.objects.filter(section__course=course).count()
    
    # Calculate the current deadline status if applicable
    deadline_passed = False
    days_remaining = None
    
    if course.deadline:
        now = timezone.now()
        if now > course.deadline:
            deadline_passed = True
        else:
            # Calculate days remaining
            time_diff = course.deadline - now
            days_remaining = time_diff.days
    
    # Get related courses (same category)
    related_courses = Course.objects.filter(
        category=course.category
    ).exclude(id=course.id).order_by('-created_at')[:4]
    
    # Get course reviews
    reviews = Review.objects.filter(course=course)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews else None
    
    # Pre-calculate counts for each rating level (1-5)
    star_counts = {}
    for i in range(1, 6):
        star_counts[i] = reviews.filter(rating=i).count()
    
    # Prepare context
    context = {
        'course': course,
        'sections': sections,
        'total_topics_count': total_topics_count,
        'deadline_passed': deadline_passed,
        'days_remaining': days_remaining,
        'is_enrolled': False,  # Default to not enrolled
        'related_courses': related_courses,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'star_counts': star_counts,
        'total_reviews': reviews.count(),
        'can_review': False,  # Default
    }
    
    # If user is authenticated, check enrollment information
    if request.user.is_authenticated:
        try:
            enrollment = Enrollment.objects.get(user=request.user, course=course)
            context['enrollment'] = enrollment
            context['is_enrolled'] = True  # User is enrolled
            context['can_review'] = True   # Enrolled users can review
            
            # Check if user has already reviewed this course
            try:
                user_review = Review.objects.get(course=course, user=request.user)
                context['user_review'] = user_review
            except Review.DoesNotExist:
                pass
            
            try:
                course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
                context['course_progress'] = course_progress
                
                # Get progress for each section
                section_progress_dict = {}
                for section_progress in SectionProgress.objects.filter(course_progress=course_progress):
                    section_progress_dict[section_progress.section_id] = {
                        'progress': section_progress.progress_percentage,
                        'completed': section_progress.completed,
                        'last_accessed': section_progress.last_accessed,
                        'is_active': section_progress.is_active
                    }
                context['section_progress'] = section_progress_dict
                
                # Get progress for topics
                topic_progress_dict = {}
                for topic_progress in TopicProgress.objects.filter(
                    section_progress__course_progress=course_progress
                ):
                    topic_progress_dict[topic_progress.topic.id] = {
                        'completed': topic_progress.completed,
                        'last_accessed': topic_progress.last_accessed,
                        'is_active': topic_progress.is_active
                    }
                context['topic_progress'] = topic_progress_dict
                
                completed_topics_count = TopicProgress.objects.filter(
                    section_progress__course_progress=course_progress,
                    completed=True
                ).count()
                
                context['completed_topics_count'] = completed_topics_count
                context['progress_percentage'] = (
                    (completed_topics_count / total_topics_count) * 100 
                    if total_topics_count > 0 else 0
                )
                
            except CourseProgress.DoesNotExist:
                context['course_progress'] = None
                # This shouldn't happen, but if it does, we should create the progress
                
                create_course_progress(enrollment)
                return redirect('course_detail', course_id=course_id)
        
        except Enrollment.DoesNotExist:
            # User is not enrolled in this course
            context['enrollment'] = None
            context['is_enrolled'] = False
    
    # Get the next section if there's progress or default to first section
    if request.user.is_authenticated and context['is_enrolled']:
        if 'course_progress' in context and context['course_progress']:
            # Find the last accessed section
            last_section_progress = SectionProgress.objects.filter(
                course_progress=context['course_progress'],
                is_active=True
            ).order_by('-last_accessed').first()
            
            if last_section_progress:
                if last_section_progress.completed:
                    # If last accessed section is completed, find the next incomplete section
                    next_sections = SectionProgress.objects.filter(
                        course_progress=context['course_progress'],
                        is_active=True,
                        completed=False
                    ).order_by('section__created_at')
                    
                    if next_sections.exists():
                        context['next_section'] = next_sections.first().section
                    else:
                        context['next_section'] = None  # All sections completed
                else:
                    # Continue with the last accessed section
                    context['next_section'] = last_section_progress.section
            else:
                # No progress yet, start with first active section
                first_section_progress = SectionProgress.objects.filter(
                    course_progress=context['course_progress'],
                    is_active=True
                ).order_by('section__created_at').first()
                
                if first_section_progress:
                    context['next_section'] = first_section_progress.section
                else:
                    context['next_section'] = None
    
    return render(request, 'course_detail.html', context)

@login_required
def topic_view(request, topic_id):
    """
    View function for displaying a topic's content and tracking progress.
    """
    # Get the topic
    topic = get_object_or_404(Topic, id=topic_id)
    section = topic.section
    course = section.course
    
    # Check if user is enrolled in the course
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('course_detail', course_id=course.id)
    
    # Get the topic progress
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
        section_progress = SectionProgress.objects.get(course_progress=course_progress, section=section)
        topic_progress, created = TopicProgress.objects.get_or_create(
            section_progress=section_progress,
            topic=topic,
            defaults={
                'completed': False,
                'is_active': True
            }
        )
    except (CourseProgress.DoesNotExist, SectionProgress.DoesNotExist):
        messages.error(request, "Error loading progress information. Please contact support.")
        return redirect('course_detail', course_id=course.id)
    
    # Check if the topic is active/accessible
    if not topic_progress.is_active and course.course_type == Course.LOCKED:
        messages.error(request, "This topic is not yet available. Please complete previous topics first.")
        return redirect('course_detail', course_id=course.id)
    
    # Update last accessed timestamp
    topic_progress.save()  # This updates the last_accessed field via auto_now
    
    # Get next and previous topics for navigation
    prev_topic = Topic.objects.filter(
        section=section,
        created_at__lt=topic.created_at
    ).order_by('-created_at').first()
    
    next_topic = Topic.objects.filter(
        section=section,
        created_at__gt=topic.created_at
    ).order_by('created_at').first()
    
    # If no next topic in this section, check next section
    if not next_topic:
        next_section = Section.objects.filter(
            course=course,
            created_at__gt=section.created_at
        ).order_by('created_at').first()
        
        if next_section:
            next_topic = Topic.objects.filter(section=next_section).order_by('created_at').first()
    
    # Prepare context
    context = {
        'topic': topic,
        'section': section,
        'course': course,
        'enrollment': enrollment,
        'topic_progress': topic_progress,
        'prev_topic': prev_topic,
        'next_topic': next_topic,
    }
    
    # Return appropriate template based on content type
    if topic.content_type == 'video':
        return render(request, 'topic_video.html', context)
    elif topic.content_type == 'article':
        return render(request, 'topic_article.html', context)
    elif topic.content_type == 'quiz':
        return render(request, 'quiz/take_quiz.html', context)
    else:
        # Fallback template
        return render(request, 'topic_default.html', context)



@login_required
def study(request, course_id):
    """
    Main view for studying a course with hierarchical navigation 
    and content display.
    """
    # Get the course
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is enrolled
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
        if enrollment.completed_at:
            messages.info(request, "You have already completed this course.")
    except Enrollment.DoesNotExist:
        messages.error(request, "You need to enroll in this course first.")
        return redirect('course_detail', course_id=course_id)
    
    # Get course progress
    try:
        course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
    except CourseProgress.DoesNotExist:
        # Create progress if it doesn't exist
        course_progress = create_course_progress(enrollment)
    
    # Get all sections with progress info
    sections = Section.objects.filter(course=course).order_by('created_at')
    
    # Get section progress data
    section_progress_dict = {}
    for section_progress in SectionProgress.objects.filter(course_progress=course_progress):
        section_progress_dict[section_progress.section_id] = {
            'id': section_progress.id,
            'progress': section_progress.progress_percentage,
            'completed': section_progress.completed,
            'is_active': section_progress.is_active,
            'last_accessed': section_progress.last_accessed
        }
    
    # Get topic progress data
    topic_progress_dict = {}
    for topic_progress in TopicProgress.objects.filter(
        section_progress__course_progress=course_progress
    ):
        topic_progress_dict[topic_progress.topic_id] = {
            'id': topic_progress.id,
            'completed': topic_progress.completed,
            'is_active': topic_progress.is_active,
            'last_accessed': topic_progress.last_accessed
        }
    
    # Get the requested topic ID from the query string (if provided)
    requested_topic_id = request.GET.get('topic_id')
    active_topic = None
    
    if requested_topic_id:
        try:
            topic = Topic.objects.get(id=requested_topic_id)
            # Check if topic belongs to this course
            if topic.section.course.id != course.id:
                messages.error(request, "Invalid topic requested.")
                requested_topic_id = None
            else:
                # Check if topic is active for this user
                if (topic.id in topic_progress_dict and 
                    (topic_progress_dict[topic.id]['is_active'] or 
                     course.course_type == Course.UNLOCKED)):
                    active_topic = topic
                else:
                    messages.error(request, "This topic is not yet available. Complete the previous topics first.")
        except Topic.DoesNotExist:
            messages.error(request, "Topic not found.")
            requested_topic_id = None
    
    # If no valid topic is requested, find the first active topic
    if not active_topic:
        for section in sections:
            if section.id in section_progress_dict and section_progress_dict[section.id]['is_active']:
                for topic in section.topics.all().order_by('created_at'):
                    if topic.id in topic_progress_dict and topic_progress_dict[topic.id]['is_active']:
                        active_topic = topic
                        break
                if active_topic:
                    break
    
    # Update last accessed timestamp for the active topic
    if active_topic and active_topic.id in topic_progress_dict:
        topic_progress = TopicProgress.objects.get(id=topic_progress_dict[active_topic.id]['id'])
        topic_progress.save()  # This will update the last_accessed field via auto_now
    
    # Check if the active topic has a quiz
    has_quiz = False
    quiz = None
    if active_topic:
        try:
            quiz = Quiz.objects.get(topic=active_topic)
            has_quiz = True
        except Quiz.DoesNotExist:
            pass
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'sections': sections,
        'section_progress': section_progress_dict,
        'topic_progress': topic_progress_dict,
        'active_topic': active_topic,
        'course_progress': course_progress,
        'has_quiz': has_quiz,
        'quiz': quiz
    }
    
    return render(request, 'study.html', context)






from django.views.decorators.http import require_GET, require_POST
from utils import activate_next_topic
@login_required
@require_POST
def clear_quiz_redirect(request):
    """Clear the quiz redirect URL from session"""
    if 'quiz_redirect_url' in request.session:
        del request.session['quiz_redirect_url']
    return JsonResponse({'status': 'success'})

# quiz data
@login_required
def start_quiz(request, quiz_id):
    """Initialize a new quiz attempt for the user"""
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    
    # Check if the quiz has any questions
    if quiz.questions.count() == 0:
        messages.error(request, "This quiz doesn't have any questions yet. Please try again later.")
        # Redirect back to the topic or course
        if hasattr(quiz, 'topic') and quiz.topic:
            return redirect('topic_view', topic_id=quiz.topic.id)
        return redirect('course_list')  # Fallback if no topic is associated
    
    # Check if user has attempts remaining
    previous_attempts = QuizAttempt.objects.filter(user=request.user, quiz=quiz)
    if previous_attempts.count() >= quiz.attempts_allowed:
        last_attempt = previous_attempts.order_by('-started_at').first()
        
        # Store redirection info in session if we came from study page
        study_url = request.GET.get('study_url')
        if study_url:
            request.session['quiz_redirect_url'] = study_url
            
        return render(request, 'quiz/no_attempts_remaining.html', {
            'quiz': quiz,
            'last_attempt': last_attempt,
            'study_url': study_url
        })
    
    # Create a new quiz attempt
    quiz_attempt = QuizAttempt(
        user=request.user,
        quiz=quiz,
        started_at=timezone.now()
    )
    quiz_attempt.save()
    
    # Store redirection info in session if we came from study page
    study_url = request.GET.get('study_url')
    if study_url:
        request.session['quiz_redirect_url'] = study_url
    
    # Redirect to the first question
    return redirect('take_quiz', attempt_id=quiz_attempt.id, question_index=0)
@login_required
def take_quiz(request, attempt_id, question_index=0):
    """Handle the quiz-taking process with two-way navigation"""
    quiz_attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    quiz = quiz_attempt.quiz
    
    # Convert question_index to integer if it's a string
    try:
        question_index = int(question_index)
    except ValueError:
        question_index = 0
    
    # If already completed, show results
    if quiz_attempt.completed_at:
        return redirect('quiz_results', attempt_id=attempt_id)
    
    # Check for time expiration if quiz has duration limit
    if quiz.duration_minutes:
        elapsed_time = timezone.now() - quiz_attempt.started_at
        elapsed_minutes = elapsed_time.total_seconds() / 60
        if elapsed_minutes > quiz.duration_minutes:
            # Time's up - mark as completed
            quiz_attempt.completed_at = timezone.now()
            quiz_attempt.calculate_score()
            quiz_attempt.save()
            return redirect('quiz_results', attempt_id=attempt_id)
    
    # Get questions for this quiz
    questions = list(quiz.questions.all())
    total_questions = len(questions)
    
    # Check if the quiz has any questions
    if total_questions == 0:
        # No questions in the quiz - mark as completed with score 0
        quiz_attempt.completed_at = timezone.now()
        quiz_attempt.score = 0
        quiz_attempt.is_passed = False
        quiz_attempt.save()
        messages.warning(request, "This quiz doesn't have any questions.")
        return redirect('quiz_results', attempt_id=attempt_id)
    
    # Validate question index
    if question_index < 0:
        question_index = 0
    elif question_index >= total_questions:
        question_index = total_questions - 1
    
    # Get the current question
    current_question = questions[question_index]
    
    # Handle answer submission
    if request.method == 'POST':
        # Get the submitted answer
        answer_id = request.POST.get('answer')
        
        # Get navigation direction
        action = request.POST.get('action', 'next')
        
        # Save answer if provided
        if answer_id:
            answer = get_object_or_404(Answer, id=answer_id, question=current_question)
            
            # Update or create the selected answer
            SelectedAnswer.objects.update_or_create(
                quiz_attempt=quiz_attempt, 
                question=current_question,
                defaults={'answer': answer}
            )
        
        # Determine next question index based on action
        if action == 'prev' and question_index > 0:
            return redirect('take_quiz', attempt_id=attempt_id, question_index=question_index-1)
        elif action == 'next' and question_index < total_questions - 1:
            return redirect('take_quiz', attempt_id=attempt_id, question_index=question_index+1)
        elif action == 'complete':
            # Check if all questions have answers
            answered_questions = quiz_attempt.selected_answers.count()
            if answered_questions == total_questions:
                quiz_attempt.completed_at = timezone.now()
                quiz_attempt.calculate_score()
                quiz_attempt.save()
                return redirect('quiz_results', attempt_id=attempt_id)
            else:
                # Find the first unanswered question
                answered_question_ids = quiz_attempt.selected_answers.values_list('question_id', flat=True)
                for idx, q in enumerate(questions):
                    if q.id not in answered_question_ids:
                        return redirect('take_quiz', attempt_id=attempt_id, question_index=idx)
    
    # Get previously selected answer for this question (if any)
    selected_answer = quiz_attempt.selected_answers.filter(question=current_question).first()
    
    # Get all answered questions to track progress
    answered_question_ids = set(quiz_attempt.selected_answers.values_list('question_id', flat=True))
    
    # Prepare context for template
    context = {
        'quiz': quiz,
        'quiz_attempt': quiz_attempt,
        'question': current_question,
        'answers': current_question.answers.all(),
        'selected_answer': selected_answer.answer if selected_answer else None,
        'progress': {
            'current_index': question_index,
            'answered': len(answered_question_ids),
            'total': total_questions,
            'is_first': question_index == 0,
            'is_last': question_index == total_questions - 1,
            'answered_all': len(answered_question_ids) == total_questions,
            'question_statuses': [{'index': idx, 'question': q, 'answered': q.id in answered_question_ids} 
                                 for idx, q in enumerate(questions)]
        }
    }
    
    # Add remaining time if duration is set
    if quiz.duration_minutes:
        elapsed_seconds = (timezone.now() - quiz_attempt.started_at).total_seconds()
        remaining_seconds = max(0, (quiz.duration_minutes * 60) - elapsed_seconds)
        context['remaining_seconds'] = remaining_seconds
    
    return render(request, 'quiz/take_quiz.html', context)



@login_required
def quiz_results(request, attempt_id):
    """Display quiz results after completion and update topic progress if quiz is passed"""
    quiz_attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    quiz = quiz_attempt.quiz
    
    # Get details about answers for display
    question_data = []
    for question in quiz.questions.all():
        selected = quiz_attempt.selected_answers.filter(question=question).first()
        question_data.append({
            'question': question,
            'selected_answer': selected.answer if selected else None,
            'is_correct': selected.answer.is_correct if selected else False,
            'correct_answer': question.answers.filter(is_correct=True).first()
        })
    
    # Get topic associated with this quiz
    if hasattr(quiz, 'topic') and quiz.topic:
        topic = quiz.topic
        
        # Only mark topic as completed if the quiz is passed
        if quiz_attempt.is_passed:
            # Find the user's topic progress
            try:
                # Get enrollment, course_progress, section_progress
                enrollment = Enrollment.objects.get(user=request.user, course=topic.section.course)
                course_progress = CourseProgress.objects.get(enrollment_model=enrollment)
                section_progress = SectionProgress.objects.get(course_progress=course_progress, section=topic.section)
                topic_progress = TopicProgress.objects.get(section_progress=section_progress, topic=topic)
                
                # Mark topic as completed if the quiz is passed
                if not topic_progress.completed:
                    topic_progress.completed = True
                    topic_progress.save()
                    messages.success(request, f"Congratulations! You passed the quiz and completed the topic '{topic.title}'.")
                    
                    # Activate next topic if applicable
                    activate_next_topic(topic_progress)
            except (Enrollment.DoesNotExist, CourseProgress.DoesNotExist, 
                   SectionProgress.DoesNotExist, TopicProgress.DoesNotExist):
                # Handle cases where progress tracking records are missing
                messages.warning(request, "Quiz passed, but topic progress could not be updated.")
    
    # Calculate remaining attempts
    total_attempts = quiz.attempts_allowed
    used_attempts = QuizAttempt.objects.filter(user=request.user, quiz=quiz).count()
    remaining_attempts = max(0, total_attempts - used_attempts)
    
    context = {
        'quiz_attempt': quiz_attempt,
        'question_data': question_data,
        'passed': quiz_attempt.is_passed,
        'remaining_attempts': remaining_attempts,
        'total_attempts': total_attempts,
        'topic': quiz.topic if hasattr(quiz, 'topic') else None,
        'section': quiz.topic.section if hasattr(quiz, 'topic') else None,
        'course': quiz.topic.section.course if hasattr(quiz, 'topic') else None,
    }
    
    return render(request, 'quiz/quiz_results.html', context)













# rating 
@login_required
def submit_review(request, course_id):
    """
    Handle submission of course reviews by enrolled users
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is enrolled in the course
    try:
        enrollment = Enrollment.objects.get(user=request.user, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "You must be enrolled in the course to post a review.")
        return redirect('course_detail', course_id=course_id)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Validate input
        if not rating or not comment:
            messages.error(request, "Both rating and comment are required.")
            return redirect('course_detail', course_id=course_id)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
        except ValueError:
            messages.error(request, "Invalid rating value.")
            return redirect('course_detail', course_id=course_id)
        
        # Update or create the review
        review, created = Review.objects.update_or_create(
            course=course,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        if created:
            messages.success(request, "Your review has been submitted. Thank you for your feedback!")
        else:
            messages.success(request, "Your review has been updated.")
        
    return redirect('course_detail', course_id=course_id)