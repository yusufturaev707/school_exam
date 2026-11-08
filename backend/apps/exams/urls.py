from django.urls import path

from . import views

urlpatterns = [
    path("examinations/available", views.AvailableExamsView.as_view()),
    path("examinations/<uuid:exam_id>/start", views.StartAttemptView.as_view()),
    path("examinations/attempts/<uuid:attempt_id>", views.AttemptDetailView.as_view()),
    path(
        "examinations/attempts/<uuid:attempt_id>/answers/<uuid:question_id>",
        views.SaveAnswerView.as_view(),
    ),
    path("examinations/attempts/<uuid:attempt_id>/submit", views.SubmitAttemptView.as_view()),
    path("student/dashboard", views.DashboardView.as_view()),
    path("student/results", views.ResultListView.as_view()),
    path("student/results/<uuid:result_id>", views.ResultDetailView.as_view()),
]
