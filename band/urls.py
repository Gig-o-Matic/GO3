from django.urls import path

from . import views
from . import helpers

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='band-detail'),
    path('update/<int:pk>/', views.UpdateView.as_view(), name='band-update'),
    path('<int:pk>/members/', views.AllMembersView.as_view(), name='all-members'),

    path('assoc/occasional/<int:ak>/<str:truefalse>', helpers.set_occasional),
]
