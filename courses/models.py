
from django.db import models
from accounts.models import User  # Assuming you have a User model in accounts app
from django.db.models.signals import post_save
from django.dispatch import receiver

class Chategory(models.Model):  # Corrected typo in "model" to "models"
    name = models.CharField(max_length=100)
    description = models.TextField()
    #image = models.ImageField(upload_to='categories/')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name
 



class Course(models.Model):  # Corrected typo in "model" to "models"
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='courses/')
    category = models.ForeignKey(Chategory, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)


    # types 
    LOCKED = 'locked'
    MANAGED = 'managed'
    UNLOCKED = 'unlocked'
    
    COURSE_TYPE_CHOICES = [
        (LOCKED, 'Locked'),
        (MANAGED, 'Managed'),
        (UNLOCKED, 'Unlocked'),
    ]

    course_type = models.CharField(
        max_length=10,
        choices=COURSE_TYPE_CHOICES,
        default=LOCKED,
    )
    
    #finished_by= models.ManyToManyField(User, related_name='finished_courses', blank=True)
    #enrolled_users = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)
    deadline = models.DateTimeField(null=True, blank=True)  # Optional field for deadline


    # levelS
    BEGINNER = 'beginner'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'
    GENERAL = 'general'

    COURSE_LEVEL_CHOICES = [
        (BEGINNER, 'beginner'),
        (INTERMEDIATE, 'intermediate'),
        (ADVANCED, 'advanced'),
        (GENERAL, 'general'),

    ]
    course_level=models.CharField(
        max_length=20,
        choices=COURSE_LEVEL_CHOICES,
        default=GENERAL,
    )

    def __str__(self):
        return self.title
    

class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    description = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)
    is_required = models.BooleanField(default=True)  # Fixed typo
    #is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title



    

class Topic(models.Model):  
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    description = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    # ctl
    is_required = models.BooleanField(default=False)  # Optional field for required topic
    #is_active = models.BooleanField(default=True)  # Optional field for active topic

    # types set on linlking when making quiz
    VIDEO = 'video'
    ARTICLE = 'article'
    QUIZ = 'quiz'

    content_type = models.CharField(
        max_length=10,
        choices=[
            (VIDEO, 'Video'),
            (ARTICLE, 'Article'),
            (QUIZ, 'Quiz'),
        ],
        default=VIDEO,
    )
    
    VIDEO_CINTETN_FILE = models.FileField(upload_to='topics/videos', blank=True, null=True)  # Optional field for file upload
    ARTICLE_CONTENT = models.TextField(blank=True, null=True)  # Optional field for article content
    #QUIZ_CONTENT = models.ForeignKey(Q)
    def __str__(self):
        return self.title





















class Question(models.Model):
    name = models.CharField(max_length=200, default='')
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    mark = models.IntegerField(default=1)  # Points for this question
    
    def __str__(self):
        return self.name

class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.text

class Quiz(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name='quizz')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    questions = models.ManyToManyField(Question, related_name='quizzes')
    # Remove the M2M to answers - they're accessed through questions
    # answers = models.ManyToManyField(Answer, related_name='quizzes')  - REMOVE THIS
    attempts_allowed = models.IntegerField(default=1)  # Renamed for clarity
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)  # Changed to minutes for simplicity
    passing_score = models.PositiveIntegerField(default=70)  # Percentage needed to pass
    is_active = models.BooleanField(default=True)
    
    def total_marks(self):
        return sum(q.mark for q in self.questions.all())
    
    def __str__(self):
        return self.name

class QuizAttempt(models.Model):  # Renamed for consistency and clarity
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    is_passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def calculate_score(self):
        correct_answers = self.selected_answers.filter(answer__is_correct=True).count()
        total_questions = self.quiz.questions.count()
        self.score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
        self.is_passed = self.score >= self.quiz.passing_score
        return self.score
    
    def __str__(self):
        return f'{self.user.username} - {self.quiz.name} - {self.score}%'

class SelectedAnswer(models.Model):
    """Track which answers a user selected for each question"""
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='selected_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['quiz_attempt', 'question']  # One answer per question per attempt
    
    def __str__(self):
        return f"{self.quiz_attempt.user.username}'s answer to {self.question.name}"
    








# Add this to the end of courses/models.py

class Review(models.Model):
    """Model for course reviews by enrolled users"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_reviews')
    rating = models.IntegerField(
        choices=[
            (1, '1 - Poor'),
            (2, '2 - Fair'),
            (3, '3 - Good'),
            (4, '4 - Very Good'),
            (5, '5 - Excellent')
        ]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Ensure each user can only review a course once
        unique_together = ('course', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.course.title}"