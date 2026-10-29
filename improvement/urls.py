from django.urls import path
from .views import Workspace, Plans, PlanAction, TaskAction

urlpatterns = [
    path('', Workspace.as_view()),
    path('plans/', Plans.as_view()),
    path('plans/<int:pk>/', PlanAction.as_view()),
    path('tasks/<int:pk>/', TaskAction.as_view()),
]
