from django.urls import path
from . import views

app_name = 'proyectos'

urlpatterns = [
    path('', views.index_view, name='index'), 
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('proyectos/', views.lista_proyectos, name='lista_proyectos'),
    path('crear_proyecto/', views.crear_proyecto, name='crear_proyecto'),
    path('proyecto/<int:pk>/', views.detalle_proyecto, name='detalle_proyecto'),
    path('proyecto/<int:pk>/editar/', views.editar_proyecto, name='editar_proyecto'),
    path('api/proyectos/search/', views.search_proyectos, name='api_search_proyectos'),
    path('proyecto/<int:proyecto_id>/asignar-tareas/', views.asignar_tareas, name='asignar_tareas'),
    path('proyecto/<int:proyecto_id>/anadir-tareas/', views.anadir_tareas, name='anadir_tareas'),
    path('api/subtarea/<int:pk>/', views.api_get_subtarea_data, name='api_get_subtarea_data'),
    path('api/subtarea/<int:pk>/update/', views.api_update_subtarea, name='api_update_subtarea'),
    path('api/subtarea/<int:pk>/delete/', views.api_delete_subtarea, name='api_delete_subtarea'),
    path('api/subtarea/<int:pk>/toggle-complete/', views.api_toggle_complete_subtarea, name='api_toggle_complete_subtarea'),
    path('subtarea/<int:pk>/detalle/', views.detalle_subtarea, name='detalle_subtarea'),
    path('api/proyecto/<int:pk>/delete/', views.api_delete_proyecto, name='api_delete_proyecto'),
    path('seguimiento/', views.vista_seguimiento, name='vista_seguimiento'),
    path('proyecto/<int:pk>/exportar-excel/', views.exportar_proyecto_excel, name='exportar_proyecto_excel'),
]