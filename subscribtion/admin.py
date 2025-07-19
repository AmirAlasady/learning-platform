from django.contrib import admin
from .models import Enrollment, CourseProgress, SectionProgress, TopicProgress

class TopicProgressInline(admin.TabularInline):
    model = TopicProgress
    extra = 0
    readonly_fields = ('last_accessed',)
    fields = ('topic', 'completed', 'last_accessed')

class SectionProgressInline(admin.TabularInline):
    model = SectionProgress
    extra = 0
    readonly_fields = ('last_accessed',)
    fields = ('section', 'progress_percentage', 'completed', 'last_accessed')
    show_change_link = True

class CourseProgressInline(admin.StackedInline):
    model = CourseProgress
    can_delete = False
    extra = 0
    readonly_fields = ('last_accessed',)
    fields = ('progress_percentage', 'completed', 'last_accessed')
    show_change_link = True
    
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'enrolled_at', 'enrolement_status', 'is_completed')
    list_filter = ('enrolement_status', 'enrolled_at', 'completed_at', 'course')
    search_fields = ('user__username', 'user__email', 'course__title')
    readonly_fields = ('enrolled_at',)
    raw_id_fields = ('user', 'course')
    date_hierarchy = 'enrolled_at'
    inlines = [CourseProgressInline]
    
    def is_completed(self, obj):
        return bool(obj.completed_at)
    is_completed.boolean = True
    is_completed.short_description = 'Completed'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'course')

@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'progress_percentage', 'completed', 'last_accessed')
    list_filter = ('completed', 'last_accessed')
    search_fields = ('enrollment_model__user__username', 'enrollment_model__course__title')
    readonly_fields = ('last_accessed', 'enrollment_model')
    inlines = [SectionProgressInline]
    
    def user(self, obj):
        return obj.enrollment_model.user
    user.short_description = 'User'
    user.admin_order_field = 'enrollment_model__user'
    
    def course(self, obj):
        return obj.enrollment_model.course
    course.short_description = 'Course'
    course.admin_order_field = 'enrollment_model__course'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('enrollment_model__user', 'enrollment_model__course')

@admin.register(SectionProgress)
class SectionProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'user', 'course', 'progress_percentage', 'completed', 'last_accessed')
    list_filter = ('completed', 'last_accessed', 'section')
    search_fields = ('section__title', 'course_progress__enrollment_model__user__username')
    readonly_fields = ('last_accessed',)
    inlines = [TopicProgressInline]
    
    def user(self, obj):
        return obj.course_progress.enrollment_model.user
    user.short_description = 'User'
    user.admin_order_field = 'course_progress__enrollment_model__user'
    
    def course(self, obj):
        return obj.course_progress.enrollment_model.course
    course.short_description = 'Course'
    course.admin_order_field = 'course_progress__enrollment_model__course'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'section', 
            'course_progress__enrollment_model__user', 
            'course_progress__enrollment_model__course'
        )

@admin.register(TopicProgress)
class TopicProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'topic', 'section', 'user', 'course', 'completed', 'last_accessed')
    list_filter = ('completed', 'last_accessed', 'topic__content_type')
    search_fields = ('topic__title', 'section_progress__section__title')
    readonly_fields = ('last_accessed',)
    
    def section(self, obj):
        return obj.section_progress.section
    section.short_description = 'Section'
    section.admin_order_field = 'section_progress__section'
    
    def user(self, obj):
        return obj.section_progress.course_progress.enrollment_model.user
    user.short_description = 'User'
    user.admin_order_field = 'section_progress__course_progress__enrollment_model__user'
    
    def course(self, obj):
        return obj.section_progress.course_progress.enrollment_model.course
    course.short_description = 'Course'
    course.admin_order_field = 'section_progress__course_progress__enrollment_model__course'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'topic',
            'section_progress__section',
            'section_progress__course_progress__enrollment_model__user',
            'section_progress__course_progress__enrollment_model__course'
        )