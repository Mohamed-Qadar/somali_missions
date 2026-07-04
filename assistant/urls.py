from django.urls import path

from . import views

urlpatterns = [
    path('ask/', views.ask_assistant_view, name='ask_assistant'),
]
