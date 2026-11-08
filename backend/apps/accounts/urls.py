from django.urls import path

from . import views

urlpatterns = [
    path("auth/jshshir", views.JshshirLoginView.as_view()),
    path("auth/qr", views.QrLoginView.as_view()),
    path("auth/me", views.MeView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
]
