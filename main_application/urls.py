from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-dashboard/', views.dashboard , name='dashboard'),
    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/dashboard/cargo-chart/', views.cargo_status_chart, name='cargo_status_chart'),
    path('cargo/', views.cargo_tracking_list, name='cargo_list'),
    path('cargo/<str:cargo_id>/', views.cargo_detail, name='cargo_detail'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/<str:supplier_id>/', views.supplier_detail, name='supplier_detail'),
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/<str:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
    # ==================== CATEGORY URLs ====================
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/', views.category_detail, name='category_detail'),
    path('categories/<int:category_id>/update/', views.category_update, name='category_update'),
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),
    path('categories/<int:category_id>/toggle/', views.category_toggle_status, name='toggle'),

    # ==================== COUNTY URLs ====================
    path('counties/', views.county_list, name='county_list'),
    path('counties/create/', views.county_create, name='county_create'),
    path('counties/<int:county_id>/', views.county_detail, name='county_detail'),
    path('counties/<int:county_id>/update/', views.county_update, name='county_update'),
    path('counties/<int:county_id>/delete/', views.county_delete, name='county_delete'),

    path('analytics/supplier-performance/', views.supplier_performance, name='supplier_performance'),
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/<int:alert_id>/resolve/', views.mark_alert_resolved, name='mark_alert_resolved'),
    path('help/', views.help_page, name='help_page'),
    path('documentation/', views.documentation_page, name='documentation'),
    
 
]