from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from .models import Course, Lesson, Enrollment, Question, Choice, Submission

# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        return Course.objects.order_by('-total_enrollment')[:10]

# CourseDetailsView
class CourseDetailsView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'

# EnrollView
class EnrollView(generic.View):
    def post(self, request, *args, **kwargs):
        course_id = kwargs.get('pk')
        course = get_object_or_404(Course, pk=course_id)
        user = request.user
        if user.is_authenticated:
            Enrollment.objects.get_or_create(user=user, course=course, mode='audit')
        return redirect('onlinecourse:course_details', pk=course.id)

# Helper function to extract selected choice ids from POST request
def extract_selected_choice_ids(request):
    selected_choice_ids = []
    for key, value in request.POST.lists():
        if key.startswith('choice_'):
            for choice_id in value:
                selected_choice_ids.append(int(choice_id))
    if not selected_choice_ids and 'choice' in request.POST:
        selected_choice_ids = [int(x) for x in request.POST.getlist('choice')]
    return selected_choice_ids

# View for submitting exam
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if request.method == 'POST':
        user = request.user
        enrollment = Enrollment.objects.filter(user=user, course=course).first()
        if not enrollment:
            enrollment = Enrollment.objects.create(user=user, course=course, mode='audit')

        selected_choice_ids = extract_selected_choice_ids(request)
        submission = Submission.objects.create(enrollment=enrollment)
        for choice_id in selected_choice_ids:
            choice = Choice.objects.filter(pk=choice_id).first()
            if choice:
                submission.choices.add(choice)
        submission.save()

        return redirect('onlinecourse:show_exam_result', course_id=course.id, submission_id=submission.id)
    return redirect('onlinecourse:course_details', pk=course.id)

# View for showing exam results
def show_exam_result(request, course_id, submission_id):
    context = {}
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    selected_choices = submission.choices.all()
    selected_choice_ids = [c.id for c in selected_choices]

    questions = course.question_set.all()
    if not questions.exists():
        questions = Question.objects.filter(lesson__course=course)

    # Calculate total possible points and earned score
    possible = 0
    earned_score = 0
    for question in questions:
        possible += question.grade
        if question.is_get_score(selected_choice_ids):
            earned_score += question.grade

    if possible == 0:
        possible = 100

    grade = int((earned_score / possible) * 100) if possible > 0 else 0

    context['course'] = course
    context['selected_ids'] = selected_choice_ids
    context['grade'] = grade
    context['score'] = earned_score
    context['earned_score'] = earned_score
    context['possible'] = possible
    context['total_possible'] = possible
    context['submission'] = submission
    context['questions'] = questions

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
