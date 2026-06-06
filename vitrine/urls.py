from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("mentions-legales/", views.MentionsLegalesView.as_view(), name="mentions_legales"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("healthz/", views.healthz, name="healthz"),
]
