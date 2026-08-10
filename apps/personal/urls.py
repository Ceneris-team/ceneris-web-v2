from django.urls import path 
from . import views

app_name = 'personal'

urlpatterns = [
    path('lista_personal/', views.lista_personal, name='lista_personal'),
    path('personal/crear/', views.crear_personal, name='crear_personal'),
    path('api/personal/search/', views.search_personal, name='api_search_personal'),
    path('api/subtarea/<int:subtarea_id>/unassign/<int:personal_id>/', views.api_unassign_personal, name='api_unassign_personal'),
    path('api/personal/<int:pk>/delete/', views.api_delete_personal, name='api_delete_personal'),
]