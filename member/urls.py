from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='member-detail'),
    path('<int:pk>/update', views.UpdateView.as_view(), name='member-update'),
    path('<int:pk>/preferences/update/', views.PreferencesUpdateView.as_view(), name='member-prefs-update'),
]