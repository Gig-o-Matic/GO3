from django.urls import path

from . import views
from . import helpers

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='band-detail'),
    path('<int:pk>/update', views.UpdateView.as_view(), name='band-update'),
    path('<int:pk>/members/', views.AllMembersView.as_view(), name='all-members'),
    path('<int:pk>/section/<int:sk>', views.SectionMembersView.as_view(), name='section-members'),

    path('assoc/<int:ak>/tfparam/<str:param>/<str:truefalse>', helpers.set_assoc_tfparam, name='assoc-tfparam'),
    path('assoc/<int:ak>/color/<int:colorindex>', helpers.set_assoc_color, name='assoc-color'),
    path('assoc/<int:ak>/section/<int:sk>', helpers.set_assoc_section, name='assoc-section'),
    path('assoc/<int:ak>/delete', helpers.delete_assoc, name='assoc-delete'),
]
