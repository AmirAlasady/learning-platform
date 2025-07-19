
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


def activate_next_topic(topic_progress):
    """
    Activate the next topic after completing the current one.
    For locked courses, this enables sequential progress.
    Enhanced to better handle section completion.
    """
    current_topic = topic_progress.topic
    section_progress = topic_progress.section_progress
    course_progress = section_progress.course_progress
    course = course_progress.course
    
    # If it's an unlocked course, all topics are already active
    if course.course_type == Course.UNLOCKED:
        return
    
    # Check if the current section is now completed after this topic
    section = section_progress.section
    
    # Get all required topics in this section
    required_topics = Topic.objects.filter(
        section=section,
        is_required=True
    )
    
    # If the section has required topics, check if they're all completed
    section_completed = True
    if required_topics.exists():
        # Check if all required topics are completed
        for req_topic in required_topics:
            try:
                topic_prog = TopicProgress.objects.get(
                    section_progress=section_progress, 
                    topic=req_topic
                )
                if not topic_prog.completed:
                    section_completed = False
                    break
            except TopicProgress.DoesNotExist:
                section_completed = False
                break
    else:
        # If no required topics, check if all topics are completed
        all_topics = Topic.objects.filter(section=section)
        all_completed = True
        for t in all_topics:
            try:
                topic_prog = TopicProgress.objects.get(
                    section_progress=section_progress, 
                    topic=t
                )
                if not topic_prog.completed:
                    all_completed = False
                    break
            except TopicProgress.DoesNotExist:
                all_completed = False
                break
        section_completed = all_completed
    
    # Update section completion status
    if section_completed and not section_progress.completed:
        section_progress.completed = True
        section_progress.progress_percentage = 100.0
        section_progress.save()
        
        # When section is completed, activate the next section
        next_section = Section.objects.filter(
            course=course,
            created_at__gt=section.created_at
        ).order_by('created_at').first()
        
        if next_section:
            # Activate the next section
            next_section_progress, section_created = SectionProgress.objects.get_or_create(
                course_progress=course_progress,
                section=next_section,
                defaults={
                    'progress_percentage': 0.0,
                    'completed': False,
                    'is_active': True
                }
            )
            
            if not section_created:
                next_section_progress.is_active = True
                next_section_progress.save()
            
            # Activate the first topic of the next section
            first_topic = Topic.objects.filter(section=next_section).order_by('created_at').first()
            if first_topic:
                next_topic_progress, topic_created = TopicProgress.objects.get_or_create(
                    section_progress=next_section_progress,
                    topic=first_topic,
                    defaults={
                        'completed': False,
                        'is_active': True
                    }
                )
                
                if not topic_created:
                    next_topic_progress.is_active = True
                    next_topic_progress.save()
                
                return  # We've activated the next section, so we're done
    
    # If the section isn't completed yet, or there's no next section,
    # try to activate the next topic in the current section
    next_topic = Topic.objects.filter(
        section=current_topic.section,
        created_at__gt=current_topic.created_at
    ).order_by('created_at').first()
    
    if next_topic:
        # Activate the next topic in the same section
        next_topic_progress, created = TopicProgress.objects.get_or_create(
            section_progress=section_progress,
            topic=next_topic,
            defaults={
                'completed': False,
                'is_active': True
            }
        )
        
        if not created:
            next_topic_progress.is_active = True
            next_topic_progress.save()

