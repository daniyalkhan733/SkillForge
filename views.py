# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.http import HttpResponseForbidden
from .models import Course, Module, Lesson, Enrollment, Category, Review, LessonCompletion
from .forms import CourseForm, ModuleForm, LessonForm, ReviewForm

# Course List Views
class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 9
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class CategoryCoursesView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 9
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, id=self.kwargs['category_id'])
        return Course.objects.filter(category=self.category)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_category'] = self.category
        return context

# Course Detail View
class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['is_enrolled'] = Enrollment.objects.filter(
                user=self.request.user, 
                course=self.object
            ).exists()
            if context['is_enrolled']:
                enrollment = Enrollment.objects.get(
                    user=self.request.user, 
                    course=self.object
                )
                context['enrollment'] = enrollment
        
        context['reviews'] = self.object.reviews.all()
        context['review_form'] = ReviewForm()
        return context

# Instructor Course Management
@login_required
def instructor_courses(request):
    if not request.user.profile.is_instructor:
        return HttpResponseForbidden("You are not registered as an instructor.")
    
    courses = Course.objects.filter(instructor=request.user)
    return render(request, 'courses/instructor/courses.html', {'courses': courses})

# Instructor Course CRUD Views
class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/instructor/course_form.html'
    success_url = reverse_lazy('instructor_courses')
    
    def form_valid(self, form):
        form.instance.instructor = self.request.user
        form.instance.slug = slugify(form.instance.title)
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.profile.is_instructor:
            return HttpResponseForbidden("You are not registered as an instructor.")
        return super().dispatch(request, *args, **kwargs)

class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/instructor/course_form.html'
    
    def get_success_url(self):
        return reverse_lazy('course_detail', kwargs={'slug': self.object.slug})
    
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.instructor != request.user:
            return HttpResponseForbidden("You are not the instructor of this course.")
        return super().dispatch(request, *args, **kwargs)

class CourseDeleteView(DeleteView):
    model = Course
    template_name = 'courses/instructor/course_confirm_delete.html'
    success_url = reverse_lazy('instructor_courses')
    
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.instructor != request.user:
            return HttpResponseForbidden("You are not the instructor of this course.")
        return super().dispatch(request, *args, **kwargs)

# Module Management
@login_required
def module_list(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    return render(request, 'courses/instructor/module_list.html', {'course': course})

@login_required
def module_create(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, "Module created successfully.")
            return redirect('module_list', course_id=course.id)
    else:
        form = ModuleForm()
    
    return render(request, 'courses/instructor/module_form.html', {
        'form': form,
        'course': course,
        'title': 'Create Module'
    })

# Lesson Management
@login_required
def lesson_list(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if module.course.instructor != request.user:
        return HttpResponseForbidden("You are not the instructor of this course.")
    
    return render(request, 'courses/instructor/lesson_list.html', {'module': module})

@login_required
def lesson_create(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    
    if module.course.instructor != request.user:
        return HttpResponseForbidden("You are not the instructor of this course.")
    
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.save()
            messages.success(request, "Lesson created successfully.")
            return redirect('lesson_list', module_id=module.id)
    else:
        form = LessonForm()
    
    return render(request, 'courses/instructor/lesson_form.html', {
        'form': form,
        'module': module,
        'title': 'Create Lesson'
    })

# Student Enrollment
@login_required
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "You are already enrolled in this course.")
    else:
        Enrollment.objects.create(user=request.user, course=course)
        messages.success(request, f"You have successfully enrolled in '{course.title}'")
    
    return redirect('course_detail', slug=slug)

@login_required
def my_courses(request):
    enrollments = Enrollment.objects.filter(user=request.user).order_by('-enrolled_at')
    return render(request, 'courses/student/my_courses.html', {'enrollments': enrollments})

@login_required
def course_content(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    course = enrollment.course
    return render(request, 'courses/student/course_content.html', {'course': course, 'enrollment': enrollment})

# Lesson Viewing and Progress Tracking
@login_required
def lesson_view(request, lesson_id):