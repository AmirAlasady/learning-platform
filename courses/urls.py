

from django.urls import  path
from .views import *

urlpatterns = [
    #path('test/',test,name='test'),

    # landing page
    
    path('', index, name='index'),
    path('about', about, name='about'),
    # course list and detail views
    path('courses/', course_list, name='course_list'),
    path('course/<int:course_id>/', course_detail, name='course_detail'),
    path('course/study/<int:course_id>/', study, name='study_course'),
    # quiz tmp views 
    path('quiz/<int:quiz_id>/start/', start_quiz, name='start_quiz'),
    path('quiz/attempt/<int:attempt_id>/', take_quiz, name='take_quiz'),
    path('quiz/attempt/<int:attempt_id>/<int:question_index>/', take_quiz, name='take_quiz'),
    path('quiz/results/<int:attempt_id>/', quiz_results, name='quiz_results'),
    path('topic/<int:topic_id>/', topic_view, name='topic_view'),
    path('clear-quiz-redirect/', clear_quiz_redirect, name='clear_quiz_redirect'),
    # rating and review
    path('course/<int:course_id>/review/', submit_review, name='submit_review'),
]

