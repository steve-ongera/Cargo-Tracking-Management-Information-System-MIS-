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
Cargo Tracking Management System - Dashboard Views (FIXED)
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


# Custom JSON encoder for Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


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
        warehouse_utilization.append(round(float(utilization_pct), 2))
        
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
    # CONTEXT DATA - Using Custom JSON Encoder
    # ============================================
    
    context = {
        # Key Metrics
        'total_active_shipments': total_active_shipments,
        'month_deliveries': month_deliveries,
        'cargo_value_in_transit': cargo_value_in_transit,
        'delayed_shipments_count': delayed_shipments_count,
        'deliveries_change': deliveries_change,
        
        # Cargo Status Distribution
        'status_labels': json.dumps(status_labels, cls=DecimalEncoder),
        'status_values': json.dumps(status_values, cls=DecimalEncoder),
        'status_colors': json.dumps(status_colors, cls=DecimalEncoder),
        
        # Daily Shipments Trend
        'shipments_trend_30days': json.dumps(shipments_trend_30days, cls=DecimalEncoder),
        
        # Supplier Performance
        'supplier_labels': json.dumps(supplier_labels, cls=DecimalEncoder),
        'supplier_scores': json.dumps(supplier_scores, cls=DecimalEncoder),
        'supplier_deliveries': json.dumps(supplier_deliveries, cls=DecimalEncoder),
        
        # Warehouse Capacity
        'warehouse_labels': json.dumps(warehouse_labels, cls=DecimalEncoder),
        'warehouse_utilization': json.dumps(warehouse_utilization, cls=DecimalEncoder),
        'warehouse_colors': json.dumps(warehouse_colors, cls=DecimalEncoder),
        
        # Category Distribution
        'category_labels': json.dumps(category_labels, cls=DecimalEncoder),
        'category_values': json.dumps(category_values, cls=DecimalEncoder),
        
        # Transport Mode
        'transport_labels': json.dumps(transport_labels, cls=DecimalEncoder),
        'transport_values': json.dumps(transport_values, cls=DecimalEncoder),
        'transport_colors': json.dumps(transport_colors, cls=DecimalEncoder),
        
        # Weekly Cargo Value
        'weekly_data': json.dumps(weekly_data, cls=DecimalEncoder),
        
        # Priority Performance
        'priority_labels': json.dumps(priority_labels, cls=DecimalEncoder),
        'priority_rates': json.dumps(priority_rates, cls=DecimalEncoder),
        
        # County Distribution
        'county_labels': json.dumps(county_labels, cls=DecimalEncoder),
        'county_values': json.dumps(county_values, cls=DecimalEncoder),
        
        # Transport Average Time
        'transport_time_labels': json.dumps(transport_time_labels, cls=DecimalEncoder),
        'transport_time_values': json.dumps(transport_time_values, cls=DecimalEncoder),
        
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


# views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from .models import (
    Cargo, Supplier, Warehouse, CargoCategory, 
    County, SupplierPerformance, Alert, Report
)
from django.core.paginator import Paginator
from django.http import JsonResponse
import json


"""
Enhanced Cargo Tracking Views with Geographical Simulation
Includes real-time tracking, route visualization, and interactive maps
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
import json
from decimal import Decimal


# Kenya County Coordinates (Major towns/cities)
KENYA_COORDINATES = {
    'Nairobi': {'lat': -1.2921, 'lng': 36.8219},
    'Mombasa': {'lat': -4.0435, 'lng': 39.6682},
    'Kisumu': {'lat': -0.0917, 'lng': 34.7680},
    'Nakuru': {'lat': -0.3031, 'lng': 36.0800},
    'Eldoret': {'lat': 0.5143, 'lng': 35.2698},
    'Thika': {'lat': -1.0332, 'lng': 37.0693},
    'Malindi': {'lat': -3.2167, 'lng': 40.1167},
    'Kitale': {'lat': 1.0167, 'lng': 35.0000},
    'Garissa': {'lat': -0.4536, 'lng': 39.6401},
    'Kakamega': {'lat': 0.2827, 'lng': 34.7519},
    'Nyeri': {'lat': -0.4167, 'lng': 36.9500},
    'Machakos': {'lat': -1.5177, 'lng': 37.2634},
    'Meru': {'lat': 0.0469, 'lng': 37.6556},
    'Kericho': {'lat': -0.3676, 'lng': 35.2839},
    'Naivasha': {'lat': -0.7167, 'lng': 36.4333},
}


def get_county_coordinates(county_name, town_city):
    """Get coordinates for a given location"""
    # Try to match town/city first
    if town_city in KENYA_COORDINATES:
        return KENYA_COORDINATES[town_city]
    
    # Try to match county name
    for location, coords in KENYA_COORDINATES.items():
        if location.lower() in county_name.lower():
            return coords
    
    # Default to Nairobi if not found
    return KENYA_COORDINATES['Nairobi']


def calculate_route_progress(cargo):
    """Calculate route progress percentage and intermediate points"""
    if not cargo.dispatch_date or not cargo.expected_arrival_date:
        return 0, []
    
    now = timezone.now()
    total_duration = (cargo.expected_arrival_date - cargo.dispatch_date).total_seconds()
    
    if cargo.actual_arrival_date:
        # Cargo has arrived
        progress = 100
        elapsed = (cargo.actual_arrival_date - cargo.dispatch_date).total_seconds()
    else:
        elapsed = (now - cargo.dispatch_date).total_seconds()
        progress = min((elapsed / total_duration) * 100, 100) if total_duration > 0 else 0
    
    # Generate intermediate waypoints for animation
    waypoints = []
    num_waypoints = 5
    
    for i in range(num_waypoints + 1):
        waypoint_progress = (i / num_waypoints) * 100
        waypoints.append({
            'progress': waypoint_progress,
            'reached': waypoint_progress <= progress
        })
    
    return round(progress, 2), waypoints


def simulate_cargo_position(cargo, supplier_coords, warehouse_coords):
    """Simulate current cargo position based on progress"""
    progress, _ = calculate_route_progress(cargo)
    progress_ratio = progress / 100
    
    # Linear interpolation between supplier and warehouse
    current_lat = supplier_coords['lat'] + (warehouse_coords['lat'] - supplier_coords['lat']) * progress_ratio
    current_lng = supplier_coords['lng'] + (warehouse_coords['lng'] - supplier_coords['lng']) * progress_ratio
    
    return {
        'lat': round(current_lat, 6),
        'lng': round(current_lng, 6),
        'progress': progress
    }


@login_required
def cargo_tracking_list(request):
    """Enhanced list view with geographical tracking"""
    cargos = Cargo.objects.select_related(
        'supplier', 'supplier__county', 'warehouse', 'warehouse__county', 'category'
    ).order_by('-dispatch_date')
    
    # Filters
    status_filter = request.GET.get('status')
    supplier_filter = request.GET.get('supplier')
    warehouse_filter = request.GET.get('warehouse')
    priority_filter = request.GET.get('priority')
    search_query = request.GET.get('search')
    
    if status_filter:
        cargos = cargos.filter(status=status_filter)
    if supplier_filter:
        cargos = cargos.filter(supplier_id=supplier_filter)
    if warehouse_filter:
        cargos = cargos.filter(warehouse_id=warehouse_filter)
    if priority_filter:
        cargos = cargos.filter(priority=priority_filter)
    if search_query:
        cargos = cargos.filter(
            Q(cargo_id__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tracking_number__icontains=search_query)
        )
    
    # Prepare map data for active shipments
    active_shipments_map_data = []
    active_shipments = cargos.filter(status__in=['DISPATCHED', 'IN_TRANSIT'])[:50]
    
    for cargo in active_shipments:
        supplier_coords = get_county_coordinates(
            cargo.supplier.county.name, 
            cargo.supplier.town_city
        )
        warehouse_coords = get_county_coordinates(
            cargo.warehouse.county.name,
            cargo.warehouse.town_city
        )
        
        progress, waypoints = calculate_route_progress(cargo)
        current_position = simulate_cargo_position(cargo, supplier_coords, warehouse_coords)
        
        active_shipments_map_data.append({
            'cargo_id': cargo.cargo_id,
            'description': cargo.description[:50],
            'supplier': {
                'name': cargo.supplier.name,
                'coords': supplier_coords
            },
            'warehouse': {
                'name': cargo.warehouse.name,
                'coords': warehouse_coords
            },
            'current_position': current_position,
            'progress': progress,
            'status': cargo.status,
            'priority': cargo.priority,
            'transport_mode': cargo.transport_mode,
            'vehicle': cargo.vehicle_registration or 'N/A',
            'dispatch_date': cargo.dispatch_date.strftime('%Y-%m-%d %H:%M'),
            'expected_arrival': cargo.expected_arrival_date.strftime('%Y-%m-%d %H:%M'),
        })
    
    # Pagination
    paginator = Paginator(cargos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    suppliers = Supplier.objects.filter(status='ACTIVE').order_by('name')
    warehouses = Warehouse.objects.filter(is_active=True).order_by('name')
    
    # Statistics
    total_active = cargos.filter(status__in=['DISPATCHED', 'IN_TRANSIT']).count()
    total_delayed = cargos.filter(is_delayed=True, status__in=['DISPATCHED', 'IN_TRANSIT']).count()
    total_value = cargos.filter(status__in=['DISPATCHED', 'IN_TRANSIT']).aggregate(
        Sum('declared_value')
    )['declared_value__sum'] or 0
    
    context = {
        'page_obj': page_obj,
        'suppliers': suppliers,
        'warehouses': warehouses,
        'status_choices': Cargo.STATUS_CHOICES,
        'priority_choices': Cargo.PRIORITY_CHOICES,
        'current_filters': {
            'status': status_filter,
            'supplier': supplier_filter,
            'warehouse': warehouse_filter,
            'priority': priority_filter,
            'search': search_query,
        },
        'active_shipments_map_data': json.dumps(active_shipments_map_data),
        'stats': {
            'total_active': total_active,
            'total_delayed': total_delayed,
            'total_value': total_value,
        },
        'kenya_center': {'lat': -1.2921, 'lng': 36.8219},  # Nairobi
    }
    
    return render(request, 'cargo/tracking_list.html', context)


@login_required
def cargo_detail(request, cargo_id):
    """Enhanced detail view with real-time tracking"""
    cargo = get_object_or_404(
        Cargo.objects.select_related(
            'supplier', 'supplier__county',
            'warehouse', 'warehouse__county',
            'category', 'created_by'
        ).prefetch_related('status_history', 'alerts'),
        cargo_id=cargo_id
    )
    
    # Get coordinates
    supplier_coords = get_county_coordinates(
        cargo.supplier.county.name,
        cargo.supplier.town_city
    )
    warehouse_coords = get_county_coordinates(
        cargo.warehouse.county.name,
        cargo.warehouse.town_city
    )
    
    # Calculate progress and position
    progress, waypoints = calculate_route_progress(cargo)
    current_position = simulate_cargo_position(cargo, supplier_coords, warehouse_coords)
    
    # Status history
    status_history = cargo.status_history.select_related('created_by').order_by('-created_at')
    
    # Related alerts
    related_alerts = cargo.alerts.filter(is_resolved=False).order_by('-created_at')
    
    # Calculate delivery metrics
    delivery_metrics = {}
    if cargo.actual_arrival_date:
        actual_duration = (cargo.actual_arrival_date - cargo.dispatch_date).total_seconds() / 3600
        expected_duration = (cargo.expected_arrival_date - cargo.dispatch_date).total_seconds() / 3600
        delivery_metrics['actual_hours'] = round(actual_duration, 2)
        delivery_metrics['expected_hours'] = round(expected_duration, 2)
        delivery_metrics['variance_hours'] = round(actual_duration - expected_duration, 2)
        delivery_metrics['on_time'] = actual_duration <= expected_duration
    else:
        elapsed = (timezone.now() - cargo.dispatch_date).total_seconds() / 3600
        expected_duration = (cargo.expected_arrival_date - cargo.dispatch_date).total_seconds() / 3600
        delivery_metrics['elapsed_hours'] = round(elapsed, 2)
        delivery_metrics['expected_hours'] = round(expected_duration, 2)
        delivery_metrics['remaining_hours'] = round(max(expected_duration - elapsed, 0), 2)
    
    # Related shipments from same supplier
    related_shipments = Cargo.objects.filter(
        supplier=cargo.supplier
    ).exclude(cargo_id=cargo_id).select_related('warehouse')[:5]
    
    # Prepare tracking data for map
    tracking_data = {
        'cargo_id': cargo.cargo_id,
        'description': cargo.description,
        'supplier': {
            'name': cargo.supplier.name,
            'address': cargo.supplier.physical_address,
            'coords': supplier_coords,
            'phone': cargo.supplier.phone_number,
        },
        'warehouse': {
            'name': cargo.warehouse.name,
            'address': cargo.warehouse.physical_address,
            'coords': warehouse_coords,
            'manager': cargo.warehouse.manager_name,
        },
        'current_position': current_position,
        'progress': progress,
        'waypoints': waypoints,
        'status': cargo.status,
        'priority': cargo.priority,
        'transport_mode': cargo.get_transport_mode_display(),
        'vehicle': cargo.vehicle_registration or 'Not Assigned',
        'driver': cargo.driver_name or 'Not Assigned',
        'driver_phone': cargo.driver_phone or 'N/A',
        'dispatch_date': cargo.dispatch_date.strftime('%Y-%m-%d %H:%M'),
        'expected_arrival': cargo.expected_arrival_date.strftime('%Y-%m-%d %H:%M'),
        'actual_arrival': cargo.actual_arrival_date.strftime('%Y-%m-%d %H:%M') if cargo.actual_arrival_date else None,
    }
    
    context = {
        'cargo': cargo,
        'status_history': status_history,
        'related_alerts': related_alerts,
        'delivery_metrics': delivery_metrics,
        'related_shipments': related_shipments,
        'tracking_data': json.dumps(tracking_data),
        'progress': progress,
    }
    
    return render(request, 'cargo/detail.html', context)


@login_required
def supplier_list(request):
    """List all suppliers with filtering"""
    suppliers = Supplier.objects.select_related('county').prefetch_related('performance')
    
    # Filters
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    county_filter = request.GET.get('county')
    
    if status_filter:
        suppliers = suppliers.filter(status=status_filter)
    if type_filter:
        suppliers = suppliers.filter(supplier_type=type_filter)
    if county_filter:
        suppliers = suppliers.filter(county_id=county_filter)
    
    # Pagination
    paginator = Paginator(suppliers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    counties = County.objects.all()
    
    context = {
        'page_obj': page_obj,
        'counties': counties,
        'status_choices': Supplier.STATUS_CHOICES,
        'type_choices': Supplier.SUPPLIER_TYPE_CHOICES,
        'current_filters': {
            'status': status_filter,
            'type': type_filter,
            'county': county_filter,
        }
    }
    
    return render(request, 'suppliers/list.html', context)


@login_required
def supplier_detail(request, supplier_id):
    """Detailed view of a supplier with performance metrics"""
    supplier = get_object_or_404(
        Supplier.objects.select_related('county', 'performance'),
        supplier_id=supplier_id
    )
    
    # Get recent cargo shipments
    recent_cargos = Cargo.objects.filter(
        supplier=supplier
    ).order_by('-dispatch_date')[:10]
    
    # Performance statistics
    performance_stats = {
        'total_shipments': recent_cargos.count(),
        'on_time_rate': supplier.reliability_score,
        'avg_delivery_time': supplier.performance.average_delivery_time_hours if hasattr(supplier, 'performance') else 0,
    }
    
    context = {
        'supplier': supplier,
        'recent_cargos': recent_cargos,
        'performance_stats': performance_stats,
    }
    
    return render(request, 'suppliers/detail.html', context)


@login_required
def warehouse_list(request):
    """List all warehouses"""
    warehouses = Warehouse.objects.select_related('county').filter(is_active=True)
    
    # Calculate utilization for each warehouse
    for warehouse in warehouses:
        warehouse.utilization_percentage = warehouse.capacity_utilization_percentage
    
    context = {
        'warehouses': warehouses,
    }
    
    return render(request, 'warehouses/list.html', context)


@login_required
def warehouse_detail(request, warehouse_id):
    """Detailed view of a warehouse"""
    warehouse = get_object_or_404(
        Warehouse.objects.select_related('county'),
        warehouse_id=warehouse_id
    )
    
    # Get current cargo in warehouse
    current_cargos = Cargo.objects.filter(
        warehouse=warehouse,
        status__in=['RECEIVED', 'STORED']
    ).select_related('supplier', 'category')
    
    # Get recent arrivals
    recent_arrivals = Cargo.objects.filter(
        warehouse=warehouse
    ).order_by('-actual_arrival_date')[:10]
    
    context = {
        'warehouse': warehouse,
        'current_cargos': current_cargos,
        'recent_arrivals': recent_arrivals,
        'utilization_percentage': warehouse.capacity_utilization_percentage,
    }
    
    return render(request, 'warehouses/detail.html', context)


@login_required
def category_list(request):
    """List all cargo categories"""
    categories = CargoCategory.objects.filter(is_active=True).annotate(
        total_cargos=Count('cargos')
    )
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'categories/list.html', context)


@login_required
def county_list(request):
    """List all counties with supplier counts"""
    counties = County.objects.annotate(
        supplier_count=Count('supplier'),
        warehouse_count=Count('warehouse')
    ).order_by('name')
    
    context = {
        'counties': counties,
    }
    
    return render(request, 'counties/list.html', context)

from django.db.models import Avg
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json

import json
from decimal import Decimal

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


@login_required
def supplier_performance(request):
    """Supplier performance analytics dashboard with dynamic graphs"""
    performances = SupplierPerformance.objects.select_related('supplier').order_by(
        '-overall_performance_score'
    )

    total_suppliers = performances.count()
    avg_performance_score = performances.aggregate(
        avg_score=Avg('overall_performance_score')
    )['avg_score'] or 0

    # Top and low performers
    top_performers = performances.filter(overall_performance_score__gte=80)[:10]
    need_improvement = performances.filter(overall_performance_score__lt=60)[:10]

    # Chart 1: Score Distribution
    score_ranges = [
        {'range': '90-100', 'count': performances.filter(overall_performance_score__gte=90).count()},
        {'range': '80-89', 'count': performances.filter(overall_performance_score__gte=80, overall_performance_score__lt=90).count()},
        {'range': '70-79', 'count': performances.filter(overall_performance_score__gte=70, overall_performance_score__lt=80).count()},
        {'range': '60-69', 'count': performances.filter(overall_performance_score__gte=60, overall_performance_score__lt=70).count()},
        {'range': 'Below 60', 'count': performances.filter(overall_performance_score__lt=60).count()},
    ]

    # Chart 2: Top 10 Suppliers
    top_10_suppliers = performances[:10]
    top_suppliers_data = {
        'labels': [p.supplier.name for p in top_10_suppliers],
        'scores': [float(p.overall_performance_score) for p in top_10_suppliers]
    }

    # Chart 3: Quality vs Delivery Performance Scatter
    scatter_data = []
    quality_scores = []
    delivery_scores = []

    for perf in performances[:50]:
        total = perf.total_deliveries or 1
        good_quality = total - (perf.damaged_cargo_count + perf.quality_issues_count)
        quality_score = (good_quality / total) * 100
        delivery_performance = float(perf.on_time_delivery_rate or 0)

        scatter_data.append({
            'x': round(quality_score, 2),
            'y': round(delivery_performance, 2),
            'label': perf.supplier.name,
            'overall': float(perf.overall_performance_score)
        })

        quality_scores.append(quality_score)
        delivery_scores.append(delivery_performance)

    # Chart 4: Average Metrics Comparison (computed manually)
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    avg_delivery = sum(delivery_scores) / len(delivery_scores) if delivery_scores else 0

    avg_metrics = {
        'Quality Score': round(avg_quality, 2),
        'Delivery Performance': round(avg_delivery, 2),
        'Responsiveness': 0,  # Placeholder for future metric
        'Cost Competitiveness': 0,  # Placeholder
        'Overall Score': round(avg_performance_score, 2)
    }

    # Chart 5: Performance Trend (last 6 months) — FIXED FIELD NAME
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_performance = SupplierPerformance.objects.filter(
        last_calculated__gte=six_months_ago  # <-- changed from last_evaluation_date
    ).annotate(
        month=TruncMonth('last_calculated')  # <-- also changed
    ).values('month').annotate(
        avg_score=Avg('overall_performance_score')
    ).order_by('month')

    trend_data = {
        'labels': [mp['month'].strftime('%b %Y') for mp in monthly_performance],
        'scores': [float(mp['avg_score']) for mp in monthly_performance]
    }

    context = {
        'performances': performances,
        'total_suppliers': total_suppliers,
        'avg_performance_score': round(avg_performance_score, 2),
        'top_performers': top_performers,
        'need_improvement': need_improvement,
        'score_ranges': json.dumps(score_ranges, default=decimal_to_float),
        'top_suppliers_data': json.dumps(top_suppliers_data, default=decimal_to_float),
        'scatter_data': json.dumps(scatter_data, default=decimal_to_float),
        'avg_metrics': json.dumps(avg_metrics, default=decimal_to_float),
        'trend_data': json.dumps(trend_data, default=decimal_to_float),

    }

    return render(request, 'analytics/supplier_performance.html', context)


@login_required
def reports_list(request):
    """List all generated reports with analytics charts."""
    reports = Report.objects.all().order_by('-created_at')

    # --- Chart 1: Reports by Type ---
    reports_by_type = (
        Report.objects.values('report_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    type_chart_data = {
        'labels': [r['report_type'].replace('_', ' ').title() for r in reports_by_type],
        'counts': [r['count'] for r in reports_by_type],
    }

    # --- Chart 2: Reports Created Over the Last 12 Months ---
    twelve_months_ago = datetime.now() - timedelta(days=365)
    monthly_reports = (
        Report.objects.filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    timeline_data = {
        'labels': [mr['month'].strftime('%b %Y') for mr in monthly_reports],
        'counts': [mr['count'] for mr in monthly_reports],
    }

    # --- Simple Stats ---
    total_reports = reports.count()
    supplier_reports = reports.filter(report_type='SUPPLIER_PERFORMANCE').count()
    cargo_reports = reports.filter(report_type='CARGO_MOVEMENT').count()
    monthly_reports_count = reports.filter(report_type='MONTHLY_SUMMARY').count()

    # Convert to JSON safely
    def safe_json(data):
        """Converts Decimal and datetime safely to JSON"""
        def default(o):
            import decimal, datetime
            if isinstance(o, decimal.Decimal):
                return float(o)
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            return str(o)
        return json.dumps(data, default=default)

    context = {
        'reports': reports,
        'total_reports': total_reports,
        'supplier_reports': supplier_reports,
        'cargo_reports': cargo_reports,
        'monthly_reports_count': monthly_reports_count,
        'type_chart_data': safe_json(type_chart_data),
        'timeline_data': safe_json(timeline_data),
    }

    return render(request, 'reports/list.html', context)


@login_required
def report_detail(request, report_id):
    """View a specific report with detailed analytics"""
    report = get_object_or_404(Report, id=report_id)
    context = {'report': report}

    def safe_json(data):
        """Helper to safely convert Decimal to JSON"""
        def default(o):
            import decimal, datetime
            if isinstance(o, decimal.Decimal):
                return float(o)
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            return str(o)
        return json.dumps(data, default=default)

    # --- Supplier Performance Report ---
    if report.report_type == 'SUPPLIER_PERFORMANCE':
        performances = (
            SupplierPerformance.objects.select_related('supplier')
            .order_by('-overall_performance_score')[:20]
        )
        performance_chart = {
            'labels': [p.supplier.name for p in performances],
            'scores': [float(p.overall_performance_score) for p in performances],
        }
        context['performance_chart'] = safe_json(performance_chart)

    # --- Cargo Movement Report ---
    elif report.report_type == 'CARGO_MOVEMENT':
        from .models import Cargo
        cargos = Cargo.objects.order_by('-dispatch_date')[:20]
        cargo_chart = {
            'labels': [c.cargo_id for c in cargos],
            'weights': [float(c.weight_kg) for c in cargos],
        }
        context['cargo_chart'] = safe_json(cargo_chart)

    # --- Inventory Summary Report ---
    elif report.report_type == 'INVENTORY_SUMMARY':
        from .models import Inventory
        items = Inventory.objects.select_related('product').order_by('-quantity')[:15]
        inventory_chart = {
            'labels': [item.product.name for item in items],
            'quantities': [item.quantity for item in items],
        }
        context['inventory_chart'] = safe_json(inventory_chart)

    # --- Delivery Analysis Report ---
    elif report.report_type == 'DELIVERY_ANALYSIS':
        from .models import Cargo
        delayed = Cargo.objects.filter(is_delayed=True).count()
        on_time = Cargo.objects.filter(is_delayed=False).count()
        delivery_chart = {
            'labels': ['On-Time', 'Delayed'],
            'counts': [on_time, delayed],
        }
        context['delivery_chart'] = safe_json(delivery_chart)

    return render(request, 'reports/detail.html', context)

@login_required
def alerts_list(request):
    """List all system alerts"""
    alerts = Alert.objects.select_related(
        'cargo', 'supplier', 'warehouse'
    ).order_by('-created_at')
    
    # Filters
    severity_filter = request.GET.get('severity')
    type_filter = request.GET.get('type')
    resolved_filter = request.GET.get('resolved')
    
    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)
    if type_filter:
        alerts = alerts.filter(alert_type=type_filter)
    if resolved_filter == 'true':
        alerts = alerts.filter(is_resolved=True)
    elif resolved_filter == 'false':
        alerts = alerts.filter(is_resolved=False)
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'severity_choices': Alert.SEVERITY_CHOICES,
        'type_choices': Alert.ALERT_TYPE_CHOICES,
        'current_filters': {
            'severity': severity_filter,
            'type': type_filter,
            'resolved': resolved_filter,
        }
    }
    
    return render(request, 'alerts/list.html', context)


@login_required
def mark_alert_resolved(request, alert_id):
    """Mark an alert as resolved"""
    if request.method == 'POST':
        alert = get_object_or_404(Alert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.resolution_notes = request.POST.get('resolution_notes', '')
        alert.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
def help_page(request):
    """Help and documentation page"""
    return render(request, 'help/index.html')


@login_required
def documentation_page(request):
    """System documentation"""
    return render(request, 'help/documentation.html')


# API Views for Dashboard Widgets
@login_required
def dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    # Calculate various statistics
    total_cargos = Cargo.objects.count()
    delayed_cargos = Cargo.objects.filter(is_delayed=True).count()
    active_suppliers = Supplier.objects.filter(status='ACTIVE').count()
    total_warehouses = Warehouse.objects.filter(is_active=True).count()
    
    # Recent activity
    recent_cargos_count = Cargo.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # High priority cargo
    high_priority_cargos = Cargo.objects.filter(
        priority__in=['HIGH', 'URGENT'],
        status__in=['DISPATCHED', 'IN_TRANSIT']
    ).count()
    
    stats = {
        'total_cargos': total_cargos,
        'delayed_cargos': delayed_cargos,
        'active_suppliers': active_suppliers,
        'total_warehouses': total_warehouses,
        'recent_activity': recent_cargos_count,
        'high_priority': high_priority_cargos,
    }
    
    return JsonResponse(stats)


@login_required
def cargo_status_chart(request):
    """API endpoint for cargo status chart data"""
    status_counts = Cargo.objects.values('status').annotate(
        count=Count('id')
    )
    
    chart_data = {
        'labels': [item['status'] for item in status_counts],
        'data': [item['count'] for item in status_counts],
    }
    
    return JsonResponse(chart_data)
