from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='band-detail'),
    path('update/<int:pk>/', views.UpdateView.as_view(), name='band-update'),
]
