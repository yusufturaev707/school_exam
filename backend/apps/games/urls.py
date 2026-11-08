from django.urls import path

from . import views

# Fixed paths go before `games/<slug>`, otherwise "categories" would be read as a game's slug.
urlpatterns = [
    path("games", views.GameListView.as_view()),
    path("games/categories", views.CategoryListView.as_view()),
    path("games/daily-challenge", views.DailyChallengeView.as_view()),
    path("games/daily-challenge/complete", views.ConfirmDailyChallengeView.as_view()),
    path("games/daily-question", views.DailyQuestionView.as_view()),
    path("games/daily-question/answer", views.AnswerDailyQuestionView.as_view()),
    path("games/sessions/<uuid:session_id>", views.SessionDetailView.as_view()),
    path("games/sessions/<uuid:session_id>/answer", views.AnswerQuestionView.as_view()),
    path("games/sessions/<uuid:session_id>/complete", views.CompleteGameView.as_view()),
    path("games/sessions/<uuid:session_id>/abandon", views.AbandonGameView.as_view()),
    path("games/sessions/<uuid:session_id>/result", views.GameResultView.as_view()),
    path("games/<uuid:game_id>/start", views.StartGameView.as_view()),
    path("games/<slug:slug>", views.GameDetailView.as_view()),
    path("student/games/statistics", views.StatisticsView.as_view()),
    path("student/achievements", views.AchievementListView.as_view()),
]
