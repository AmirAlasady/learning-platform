# management/urls.py

from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # --- Course Level ---
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/manage/', views.manage_course, name='manage_course'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),

    # --- Section Level ---
    path('courses/<int:course_pk>/sections/create/', views.section_create, name='section_create'),
    path('sections/<int:pk>/manage/', views.manage_section, name='manage_section'),
    path('sections/<int:pk>/delete/', views.section_delete, name='section_delete'),

    # --- Topic Level ---
    path('sections/<int:section_pk>/topics/create/', views.topic_create, name='topic_create'),
    path('topics/<int:pk>/edit/', views.topic_edit, name='topic_edit'),
    path('topics/<int:pk>/delete/', views.topic_delete, name='topic_delete'),

    # --- NEW & IMPROVED Quiz/Question/Answer URLs ---
    # A single hub for a quiz and its questions
    path('topics/<int:topic_pk>/quiz/', views.manage_quiz, name='manage_quiz'),

    # A central hub for managing a question and its answers
    path('questions/<int:pk>/manage/', views.manage_question, name='manage_question'),
    path('questions/<int:pk>/delete/', views.question_delete, name='question_delete'),

    # URL for handling answer creation and updates
    path('questions/<int:question_pk>/answers/create/', views.answer_create, name='answer_create'),
    path('answers/<int:pk>/edit/', views.answer_edit, name='answer_edit'),
    path('answers/<int:pk>/delete/', views.answer_delete, name='answer_delete'),
]