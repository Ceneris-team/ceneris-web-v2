from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('lista_insumos/', views.lista_insumos, name='lista_insumos'),
    path('crear_insumo/', views.crear_insumo, name='crear_insumo'),
    path('insumo/<int:insumo_id>/update/', views.update_insumo, name='update_insumo'),path('insumo/<int:pk>/detalle/', views.detalle_insumo, name='detalle_insumo'),
    path('item-insumo/<int:pk>/gestionar-accesorios/', views.gestionar_accesorios, name='gestionar_accesorios'),
    path('item-insumo/<int:pk>/registrar-reparacion/', views.registrar_reparacion, name='registrar_reparacion'),
    path('inventario/notificaciones-calibracion/', views.notificaciones_calibracion, name='notificaciones_calibracion'),   
    path('api/calibrar/<str:model_type>/<int:pk>/', views.api_registrar_calibracion, name='api_registrar_calibracion'),
    path('api/item-insumo/<int:pk>/delete/', views.api_delete_item_insumo, name='api_delete_item_insumo'),
    path('api/insumos/search/', views.search_insumos, name='search_insumos'),
    path('api/asignacion/<int:pk>/', views.api_get_asignacion_data, name='api_get_asignacion_data'),
    path('api/asignacion/<int:pk>/devolver/', views.api_devolver_insumo, name='api_devolver_insumo'),
    path('api/insumo/<int:insumo_id>/items/', views.api_get_items_for_insumo, name='api_get_items_for_insumo'),
    path('api/accesorio/<int:pk>/delete/', views.api_delete_accesorio, name='api_delete_accesorio'),
]