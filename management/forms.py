# management/forms.py

from django import forms
from courses.models import Course, Section, Topic, Quiz, Question, Answer

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'image', 'category', 'price', 'course_type', 'deadline', 'course_level']
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['title', 'description', 'is_required']

class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['title', 'description', 'is_required', 'content_type', 'VIDEO_CINTETN_FILE', 'ARTICLE_CONTENT']

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['name', 'description', 'attempts_allowed', 'duration_minutes', 'passing_score', 'is_active']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['name', 'text', 'mark']

# NEW: Form for creating/editing answers
class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Enter answer text'}),
        }