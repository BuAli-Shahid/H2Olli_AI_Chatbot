"""
URL configuration for chatbot_project project.
"""
from django.urls import path, include

urlpatterns = [
    path('', include('chatbot.urls')),
] 