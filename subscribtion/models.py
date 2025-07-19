import time
from django.db import models
from accounts.models import User
from courses.models import Course, Section, Topic
# Create your models here.


# user enrollement model for courses
class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='enrolled_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = [
        ('active', 'ACTIVE'),
        ('paused', 'PAUSED'),
    ]

    enrolement_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
    )

    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.title}"

    class Meta:
        unique_together = ('user', 'course')  # Ensure a user can enroll in a course only once
        verbose_name = "Enrollment"

class CourseProgress(models.Model):
    enrollment_model = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='progress')
    # No need for a separate course field - we can access it through enrollment_model.course
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    last_accessed = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.enrollment_model.user.username} progress in {self.enrollment_model.course.title}"
    
    class Meta:
        verbose_name = "Course Progress"
        verbose_name_plural = "Course Progresses"

    @property
    def course(self):
        """Convenience property to access the course directly"""
        return self.enrollment_model.course


class SectionProgress(models.Model):
    course_progress = models.ForeignKey(CourseProgress, on_delete=models.CASCADE, related_name='section_progress')
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    last_accessed = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)  # Indicates if the section is active
    def __str__(self):
        return f"{self.course_progress.enrollment_model.user.username} progress in {self.section.title}"
    
class TopicProgress(models.Model):
    section_progress = models.ForeignKey(SectionProgress, on_delete=models.CASCADE, related_name='topic_progress')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    last_accessed = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)  # Indicates if the topic is active
    
    def __str__(self):
        return f"{self.section_progress.course_progress.enrollment_model.user.username} progress in {self.topic.title}"

    class Meta:
        verbose_name = "Topic Progress"
        verbose_name_plural = "Topic Progresses"







class Certificate(models.Model):
    """Model to track course completion certificates"""
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='certificate')
    issued_on = models.DateTimeField(auto_now_add=True)
    certificate_id = models.CharField(max_length=50, unique=True)
    pdf_file = models.FileField(upload_to='certificates/', null=True, blank=True)
    
    def __str__(self):
        return f"Certificate for {self.enrollment.user.username} - {self.enrollment.course.title}"
    
    def save(self, *args, **kwargs):
        # Generate a unique certificate ID if not already set
        if not self.certificate_id:
            # Format: CERT-{USER_ID}-{COURSE_ID}-{TIMESTAMP}
            timestamp = int(time.time())
            self.certificate_id = f"CERT-{self.enrollment.user.id}-{self.enrollment.course.id}-{timestamp}"
        
        super().save(*args, **kwargs)
    
    @property
    def user(self):
        return self.enrollment.user
    
    @property
    def course(self):
        return self.enrollment.course