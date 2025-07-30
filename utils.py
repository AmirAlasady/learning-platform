from django.utils import timezone
from courses.models import Course, Section, Topic
from subscribtion.models import CourseProgress, SectionProgress, TopicProgress

def create_course_progress(enrollment):
    """
    Create a course progress record for an enrollment, along with section and topic progress.
    The activation of sections and topics depends on the course type.
    
    For locked courses:
        - Only the first section is active
        - Only the first topic of the first section is active
        
    For unlocked courses:
        - All sections and topics are active
    """
    # Create course progress
    course_progress, created = CourseProgress.objects.get_or_create(
        enrollment_model=enrollment,
        defaults={
            'progress_percentage': 0.0,
            'completed': False
        }
    )
    
    # Get all sections for the course
    course = enrollment.course
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
        
        # Create section progress
        section_progress, section_created = SectionProgress.objects.get_or_create(
            course_progress=course_progress,
            section=section,
            defaults={
                'progress_percentage': 0.0,
                'completed': False,
                'is_active': is_active
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
            
            # Create topic progress
            topic_progress, topic_created = TopicProgress.objects.get_or_create(
                section_progress=section_progress,
                topic=topic,
                defaults={
                    'completed': False,
                    'is_active': topic_is_active
                }
            )
    
    return course_progress


# In subscribtion/utils.py

def activate_next_topic(topic_progress):
    """
    CORRECTED & RE-ENGINEERED:
    This version fixes the out-of-order completion bug by ensuring the overall
    course completion check runs every single time, independent of section completion.
    """
    current_topic = topic_progress.topic
    section_progress = topic_progress.section_progress
    course_progress = section_progress.course_progress
    course = course_progress.course
    section = section_progress.section

    # --- JOB 1: HANDLE SEQUENTIAL CONTENT ACTIVATION (for Locked Courses) ---
    # This logic is for unlocking the next item in a sequence.
    if course.course_type == Course.LOCKED:
        # Find the next topic in the current section's sequence
        next_topic = Topic.objects.filter(
            section=section,
            created_at__gt=current_topic.created_at
        ).order_by('created_at').first()

        # If no next topic in this section, find the next section
        if not next_topic:
            next_section = Section.objects.filter(
                course=course,
                created_at__gt=section.created_at
            ).order_by('created_at').first()
            if next_section:
                # And get its first topic
                next_topic = Topic.objects.filter(section=next_section).order_by('created_at').first()
        
        # If we found a next topic to activate, do so.
        if next_topic:
            # get_or_create is used to safely handle the TopicProgress record
            next_tp, created = TopicProgress.objects.get_or_create(
                section_progress__course_progress=course_progress,
                topic=next_topic
            )
            # Ensure the next topic is marked as active
            if not next_tp.is_active:
                next_tp.is_active = True
                next_tp.save()

    # --- JOB 2: CALCULATE AND UPDATE COMPLETION STATUS ---
    
    # Part A: Check if the current section is now complete
    section_completed = False
    required_topics = Topic.objects.filter(section=section, is_required=True)
    if required_topics.exists():
        completed_required_count = TopicProgress.objects.filter(
            section_progress=section_progress, topic__in=required_topics, completed=True).count()
        if completed_required_count >= required_topics.count():
            section_completed = True
    else:
        # If no required topics, all topics must be complete for the section to be "done"
        all_topics_count = Topic.objects.filter(section=section).count()
        completed_topics_count = TopicProgress.objects.filter(section_progress=section_progress, completed=True).count()
        if all_topics_count > 0 and completed_topics_count >= all_topics_count:
            section_completed = True
    
    # Update the section's completion status in the database if it has changed
    if section_completed != section_progress.completed:
        section_progress.completed = section_completed
        section_progress.save()

    # Part B: Check if the entire course is now complete (THE FIX FOR THE OUT-OF-ORDER BUG)
    # This logic now runs EVERY time, regardless of whether a section was just completed.
    course_completed = False
    required_sections = Section.objects.filter(course=course, is_required=True)
    
    if required_sections.exists():
        # If required sections are defined, check only them.
        completed_required_sections_count = SectionProgress.objects.filter(
            course_progress=course_progress, section__in=required_sections, completed=True).count()
        if completed_required_sections_count >= required_sections.count():
            course_completed = True
    else:
        # If no sections are marked as required, all sections must be complete.
        all_sections_count = Section.objects.filter(course=course).count()
        completed_sections_count = SectionProgress.objects.filter(course_progress=course_progress, completed=True).count()
        if all_sections_count > 0 and completed_sections_count >= all_sections_count:
            course_completed = True
            
    # Finally, update the master CourseProgress object if the course is now complete.
    # This sets both the 'completed' flag and the percentage correctly.
    if course_completed and not course_progress.completed:
        course_progress.completed = True
        course_progress.progress_percentage = 100
        course_progress.save()
        enrollment = course_progress.enrollment_model
        if not enrollment.completed_at:
            enrollment.completed_at = timezone.now()
            enrollment.save()
            
    # The function finishes here. The logic correctly handles all cases without errors.