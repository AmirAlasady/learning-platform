# management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from courses.models import Course, Section, Topic, Quiz, Question, Answer
from .forms import *

# Helper to check if user is an admin
def is_admin(user):
    return user.is_staff

@user_passes_test(is_admin)
def dashboard(request):
    course_count = Course.objects.count()
    context = {'course_count': course_count}
    return render(request, 'management/dashboard.html', context)

# --- Course Views ---

@user_passes_test(is_admin)
def course_list(request):
    courses = Course.objects.all().order_by('-created_at')
    return render(request, 'management/course_list.html', {'courses': courses})

@user_passes_test(is_admin)
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course "{course.title}" created successfully.')
            return redirect('management:manage_course', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'management/course_form.html', {'form': form, 'title': 'Create New Course'})

@user_passes_test(is_admin)
def manage_course(request, pk):
    """
    This is the main hub for managing a single course.
    It handles both updating the course and listing its sections.
    """
    course = get_object_or_404(Course, pk=pk)
    sections = Section.objects.filter(course=course).order_by('created_at')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course details updated successfully.')
            return redirect('management:manage_course', pk=course.pk)
    else:
        form = CourseForm(instance=course)
        
    context = {
        'form': form,
        'course': course,
        'sections': sections,
    }
    return render(request, 'management/manage_course.html', context)

@user_passes_test(is_admin)
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course_title = course.title
        course.delete()
        messages.success(request, f'Course "{course_title}" was deleted.')
        return redirect('management:course_list')
    return render(request, 'management/confirm_delete.html', {'object': course, 'type': 'Course'})


# --- Section Views ---

@user_passes_test(is_admin)
def section_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    print('1')
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.course = course
            section.save()
            messages.success(request, f'Section "{section.title}" created.')
            return redirect('management:manage_course', pk=course.pk)
    else:
        print('2')
        form = SectionForm()
        print('3')
    return render(request, 'management/section_form.html', {'form': form, 'course': course, 'title': 'Create New Section'})

@user_passes_test(is_admin)
def manage_section(request, pk):
    """
    Hub for managing a single section.
    Handles updating the section and listing its topics.
    """
    section = get_object_or_404(Section, pk=pk)
    topics = Topic.objects.filter(section=section).order_by('created_at')
    
    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, 'Section details updated successfully.')
            return redirect('management:manage_section', pk=section.pk)
    else:
        form = SectionForm(instance=section)
        
    context = {
        'form': form,
        'section': section,
        'topics': topics,
    }
    return render(request, 'management/manage_section.html', context)

@user_passes_test(is_admin)
def section_delete(request, pk):
    section = get_object_or_404(Section, pk=pk)
    course_pk = section.course.pk
    if request.method == 'POST':
        section_title = section.title
        section.delete()
        messages.success(request, f'Section "{section_title}" was deleted.')
        return redirect('management:manage_course', pk=course_pk)
    return render(request, 'management/confirm_delete.html', {'object': section, 'type': 'Section', 'parent_pk': course_pk, 'parent_url_name': 'manage_course'})

# --- Topic Views ---

@user_passes_test(is_admin)
def topic_create(request, section_pk):
    section = get_object_or_404(Section, pk=section_pk)
    if request.method == 'POST':
        form = TopicForm(request.POST, request.FILES)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.section = section
            topic.save()
            messages.success(request, f'Topic "{topic.title}" created.')
            return redirect('management:manage_section', pk=section.pk)
    else:
        form = TopicForm()
    return render(request, 'management/topic_form.html', {'form': form, 'section': section, 'title': 'Create New Topic'})

@user_passes_test(is_admin)
def topic_edit(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if request.method == 'POST':
        form = TopicForm(request.POST, request.FILES, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, 'Topic updated successfully.')
            return redirect('management:manage_section', pk=topic.section.pk)
    else:
        form = TopicForm(instance=topic)
    return render(request, 'management/topic_form.html', {'form': form, 'section': topic.section, 'title': 'Edit Topic'})

@user_passes_test(is_admin)
def topic_delete(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    section_pk = topic.section.pk
    if request.method == 'POST':
        topic_title = topic.title
        topic.delete()
        messages.success(request, f'Topic "{topic_title}" was deleted.')
        return redirect('management:manage_section', pk=section_pk)
    return render(request, 'management/confirm_delete.html', {'object': topic, 'type': 'Topic', 'parent_pk': section_pk, 'parent_url_name': 'manage_section'})

# --- Quiz Views ---
@user_passes_test(is_admin)
def manage_quiz(request, topic_pk):
    """
    This is the central hub for a single quiz.
    It handles editing quiz settings AND adding/listing questions.
    """
    topic = get_object_or_404(Topic, pk=topic_pk)
    # Get or create the quiz associated with this topic
    quiz, created = Quiz.objects.get_or_create(
        topic=topic,
        defaults={'name': f"Quiz for {topic.title}", 'description': f"Test your knowledge on {topic.title}."}
    )
    questions = quiz.questions.all().order_by('created_at')

    # Handle the two forms on this page
    quiz_form = QuizForm(instance=quiz)
    question_form = QuestionForm()

    if request.method == 'POST':
        # Check which form was submitted
        if 'update_quiz' in request.POST:
            quiz_form = QuizForm(request.POST, instance=quiz)
            if quiz_form.is_valid():
                quiz_form.save()
                messages.success(request, 'Quiz settings have been updated.')
                return redirect('management:manage_quiz', topic_pk=topic.pk)
        
        elif 'add_question' in request.POST:
            question_form = QuestionForm(request.POST)
            if question_form.is_valid():
                question = question_form.save()
                quiz.questions.add(question)
                messages.success(request, 'New question has been added.')
                return redirect('management:manage_quiz', topic_pk=topic.pk)

    context = {
        'topic': topic,
        'quiz': quiz,
        'questions': questions,
        'quiz_form': quiz_form,
        'question_form': question_form,
    }
    return render(request, 'management/manage_quiz.html', context)

@user_passes_test(is_admin)
def manage_question(request, pk):
    """
    Central hub for managing a single question and its answers.
    """
    question = get_object_or_404(Question, pk=pk)
    
    # THIS IS THE FIX: Order by 'id' instead of the non-existent 'created_at'
    answers = question.answers.all().order_by('id')

    # Handle the two forms
    question_form = QuestionForm(instance=question)
    answer_form = AnswerForm()

    if request.method == 'POST':
        # Check which form was submitted
        if 'update_question' in request.POST:
            question_form = QuestionForm(request.POST, instance=question)
            if question_form.is_valid():
                question_form.save()
                messages.success(request, 'Question has been updated.')
                return redirect('management:manage_question', pk=question.pk)
        
    context = {
        'question': question,
        'answers': answers,
        'question_form': question_form,
        'answer_form': answer_form,
        'quiz_topic_pk': question.quizzes.first().topic.pk, # For the back button
    }
    return render(request, 'management/manage_question.html', context)


@user_passes_test(is_admin)
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    # We need to find the topic_pk to redirect back to the quiz page
    quiz = question.quizzes.first()
    if not quiz:
        messages.error(request, 'Cannot delete question as it is not linked to any quiz.')
        return redirect('management:dashboard') # Or a more suitable page

    topic_pk = quiz.topic.pk
    if request.method == 'POST':
        question_text = question.text
        question.delete()
        messages.success(request, f'Question "{question_text[:30]}..." was deleted.')
        return redirect('management:manage_quiz', topic_pk=topic_pk)
    
    context = {
        'object': question, 
        'type': 'Question', 
        'parent_url_name': 'manage_quiz', 
        'parent_pk': topic_pk, 
        'parent_is_topic': True
    }
    return render(request, 'management/confirm_delete.html', context)


@user_passes_test(is_admin)
def answer_create(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.question = question
            answer.save()
            messages.success(request, 'Answer choice created.')
    return redirect('management:manage_question', pk=question.pk)

@user_passes_test(is_admin)
def answer_edit(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    if request.method == 'POST':
        form = AnswerForm(request.POST, instance=answer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Answer updated.')
            return redirect('management:manage_question', pk=answer.question.pk)
    else:
        form = AnswerForm(instance=answer)
    return render(request, 'management/answer_form.html', {'form': form, 'answer': answer})


@user_passes_test(is_admin)
def answer_delete(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    question_pk = answer.question.pk
    if request.method == 'POST':
        answer.delete()
        messages.success(request, 'Answer deleted.')
    return redirect('management:manage_question', pk=question_pk)