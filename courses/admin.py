from django.contrib import admin
from django import forms
from .models import (
    Chategory, Course, Section, Topic, 
    Question, Answer, Quiz, QuizAttempt, SelectedAnswer
)


# Inline classes for nested administration
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    fields = ('text', 'is_correct')


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ('name', 'text', 'mark')
    inlines = [AnswerInline]
    # Since Question doesn't have a direct FK to Quiz, we'll handle this through the Quiz admin


class TopicInline(admin.StackedInline):
    model = Topic
    extra = 1
    fields = ('title', 'description', 'is_required', 'content_type', 
              'VIDEO_CINTETN_FILE', 'ARTICLE_CONTENT')
    classes = ['collapse']


class SectionInline(admin.StackedInline):
    model = Section
    extra = 1
    fields = ('title', 'description', 'is_required')
    classes = ['collapse']


class QuizInline(admin.StackedInline):
    model = Quiz
    fields = ('name', 'description', 'attempts_allowed', 
              'duration_minutes', 'passing_score', 'is_active')
    extra = 0
    classes = ['collapse']


class SelectedAnswerInline(admin.TabularInline):
    model = SelectedAnswer
    extra = 0
    fields = ('question', 'answer')
    readonly_fields = ('question', 'answer')


# Main admin classes
@admin.register(Chategory)
class ChategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'course_type', 'course_level', 'created_at')
    list_filter = ('category', 'course_type', 'course_level', 'created_at')
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'image', 'category', 'price')
        }),
        ('Course Settings', {
            'fields': ('course_type', 'course_level', 'deadline'),
            'classes': ('collapse',),
        }),
    )
    inlines = [SectionInline]
    list_per_page = 20


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'is_required', 'created_at')
    list_filter = ('course', 'is_required', 'created_at')
    search_fields = ('title', 'description', 'course__title')
    inlines = [TopicInline]


class TopicAdminForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = '__all__'
        
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        video_file = cleaned_data.get('VIDEO_CINTETN_FILE')
        article_content = cleaned_data.get('ARTICLE_CONTENT')
        
        if content_type == 'video' and not video_file:
            self.add_error('VIDEO_CINTETN_FILE', 'Video file is required for video content type')
        elif content_type == 'article' and not article_content:
            self.add_error('ARTICLE_CONTENT', 'Article content is required for article content type')
        
        return cleaned_data


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    form = TopicAdminForm
    list_display = ('title', 'section', 'content_type', 'is_required', 'created_at')
    list_filter = ('section__course', 'section', 'content_type', 'is_required')
    search_fields = ('title', 'description', 'section__title', 'section__course__title')
    fieldsets = (
        (None, {
            'fields': ('section', 'title', 'description', 'is_required')
        }),
        ('Content Settings', {
            'fields': ('content_type', 'VIDEO_CINTETN_FILE', 'ARTICLE_CONTENT'),
            'classes': ('collapse',),
        }),
    )
    inlines = [QuizInline]
    list_per_page = 20


class QuizAdminForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = '__all__'
        
    def clean(self):
        cleaned_data = super().clean()
        topic = cleaned_data.get('topic')
        
        if topic and topic.content_type != 'quiz':
            self.add_error('topic', 'Quiz can only be attached to a topic with content type "quiz"')
        
        return cleaned_data


class QuestionsInQuizInline(admin.TabularInline):
    model = Quiz.questions.through
    extra = 1
    verbose_name = "Question"
    verbose_name_plural = "Questions"


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    form = QuizAdminForm
    list_display = ('name', 'topic', 'attempts_allowed', 'passing_score', 'total_marks', 'is_active')
    list_filter = ('topic__section__course', 'is_active')
    search_fields = ('name', 'description', 'topic__title')
    fieldsets = (
        (None, {
            'fields': ('topic', 'name', 'description')
        }),
        ('Quiz Settings', {
            'fields': ('attempts_allowed', 'duration_minutes', 'passing_score', 'is_active'),
            'classes': ('collapse',),
        }),
    )
    filter_horizontal = ('questions',)
    inlines = [QuestionsInQuizInline]
    exclude = ('questions',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'text', 'mark', 'created_at')
    search_fields = ('name', 'text')
    list_filter = ('mark', 'created_at')
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'is_correct')
    list_filter = ('is_correct', 'question')
    search_fields = ('text', 'question__text', 'question__name')


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'is_passed', 'started_at', 'completed_at')
    list_filter = ('quiz', 'is_passed', 'started_at')
    search_fields = ('user__username', 'quiz__name')
    readonly_fields = ('score', 'is_passed')
    inlines = [SelectedAnswerInline]
    
    actions = ['recalculate_scores']
    
    def recalculate_scores(self, request, queryset):
        updated = 0
        for attempt in queryset:
            attempt.calculate_score()
            attempt.save()
            updated += 1
        self.message_user(request, f'Recalculated scores for {updated} attempts.')
    
    recalculate_scores.short_description = "Recalculate selected attempts' scores"


# No need to register SelectedAnswer as it's managed through QuizAttempt
