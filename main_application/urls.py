from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-dashboard/', views.dashboard , name='dashboard'),

    path('api/dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/dashboard/cargo-chart/', views.cargo_status_chart, name='cargo_status_chart'),
    
    # Cargo Tracking
    path('cargo/', views.cargo_tracking_list, name='cargo_list'),
    path('cargo/<str:cargo_id>/', views.cargo_detail, name='cargo_detail'),
    
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/<str:supplier_id>/', views.supplier_detail, name='supplier_detail'),
    
    # Warehouses
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/<str:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    
    # Counties
    path('counties/', views.county_list, name='county_list'),
    
    # Analytics
    path('analytics/supplier-performance/', views.supplier_performance, name='supplier_performance'),
    
    # Reports
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    
    # Alerts
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/<int:alert_id>/resolve/', views.mark_alert_resolved, name='mark_alert_resolved'),
    
    # Help & Documentation
    path('help/', views.help_page, name='help_page'),
    path('documentation/', views.documentation_page, name='documentation'),
    
 
]