from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment, CourseProgress, SectionProgress, TopicProgress
from courses.models import Course, Section, Topic

@receiver(post_save, sender=Enrollment)
def create_progress_on_enrollment(sender, instance, created, **kwargs):
    """
    Modified signal handler that doesn't use is_active field
    if it doesn't exist in the database schema yet.
    """
    if not created:
        return
        
    # Create course progress
    course_progress, created = CourseProgress.objects.get_or_create(
        enrollment_model=instance,
        defaults={
            'progress_percentage': 0.0,
            'completed': False
        }
    )
    
    # Get all sections for the course
    course = instance.course
    sections = Section.objects.filter(course=course).order_by('created_at')
    
    # Track if we've set the first section/topic active (for locked courses)
    first_section_done = False
    
    # Create section progress for each section
    for index, section in enumerate(sections):
        # Determine if this section should be active
        is_active = False
        if course.course_type == Course.UNLOCKED:
            # For unlocked courses, all sections are active
            is_active = True
        elif course.course_type == Course.LOCKED and not first_section_done:
            # For locked courses, only the first section is active
            is_active = True
            first_section_done = True
        
        # Create section progress - don't use is_active if the field doesn't exist
        try:
            section_progress, section_created = SectionProgress.objects.get_or_create(
                course_progress=course_progress,
                section=section,
                defaults={
                    'progress_percentage': 0.0,
                    'completed': False,
                    'is_active': is_active  # May cause error if field doesn't exist
                }
            )
        except Exception:
            # Fallback if is_active doesn't exist in database yet
            section_progress, section_created = SectionProgress.objects.get_or_create(
                course_progress=course_progress,
                section=section,
                defaults={
                    'progress_percentage': 0.0,
                    'completed': False
                }
            )
        
        # Create topic progress for each topic in this section
        topics = Topic.objects.filter(section=section).order_by('created_at')
        first_topic_done = False
        
        for topic_index, topic in enumerate(topics):
            # Determine if this topic should be active
            topic_is_active = False
            if course.course_type == Course.UNLOCKED:
                # For unlocked courses, all topics are active
                topic_is_active = True
            elif course.course_type == Course.LOCKED and is_active and not first_topic_done:
                # For locked courses, only the first topic of the active section is active
                topic_is_active = True
                first_topic_done = True
            
            # Create topic progress - don't use is_active if the field doesn't exist
            try:
                topic_progress, topic_created = TopicProgress.objects.get_or_create(
                    section_progress=section_progress,
                    topic=topic,
                    defaults={
                        'completed': False,
                        'is_active': topic_is_active  # May cause error if field doesn't exist
                    }
                )
            except Exception:
                # Fallback if is_active doesn't exist in database yet
                topic_progress, topic_created = TopicProgress.objects.get_or_create(
                    section_progress=section_progress,
                    topic=topic,
                    defaults={
                        'completed': False
                    }
                )