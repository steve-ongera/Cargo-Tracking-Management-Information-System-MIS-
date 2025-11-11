from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from .models import Cargo, Supplier, Warehouse, Alert

def login_view(request):
    """
    Custom login view for Cargo Tracking Management System
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Log the login activity
                messages.success(
                    request, 
                    f'Welcome back, {user.username}! You have successfully logged into the Cargo Tracking System.'
                )
                
                # Redirect to next page or dashboard
                next_page = request.GET.get('next', 'dashboard')
                return redirect(next_page)
            else:
                messages.error(
                    request, 
                    'Invalid username or password. Please try again.'
                )
        else:
            messages.error(
                request, 
                'Please correct the errors below.'
            )
    else:
        form = AuthenticationForm()
    
    return render(request, 'auth/login.html', {
        'form': form,
        'system_name': 'Cargo Tracking MIS',
        'current_year': timezone.now().year
    })

def logout_view(request):
    """
    Custom logout view
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.info(
            request, 
            f'You have been successfully logged out. Goodbye, {username}!'
        )
    
    return redirect('login')


"""
Cargo Tracking Management System - Dashboard Views
File: main_application/views.py
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    Cargo, Supplier, Warehouse, CargoCategory, 
    SupplierPerformance, Alert, CargoStatusHistory
)


@login_required
def dashboard(request):
    """
    Main dashboard view with comprehensive cargo tracking analytics
    """
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # ============================================
    # KEY METRICS
    # ============================================
    
    # Total Active Shipments
    total_active_shipments = Cargo.objects.filter(
        status__in=['DISPATCHED', 'IN_TRANSIT', 'ARRIVED']
    ).count()
    
    # Shipments Delivered This Month
    month_deliveries = Cargo.objects.filter(
        status__in=['RECEIVED', 'STORED'],
        received_date__gte=timezone.now().replace(day=1)
    ).count()
    
    # Total Cargo Value in Transit
    cargo_value_in_transit = Cargo.objects.filter(
        status__in=['DISPATCHED', 'IN_TRANSIT', 'ARRIVED']
    ).aggregate(total=Sum('declared_value'))['total'] or Decimal('0.00')
    
    # Delayed Shipments Count
    delayed_shipments_count = Cargo.objects.filter(is_delayed=True).count()
    
    # Calculate changes (for trend indicators)
    last_month_deliveries = Cargo.objects.filter(
        status__in=['RECEIVED', 'STORED'],
        received_date__gte=timezone.now().replace(day=1) - timedelta(days=30),
        received_date__lt=timezone.now().replace(day=1)
    ).count()
    
    deliveries_change = 0
    if last_month_deliveries > 0:
        deliveries_change = ((month_deliveries - last_month_deliveries) / last_month_deliveries) * 100
    
    # ============================================
    # CARGO STATUS DISTRIBUTION (Donut Chart)
    # ============================================
    
    cargo_status_data = Cargo.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    status_labels = []
    status_values = []
    status_colors = []
    
    status_color_map = {
        'DISPATCHED': '#4e73df',
        'IN_TRANSIT': '#36b9cc',
        'ARRIVED': '#f6c23e',
        'RECEIVED': '#1cc88a',
        'STORED': '#858796',
        'DELAYED': '#e74a3b',
        'CANCELLED': '#d63384',
        'DAMAGED': '#fd7e14'
    }
    
    for item in cargo_status_data:
        status_labels.append(item['status'].replace('_', ' ').title())
        status_values.append(item['count'])
        status_colors.append(status_color_map.get(item['status'], '#858796'))
    
    # ============================================
    # DAILY SHIPMENTS TREND (Last 30 Days - Line Chart)
    # ============================================
    
    shipments_trend_30days = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        
        dispatched_count = Cargo.objects.filter(
            dispatch_date__date=date
        ).count()
        
        delivered_count = Cargo.objects.filter(
            received_date__date=date
        ).count()
        
        shipments_trend_30days.append({
            'date': date.strftime('%b %d'),
            'dispatched': dispatched_count,
            'delivered': delivered_count
        })
    
    # ============================================
    # SUPPLIER PERFORMANCE (Bar Chart)
    # ============================================
    
    top_suppliers = SupplierPerformance.objects.select_related('supplier').filter(
        total_deliveries__gte=1
    ).order_by('-overall_performance_score')[:10]
    
    supplier_labels = []
    supplier_scores = []
    supplier_deliveries = []
    
    for perf in top_suppliers:
        supplier_labels.append(perf.supplier.name[:30])  # Truncate long names
        supplier_scores.append(float(perf.overall_performance_score))
        supplier_deliveries.append(perf.total_deliveries)
    
    # ============================================
    # WAREHOUSE CAPACITY UTILIZATION (Bar Chart)
    # ============================================
    
    warehouses = Warehouse.objects.filter(is_active=True)
    
    warehouse_labels = []
    warehouse_utilization = []
    warehouse_colors = []
    
    for wh in warehouses:
        warehouse_labels.append(wh.name[:25])
        utilization_pct = wh.capacity_utilization_percentage
        warehouse_utilization.append(round(utilization_pct, 2))
        
        # Color based on utilization
        if utilization_pct >= 90:
            warehouse_colors.append('#e74a3b')  # Red - Critical
        elif utilization_pct >= 75:
            warehouse_colors.append('#f6c23e')  # Yellow - Warning
        else:
            warehouse_colors.append('#1cc88a')  # Green - Good
    
    # ============================================
    # CARGO BY CATEGORY (Pie Chart)
    # ============================================
    
    category_data = Cargo.objects.values(
        'category__name'
    ).annotate(
        count=Count('id'),
        total_value=Sum('declared_value')
    ).order_by('-total_value')[:8]
    
    category_labels = []
    category_values = []
    
    for item in category_data:
        category_labels.append(item['category__name'] or 'Uncategorized')
        category_values.append(float(item['total_value'] or 0))
    
    # ============================================
    # TRANSPORT MODE DISTRIBUTION (Donut Chart)
    # ============================================
    
    transport_data = Cargo.objects.values('transport_mode').annotate(
        count=Count('id')
    ).order_by('-count')
    
    transport_labels = []
    transport_values = []
    transport_colors = ['#4e73df', '#1cc88a', '#f6c23e', '#e74a3b', '#36b9cc']
    
    for item in transport_data:
        transport_labels.append(item['transport_mode'].replace('_', ' ').title())
        transport_values.append(item['count'])
    
    # ============================================
    # WEEKLY CARGO VALUE (Bar Chart)
    # ============================================
    
    weekly_data = []
    for i in range(4):
        week_start = today - timedelta(days=(i+1)*7)
        week_end = today - timedelta(days=i*7)
        
        week_value = Cargo.objects.filter(
            dispatch_date__date__gte=week_start,
            dispatch_date__date__lt=week_end
        ).aggregate(total=Sum('declared_value'))['total'] or Decimal('0.00')
        
        weekly_data.insert(0, {
            'week': f'Week {4-i}',
            'value': float(week_value)
        })
    
    # ============================================
    # DELIVERY PERFORMANCE BY PRIORITY (Bar Chart)
    # ============================================
    
    priority_performance = []
    priorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']
    
    for priority in priorities:
        total = Cargo.objects.filter(priority=priority).count()
        on_time = Cargo.objects.filter(
            priority=priority, 
            is_delayed=False,
            status__in=['RECEIVED', 'STORED']
        ).count()
        
        if total > 0:
            on_time_rate = (on_time / total) * 100
        else:
            on_time_rate = 0
            
        priority_performance.append({
            'priority': priority,
            'on_time_rate': round(on_time_rate, 2),
            'total': total
        })
    
    priority_labels = [p['priority'] for p in priority_performance]
    priority_rates = [p['on_time_rate'] for p in priority_performance]
    
    # ============================================
    # COUNTY DISTRIBUTION (Horizontal Bar Chart)
    # ============================================
    
    county_shipments = Cargo.objects.values(
        'warehouse__county__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    county_labels = []
    county_values = []
    
    for item in county_shipments:
        county_labels.append(item['warehouse__county__name'] or 'Unknown')
        county_values.append(item['count'])
    
    # ============================================
    # RECENT CARGO SHIPMENTS (Table)
    # ============================================
    
    recent_cargo = Cargo.objects.select_related(
        'supplier', 'warehouse', 'category'
    ).order_by('-dispatch_date')[:10]
    
    # ============================================
    # DELAYED SHIPMENTS (Table)
    # ============================================
    
    delayed_shipments = Cargo.objects.filter(
        is_delayed=True
    ).select_related('supplier', 'warehouse').order_by('-expected_arrival_date')[:10]
    
    # ============================================
    # ACTIVE ALERTS (Table)
    # ============================================
    
    active_alerts = Alert.objects.filter(
        is_resolved=False
    ).select_related('cargo', 'supplier', 'warehouse').order_by('-created_at')[:8]
    
    # ============================================
    # TOP PERFORMING SUPPLIERS (Table)
    # ============================================
    
    top_suppliers_table = SupplierPerformance.objects.select_related(
        'supplier'
    ).order_by('-overall_performance_score')[:5]
    
    # ============================================
    # AVERAGE DELIVERY TIME BY TRANSPORT MODE (Bar Chart)
    # ============================================
    
    transport_avg_time = Cargo.objects.filter(
        delivery_duration_hours__isnull=False
    ).values('transport_mode').annotate(
        avg_hours=Avg('delivery_duration_hours')
    ).order_by('avg_hours')
    
    transport_time_labels = []
    transport_time_values = []
    
    for item in transport_avg_time:
        transport_time_labels.append(item['transport_mode'].replace('_', ' ').title())
        transport_time_values.append(float(item['avg_hours'] or 0))
    
    # ============================================
    # CONTEXT DATA
    # ============================================
    
    context = {
        # Key Metrics
        'total_active_shipments': total_active_shipments,
        'month_deliveries': month_deliveries,
        'cargo_value_in_transit': cargo_value_in_transit,
        'delayed_shipments_count': delayed_shipments_count,
        'deliveries_change': deliveries_change,
        
        # Cargo Status Distribution
        'status_labels': json.dumps(status_labels),
        'status_values': json.dumps(status_values),
        'status_colors': json.dumps(status_colors),
        
        # Daily Shipments Trend
        'shipments_trend_30days': json.dumps(shipments_trend_30days),
        
        # Supplier Performance
        'supplier_labels': json.dumps(supplier_labels),
        'supplier_scores': json.dumps(supplier_scores),
        'supplier_deliveries': json.dumps(supplier_deliveries),
        
        # Warehouse Capacity
        'warehouse_labels': json.dumps(warehouse_labels),
        'warehouse_utilization': json.dumps(warehouse_utilization),
        'warehouse_colors': json.dumps(warehouse_colors),
        
        # Category Distribution
        'category_labels': json.dumps(category_labels),
        'category_values': json.dumps(category_values),
        
        # Transport Mode
        'transport_labels': json.dumps(transport_labels),
        'transport_values': json.dumps(transport_values),
        'transport_colors': json.dumps(transport_colors),
        
        # Weekly Cargo Value
        'weekly_data': json.dumps(weekly_data),
        
        # Priority Performance
        'priority_labels': json.dumps(priority_labels),
        'priority_rates': json.dumps(priority_rates),
        
        # County Distribution
        'county_labels': json.dumps(county_labels),
        'county_values': json.dumps(county_values),
        
        # Transport Average Time
        'transport_time_labels': json.dumps(transport_time_labels),
        'transport_time_values': json.dumps(transport_time_values),
        
        # Tables
        'recent_cargo': recent_cargo,
        'delayed_shipments': delayed_shipments,
        'active_alerts': active_alerts,
        'top_suppliers_table': top_suppliers_table,
        
        # Additional Stats
        'total_suppliers': Supplier.objects.filter(status='ACTIVE').count(),
        'total_warehouses': Warehouse.objects.filter(is_active=True).count(),
        'total_categories': CargoCategory.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'admin/dashboard.html', context)
