from django.urls import path
from . import views

urlpatterns = [
    # Payment and enrollment
    path('enroll/<int:course_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/check/<str:transaction_id>/', views.check_transaction_status, name='check_transaction_status'),
    path('enroll-free/<int:course_id>/', views.enroll_free_course, name='enroll_free_course'),

    # Progress tracking
    path('mark-completed/<int:topic_id>/', views.mark_topic_as_completed, name='mark_topic_completed'),
    path('mark-completed-debug/<int:topic_id>/', views.mark_topic_as_completed_debug, name='mark_topic_completed_debug'),

    # debugging
    path('debug-video/<int:topic_id>/', views.debug_video_view, name='debug_video_view'),
    path('super-debug/<int:topic_id>/', views.super_detailed_debug, name='super_detailed_debug'),

    #certificate generation
    path('certificate/<int:course_id>/', views.generate_certificate, name='generate_certificate'),
    path('certificate/view/<str:certificate_id>/', views.view_certificate, name='view_certificate'),
    path('certificate/download/<str:certificate_id>/', views.download_certificate, name='download_certificate'),
]