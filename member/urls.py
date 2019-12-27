from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='member-detail'),
    path('update/<int:pk>/', views.UpdateView.as_view(), name='member-update'),
    path('preferences/update/<int:pk>/', views.PreferencesUpdateView.as_view(), name='member-prefs-update'),
]