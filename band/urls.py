from django.urls import path

from . import views
from . import helpers

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='band-detail'),
    path('update/<int:pk>/', views.UpdateView.as_view(), name='band-update'),
    path('<int:pk>/members/', views.AllMembersView.as_view(), name='all-members'),

    path('assoc/tfparam/<int:ak>/<str:param>/<str:truefalse>', helpers.set_assoc_tfparam),
    path('assoc/section/<int:ak>/<int:sk>', helpers.set_assoc_section),
]
