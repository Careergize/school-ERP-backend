from datetime import timedelta
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from core.api import ERPAPIView
from core.services import allowed_students, queryset_for, HTTPException, audit
from .models import ImprovementPlan, LearningTask


def percentage(result):
    return round(result.marks / result.exam.max_marks * 100, 1)


def plans(user):
    return ImprovementPlan.objects.filter(baseline__student__in=allowed_students(user)).select_related('baseline__student', 'baseline__exam__subject', 'teacher', 'reassessment__exam').prefetch_related('tasks')


def present(plan):
    return dict(id=plan.pk, baseline_id=plan.baseline_id, student=plan.baseline.student.name, subject=plan.baseline.exam.subject.name,
        topic=plan.topic, teacher=str(plan.teacher), due=plan.due, target=plan.target,
        baseline=plan.baseline_percent, reassessment=plan.reassessment_percent,
        improvement=None if plan.reassessment_percent is None else round(plan.reassessment_percent-plan.baseline_percent, 1),
        feedback=plan.feedback, closed=plan.closed, version=plan.version,
        student_id=plan.baseline.student_id, subject_id=plan.baseline.exam.subject_id,
        tasks=[dict(id=t.pk, title=t.title, instructions=t.instructions, due=t.due, completed=t.completed, evidence=t.evidence, version=t.version) for t in plan.tasks.all()])


class ImprovementView(ERPAPIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.erp_user['role'] not in ['admin', 'teacher', 'student', 'parent']:
            raise HTTPException(403, 'Academic support is available to students, parents and teaching staff.')

    def teacher_only(self):
        if self.erp_user['role'] not in ['admin', 'teacher']:
            raise HTTPException(403, 'A teacher must review this action.')


class Workspace(ImprovementView):
    def get(self, request):
        classes = queryset_for('classes', self.erp_user).order_by('name', 'year', 'id')
        class_id = request.query_params.get('class_id', '')
        if class_id:
            try:
                class_id = int(class_id)
                if class_id < 1: raise ValueError
            except (ValueError, TypeError):
                raise HTTPException(400, 'Choose a valid class.')
            if not classes.filter(pk=class_id).exists():
                raise HTTPException(404, 'Class not found or unavailable to your account.')
        results = queryset_for('results', self.erp_user).select_related('exam__subject', 'student__school_class').filter(exam__date__lte=timezone.localdate()).order_by('-exam__date', '-id')
        support_plans = plans(self.erp_user)
        if class_id:
            results = results.filter(student__school_class_id=class_id)
            support_plans = support_plans.filter(baseline__student__school_class_id=class_id)
        grouped = {}
        for result in results:
            grouped.setdefault((result.student_id, result.exam.subject_id), []).append(result)
        gaps = []
        for history in grouped.values():
            latest = history[0]; score = percentage(latest)
            previous = percentage(history[1]) if len(history) > 1 else None
            if score < 60 or (previous is not None and previous-score >= 10):
                gaps.append(dict(result_id=latest.pk, student=latest.student.name, subject=latest.exam.subject.name,
                    school_class=str(latest.student.school_class), score=score, previous=previous,
                    reason='Below 60%' if score < 60 else 'Drop of at least 10 percentage points'))
        return Response(dict(gaps=gaps, plans=[present(p) for p in support_plans],
            classes=list(classes.values('id', 'name', 'year')), class_id=class_id or None,
            can_manage=self.erp_user['role'] in ['admin', 'teacher']))


class PlanInput(serializers.Serializer):
    baseline_id = serializers.IntegerField(min_value=1)
    topic = serializers.CharField(max_length=255)
    target = serializers.IntegerField(min_value=1, max_value=100)
    due = serializers.DateField()
    instructions = serializers.CharField(max_length=4000)


class Plans(ImprovementView):
    def post(self, request):
        self.teacher_only()
        data = PlanInput(data=self.object_body(request)); data.is_valid(raise_exception=True); value=data.validated_data
        baseline = get_object_or_404(queryset_for('results', self.erp_user).select_related('exam__subject'), pk=value['baseline_id'])
        if value['due'] <= timezone.localdate() or baseline.exam.date > timezone.localdate() or value['target'] <= percentage(baseline):
            raise HTTPException(400, 'Choose a future review date and a target above the baseline score.')
        try:
            with transaction.atomic():
                plan=ImprovementPlan.objects.create(baseline=baseline, baseline_percent=percentage(baseline), topic=value['topic'], target=value['target'], due=value['due'], teacher=baseline.exam.subject.teacher)
                today=timezone.localdate()
                for title, instructions, due in [
                    ('Revise the learning gap', value['instructions'], today),
                    ('Practice and record your work', 'Complete teacher-assigned questions. Record your answers and the questions you found difficult.', min(today+timedelta(days=2), plan.due)),
                    ('Review mistakes with your teacher', 'Discuss incorrect answers and explain the corrected method. Your teacher will arrange a follow-up exam.', plan.due),
                ]:
                    LearningTask.objects.create(plan=plan, title=title, instructions=instructions, due=due)
                audit(self.erp_user, 'create', 'improvement', plan.pk)
        except IntegrityError:
            raise HTTPException(409, 'An active plan already exists for this baseline.')
        return Response(present(plans(self.erp_user).get(pk=plan.pk)), status=201)


class ReviewInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    feedback = serializers.CharField(max_length=4000)
    reassessment_id = serializers.IntegerField(min_value=1)
    close = serializers.BooleanField(default=False)


class PlanAction(ImprovementView):
    def post(self, request, pk):
        self.teacher_only()
        data=ReviewInput(data=self.object_body(request)); data.is_valid(raise_exception=True); value=data.validated_data
        with transaction.atomic():
            plan=get_object_or_404(plans(self.erp_user).select_for_update(of=('self',)), pk=pk)
            if plan.closed or plan.version != value['version']: raise HTTPException(409, 'Plan changed or is closed. Refresh and try again.')
            result=get_object_or_404(queryset_for('results', self.erp_user).select_related('exam'), pk=value['reassessment_id'])
            if result.student_id != plan.baseline.student_id or result.exam.subject_id != plan.baseline.exam.subject_id or result.exam.date <= plan.baseline.exam.date or result.exam.date > timezone.localdate() or result.created_at <= plan.created_at:
                raise HTTPException(400, 'Select a result recorded after this plan began, from a later exam for the same student and subject.')
            if value['close'] and (plan.tasks.filter(completed=False).exists() or percentage(result) < plan.target):
                raise HTTPException(400, 'Complete all practice tasks and meet the target before closing the plan.')
            plan.reassessment=result; plan.reassessment_percent=percentage(result); plan.feedback=value['feedback']; plan.closed=value['close']; plan.version+=1; plan.save()
            audit(self.erp_user, 'review', 'improvement', plan.pk)
        return Response(present(plans(self.erp_user).get(pk=pk)))


class TaskInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    completed = serializers.BooleanField()
    evidence = serializers.CharField(max_length=4000)


class TaskAction(ImprovementView):
    def post(self, request, pk):
        if self.erp_user['role']=='parent': raise HTTPException(403, 'Parents can view progress; students and teachers record practice.')
        data=TaskInput(data=self.object_body(request)); data.is_valid(raise_exception=True); value=data.validated_data
        with transaction.atomic():
            visible_task=get_object_or_404(LearningTask.objects.filter(plan__in=plans(self.erp_user)), pk=pk)
            plan=ImprovementPlan.objects.select_for_update().get(pk=visible_task.plan_id)
            task=LearningTask.objects.select_for_update().get(pk=pk)
            if plan.closed or task.version != value['version']: raise HTTPException(409, 'Task changed or plan is closed. Refresh and try again.')
            task.completed=value['completed']; task.evidence=value['evidence']; task.version+=1; task.save()
            plan.version+=1; plan.save()
            audit(self.erp_user, 'practice', 'improvement', plan.pk)
        return Response(present(plans(self.erp_user).get(pk=plan.pk)))
