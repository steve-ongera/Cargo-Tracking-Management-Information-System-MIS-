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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import CargoCategory, County, Supplier, Warehouse, Cargo
from .forms import CargoCategoryForm, CountyForm  # We'll create these forms
import json


# ==================== CARGO CATEGORY VIEWS ====================

@login_required
def category_list(request):
    """List all cargo categories with analytics"""
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Base queryset
    categories = CargoCategory.objects.annotate(
        total_cargos=Count('cargos'),
        active_cargos=Count('cargos', filter=Q(cargos__status__in=['DISPATCHED', 'IN_TRANSIT', 'ARRIVED'])),
        total_value=Count('cargos__declared_value')
    )
    
    # Apply search filter
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        categories = categories.filter(is_active=(status_filter == 'active'))
    
    # Order by
    order_by = request.GET.get('order_by', '-total_cargos')
    categories = categories.order_by(order_by)
    
    # Pagination
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    categories_page = paginator.get_page(page_number)
    
    # Statistics
    total_categories = CargoCategory.objects.count()
    active_categories = CargoCategory.objects.filter(is_active=True).count()
    special_handling_categories = CargoCategory.objects.filter(requires_special_handling=True).count()
    
    # Chart data: Categories by cargo count
    top_categories = CargoCategory.objects.annotate(
        cargo_count=Count('cargos')
    ).order_by('-cargo_count')[:10]
    
    category_chart_data = {
        'labels': [cat.name for cat in top_categories],
        'data': [cat.cargo_count for cat in top_categories]
    }
    
    # Chart data: Special handling vs regular
    special_handling_data = {
        'labels': ['Special Handling', 'Regular'],
        'data': [
            special_handling_categories,
            active_categories - special_handling_categories
        ]
    }
    
    context = {
        'categories': categories_page,
        'total_categories': total_categories,
        'active_categories': active_categories,
        'special_handling_categories': special_handling_categories,
        'search_query': search_query,
        'status_filter': status_filter,
        'order_by': order_by,
        'category_chart_data': json.dumps(category_chart_data),
        'special_handling_data': json.dumps(special_handling_data),
    }
    
    return render(request, 'categories/list.html', context)


@login_required
def category_create(request):
    """Create a new cargo category"""
    if request.method == 'POST':
        form = CargoCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('categories:list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CargoCategoryForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'categories/form.html', context)


@login_required
def category_detail(request, category_id):
    """View category details with related cargo statistics"""
    category = get_object_or_404(CargoCategory, id=category_id)
    
    # Get related cargos
    cargos = Cargo.objects.filter(category=category).select_related(
        'supplier', 'warehouse'
    ).order_by('-dispatch_date')[:20]
    
    # Statistics
    total_cargos = Cargo.objects.filter(category=category).count()
    active_cargos = Cargo.objects.filter(
        category=category,
        status__in=['DISPATCHED', 'IN_TRANSIT', 'ARRIVED']
    ).count()
    completed_cargos = Cargo.objects.filter(
        category=category,
        status='RECEIVED'
    ).count()
    
    # Status distribution
    status_distribution = Cargo.objects.filter(category=category).values(
        'status'
    ).annotate(count=Count('id')).order_by('-count')
    
    status_chart_data = {
        'labels': [item['status'].replace('_', ' ').title() for item in status_distribution],
        'data': [item['count'] for item in status_distribution]
    }
    
    # Monthly trend (last 6 months)
    from datetime import datetime, timedelta
    from django.db.models.functions import TruncMonth
    
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_trend = Cargo.objects.filter(
        category=category,
        dispatch_date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('dispatch_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    trend_data = {
        'labels': [item['month'].strftime('%b %Y') for item in monthly_trend],
        'data': [item['count'] for item in monthly_trend]
    }
    
    context = {
        'category': category,
        'cargos': cargos,
        'total_cargos': total_cargos,
        'active_cargos': active_cargos,
        'completed_cargos': completed_cargos,
        'status_chart_data': json.dumps(status_chart_data),
        'trend_data': json.dumps(trend_data),
    }
    
    return render(request, 'categories/detail.html', context)


@login_required
def category_update(request, category_id):
    """Update an existing category"""
    category = get_object_or_404(CargoCategory, id=category_id)
    
    if request.method == 'POST':
        form = CargoCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('categories:detail', category_id=category.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CargoCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'action': 'Update',
    }
    
    return render(request, 'categories/form.html', context)


@login_required
def category_delete(request, category_id):
    """Delete a category"""
    category = get_object_or_404(CargoCategory, id=category_id)
    
    # Check if category has related cargos
    cargo_count = Cargo.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if cargo_count > 0:
            messages.error(
                request,
                f'Cannot delete category "{category.name}". It has {cargo_count} associated cargo(s).'
            )
            return redirect('categories:detail', category_id=category.id)
        
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully!')
        return redirect('categories:list')
    
    context = {
        'category': category,
        'cargo_count': cargo_count,
    }
    
    return render(request, 'categories/delete.html', context)


@login_required
def category_toggle_status(request, category_id):
    """Toggle category active status (AJAX)"""
    if request.method == 'POST':
        category = get_object_or_404(CargoCategory, id=category_id)
        category.is_active = not category.is_active
        category.save()
        
        return JsonResponse({
            'success': True,
            'is_active': category.is_active,
            'message': f'Category {"activated" if category.is_active else "deactivated"} successfully!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


# ==================== COUNTY VIEWS ====================

@login_required
def county_list(request):
    """List all counties with supplier and warehouse counts"""
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Base queryset with annotations
    counties = County.objects.annotate(
        supplier_count=Count('supplier', filter=Q(supplier__status='ACTIVE')),
        warehouse_count=Count('warehouse', filter=Q(warehouse__is_active=True)),
        total_suppliers=Count('supplier'),
        total_warehouses=Count('warehouse'),
        cargo_count=Count('warehouse__cargos')
    )
    
    # Apply search filter
    if search_query:
        counties = counties.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query)
        )
    
    # Order by
    order_by = request.GET.get('order_by', 'name')
    counties = counties.order_by(order_by)
    
    # Pagination
    paginator = Paginator(counties, 15)
    page_number = request.GET.get('page')
    counties_page = paginator.get_page(page_number)
    
    # Statistics
    total_counties = County.objects.count()
    counties_with_suppliers = County.objects.annotate(
        sup_count=Count('supplier')
    ).filter(sup_count__gt=0).count()
    counties_with_warehouses = County.objects.annotate(
        wh_count=Count('warehouse')
    ).filter(wh_count__gt=0).count()
    
    # Chart data: Top counties by suppliers
    top_supplier_counties = County.objects.annotate(
        supplier_count=Count('supplier')
    ).order_by('-supplier_count')[:10]
    
    supplier_chart_data = {
        'labels': [county.name for county in top_supplier_counties],
        'data': [county.supplier_count for county in top_supplier_counties]
    }
    
    # Chart data: Top counties by warehouses
    top_warehouse_counties = County.objects.annotate(
        warehouse_count=Count('warehouse')
    ).order_by('-warehouse_count')[:10]
    
    warehouse_chart_data = {
        'labels': [county.name for county in top_warehouse_counties],
        'data': [county.warehouse_count for county in top_warehouse_counties]
    }
    
    # Distribution chart
    distribution_data = {
        'labels': ['With Suppliers', 'With Warehouses', 'Without Facilities'],
        'data': [
            counties_with_suppliers,
            counties_with_warehouses,
            total_counties - max(counties_with_suppliers, counties_with_warehouses)
        ]
    }
    
    context = {
        'counties': counties_page,
        'total_counties': total_counties,
        'counties_with_suppliers': counties_with_suppliers,
        'counties_with_warehouses': counties_with_warehouses,
        'search_query': search_query,
        'order_by': order_by,
        'supplier_chart_data': json.dumps(supplier_chart_data),
        'warehouse_chart_data': json.dumps(warehouse_chart_data),
        'distribution_data': json.dumps(distribution_data),
    }
    
    return render(request, 'counties/list.html', context)


@login_required
def county_create(request):
    """Create a new county"""
    if request.method == 'POST':
        form = CountyForm(request.POST)
        if form.is_valid():
            county = form.save()
            messages.success(request, f'County "{county.name}" created successfully!')
            return redirect('counties:list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CountyForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'counties/form.html', context)


@login_required
def county_detail(request, county_id):
    """View county details with suppliers and warehouses"""
    county = get_object_or_404(County, id=county_id)
    
    # Get suppliers in this county
    suppliers = Supplier.objects.filter(county=county).annotate(
        cargo_count=Count('cargos')
    ).order_by('-reliability_score')[:10]
    
    # Get warehouses in this county
    warehouses = Warehouse.objects.filter(county=county).annotate(
        cargo_count=Count('cargos')
    ).order_by('-total_capacity_sqm')[:10]
    
    # Statistics
    total_suppliers = Supplier.objects.filter(county=county).count()
    active_suppliers = Supplier.objects.filter(county=county, status='ACTIVE').count()
    total_warehouses = Warehouse.objects.filter(county=county).count()
    active_warehouses = Warehouse.objects.filter(county=county, is_active=True).count()
    
    # Cargo statistics
    total_cargos = Cargo.objects.filter(
        Q(supplier__county=county) | Q(warehouse__county=county)
    ).count()
    
    # Supplier status distribution
    supplier_status_dist = Supplier.objects.filter(county=county).values(
        'status'
    ).annotate(count=Count('id'))
    
    supplier_status_data = {
        'labels': [item['status'].title() for item in supplier_status_dist],
        'data': [item['count'] for item in supplier_status_dist]
    }
    
    # Warehouse capacity utilization
    warehouses_capacity = Warehouse.objects.filter(county=county)
    capacity_data = {
        'labels': [wh.name for wh in warehouses_capacity],
        'utilization': [float(wh.capacity_utilization_percentage) for wh in warehouses_capacity],
        'total': [float(wh.total_capacity_sqm) for wh in warehouses_capacity]
    }
    
    context = {
        'county': county,
        'suppliers': suppliers,
        'warehouses': warehouses,
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,
        'total_warehouses': total_warehouses,
        'active_warehouses': active_warehouses,
        'total_cargos': total_cargos,
        'supplier_status_data': json.dumps(supplier_status_data),
        'capacity_data': json.dumps(capacity_data),
    }
    
    return render(request, 'counties/detail.html', context)


@login_required
def county_update(request, county_id):
    """Update an existing county"""
    county = get_object_or_404(County, id=county_id)
    
    if request.method == 'POST':
        form = CountyForm(request.POST, instance=county)
        if form.is_valid():
            county = form.save()
            messages.success(request, f'County "{county.name}" updated successfully!')
            return redirect('counties:detail', county_id=county.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CountyForm(instance=county)
    
    context = {
        'form': form,
        'county': county,
        'action': 'Update',
    }
    
    return render(request, 'counties/form.html', context)


@login_required
def county_delete(request, county_id):
    """Delete a county"""
    county = get_object_or_404(County, id=county_id)
    
    # Check for related objects
    supplier_count = Supplier.objects.filter(county=county).count()
    warehouse_count = Warehouse.objects.filter(county=county).count()
    
    if request.method == 'POST':
        if supplier_count > 0 or warehouse_count > 0:
            messages.error(
                request,
                f'Cannot delete county "{county.name}". It has {supplier_count} supplier(s) and {warehouse_count} warehouse(s).'
            )
            return redirect('counties:detail', county_id=county.id)
        
        county_name = county.name
        county.delete()
        messages.success(request, f'County "{county_name}" deleted successfully!')
        return redirect('counties:list')
    
    context = {
        'county': county,
        'supplier_count': supplier_count,
        'warehouse_count': warehouse_count,
    }
    
    return render(request, 'counties/delete.html', context)


"""
Fixed Supplier Performance Analytics View
Works with your actual SupplierPerformance model fields
"""

from django.db.models import Avg, Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json
from decimal import Decimal


def convert_to_json_serializable(obj):
    """Convert Decimal and datetime objects to JSON-serializable types"""
    if isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, datetime.date)):
        return obj.isoformat()
    elif obj is None:
        return None
    else:
        return obj


@login_required
def supplier_performance(request):
    """Supplier performance analytics dashboard with dynamic graphs"""
    from .models import SupplierPerformance
    
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
        {
            'range': '90-100',
            'count': performances.filter(overall_performance_score__gte=90).count()
        },
        {
            'range': '80-89',
            'count': performances.filter(
                overall_performance_score__gte=80,
                overall_performance_score__lt=90
            ).count()
        },
        {
            'range': '70-79',
            'count': performances.filter(
                overall_performance_score__gte=70,
                overall_performance_score__lt=80
            ).count()
        },
        {
            'range': '60-69',
            'count': performances.filter(
                overall_performance_score__gte=60,
                overall_performance_score__lt=70
            ).count()
        },
        {
            'range': 'Below 60',
            'count': performances.filter(overall_performance_score__lt=60).count()
        },
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

    # Chart 4: Average Metrics Comparison
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    avg_delivery = sum(delivery_scores) / len(delivery_scores) if delivery_scores else 0
    avg_overall = float(avg_performance_score)

    # Calculate average delivery time across all suppliers
    avg_delivery_time = performances.aggregate(
        avg=Avg('average_delivery_time_hours')
    )['avg'] or 0
    
    # Convert delivery time to a score (assuming 48 hours is baseline, faster is better)
    delivery_time_score = max(0, 100 - (float(avg_delivery_time) / 48 * 100)) if avg_delivery_time > 0 else 0

    avg_metrics = {
        'Quality': round(avg_quality, 2),
        'On-Time Delivery': round(avg_delivery, 2),
        'Speed': round(delivery_time_score, 2),
        'Consistency': round(avg_overall * 0.8, 2),  # Derived metric
        'Overall': round(avg_overall, 2)
    }

    # Chart 5: Performance Trend (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_performance = SupplierPerformance.objects.filter(
        last_calculated__gte=six_months_ago
    ).annotate(
        month=TruncMonth('last_calculated')
    ).values('month').annotate(
        avg_score=Avg('overall_performance_score')
    ).order_by('month')

    trend_data = {
        'labels': [mp['month'].strftime('%b %Y') for mp in monthly_performance],
        'scores': [float(mp['avg_score']) for mp in monthly_performance]
    }

    # Chart 6: Delivery Metrics Breakdown
    delivery_metrics = {
        'labels': ['On-Time', 'Delayed', 'Cancelled'],
        'data': [
            performances.aggregate(total=Count('on_time_deliveries'))['total'] or 0,
            performances.aggregate(total=Count('delayed_deliveries'))['total'] or 0,
            performances.aggregate(total=Count('cancelled_deliveries'))['total'] or 0,
        ]
    }

    # Enhanced top performers data with all metrics
    top_performers_data = []
    for perf in top_performers:
        total = perf.total_deliveries or 1
        good_quality = total - (perf.damaged_cargo_count + perf.quality_issues_count)
        quality_score = (good_quality / total) * 100
        
        top_performers_data.append({
            'supplier': perf.supplier,
            'overall_score': float(perf.overall_performance_score),
            'quality_score': round(quality_score, 2),
            'delivery_rate': float(perf.on_time_delivery_rate),
            'total_deliveries': perf.total_deliveries,
            'avg_delivery_time': float(perf.average_delivery_time_hours) if perf.average_delivery_time_hours else 0
        })

    # Enhanced need improvement data
    need_improvement_data = []
    for perf in need_improvement:
        total = perf.total_deliveries or 1
        good_quality = total - (perf.damaged_cargo_count + perf.quality_issues_count)
        quality_score = (good_quality / total) * 100
        
        need_improvement_data.append({
            'supplier': perf.supplier,
            'overall_score': float(perf.overall_performance_score),
            'quality_score': round(quality_score, 2),
            'delivery_rate': float(perf.on_time_delivery_rate),
            'total_deliveries': perf.total_deliveries,
            'delayed_deliveries': perf.delayed_deliveries
        })

    context = {
        'performances': performances,
        'total_suppliers': total_suppliers,
        'avg_performance_score': round(float(avg_performance_score), 2),
        'top_performers_count': top_performers.count(),
        'need_improvement_count': need_improvement.count(),
        'top_performers_data': top_performers_data,
        'need_improvement_data': need_improvement_data,
        'score_ranges': json.dumps(convert_to_json_serializable(score_ranges)),
        'top_suppliers_data': json.dumps(convert_to_json_serializable(top_suppliers_data)),
        'scatter_data': json.dumps(convert_to_json_serializable(scatter_data)),
        'avg_metrics': json.dumps(convert_to_json_serializable(avg_metrics)),
        'trend_data': json.dumps(convert_to_json_serializable(trend_data)),
        'delivery_metrics': json.dumps(convert_to_json_serializable(delivery_metrics)),
    }

    return render(request, 'analytics/supplier_performance.html', context)


"""
Updated Django Views for Cargo Tracking System
Includes automatic report generation and proper chart data handling
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q, Max, Min, F
from django.db.models.functions import TruncMonth, TruncDate
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

from .models import (
    CargoCategory, Cargo, Supplier, Warehouse, 
    SupplierPerformance, Report, Alert
)


# ============================================
# HELPER FUNCTION FOR JSON SERIALIZATION
# ============================================

def convert_to_json_serializable(obj):
    """
    Recursively convert Decimal, datetime, and date objects to JSON-serializable types
    """
    if isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif obj is None:
        return None
    else:
        return obj


# ============================================
# AUTOMATIC REPORT GENERATION FUNCTION
# ============================================

@login_required
def generate_automatic_reports(request):
    """
    Generate all automatic reports with current system data
    """
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Generate Supplier Performance Report
    supplier_performances = SupplierPerformance.objects.select_related('supplier').all()
    supplier_report_data = {
        'generated_at': timezone.now().isoformat(),
        'total_suppliers': supplier_performances.count(),
        'active_suppliers': Supplier.objects.filter(status='ACTIVE').count(),
        'top_performers': list(
            supplier_performances.order_by('-overall_performance_score')[:10]
            .values('supplier__name', 'overall_performance_score', 'on_time_delivery_rate')
        ),
        'statistics': {
            'avg_performance_score': float(supplier_performances.aggregate(
                avg=Avg('overall_performance_score'))['avg'] or 0),
            'total_deliveries': supplier_performances.aggregate(
                total=Sum('total_deliveries'))['total'] or 0,
            'on_time_deliveries': supplier_performances.aggregate(
                total=Sum('on_time_deliveries'))['total'] or 0,
        }
    }
    
    # Convert to JSON-serializable format
    supplier_report_data = convert_to_json_serializable(supplier_report_data)
    
    Report.objects.create(
        report_type='SUPPLIER_PERFORMANCE',
        title=f'Supplier Performance Report - {today.strftime("%B %Y")}',
        description='Automatically generated monthly supplier performance analysis',
        start_date=start_of_month,
        end_date=today,
        report_data=supplier_report_data,
        created_by=request.user
    )
    
    # Generate Cargo Movement Report
    cargo_stats = Cargo.objects.aggregate(
        total=Count('id'),
        in_transit=Count('id', filter=Q(status='IN_TRANSIT')),
        delivered=Count('id', filter=Q(status='RECEIVED')),
        delayed=Count('id', filter=Q(is_delayed=True)),
        cancelled=Count('id', filter=Q(status='CANCELLED')),
        damaged=Count('id', filter=Q(status='DAMAGED')),
        total_weight=Sum('weight_kg'),
        total_value=Sum('declared_value')
    )
    
    cargo_report_data = {
        'generated_at': timezone.now().isoformat(),
        'summary': cargo_stats,
        'by_status': list(
            Cargo.objects.values('status')
            .annotate(count=Count('id'), total_value=Sum('declared_value'))
            .order_by('-count')
        ),
        'by_warehouse': list(
            Cargo.objects.values('warehouse__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        ),
    }
    
    # Convert to JSON-serializable format
    cargo_report_data = convert_to_json_serializable(cargo_report_data)
    
    Report.objects.create(
        report_type='CARGO_MOVEMENT',
        title=f'Cargo Movement Report - {today.strftime("%B %Y")}',
        description='Automatically generated cargo movement analysis',
        start_date=start_of_month,
        end_date=today,
        report_data=cargo_report_data,
        created_by=request.user
    )
    
    # Generate Delivery Analysis Report
    delivery_data = {
        'generated_at': timezone.now().isoformat(),
        'on_time_deliveries': Cargo.objects.filter(
            is_delayed=False, status='RECEIVED'
        ).count(),
        'delayed_deliveries': Cargo.objects.filter(is_delayed=True).count(),
        'average_delivery_time': float(
            Cargo.objects.filter(delivery_duration_hours__isnull=False)
            .aggregate(avg=Avg('delivery_duration_hours'))['avg'] or 0
        ),
        'by_supplier': list(
            Cargo.objects.values('supplier__name')
            .annotate(
                total=Count('id'),
                delayed=Count('id', filter=Q(is_delayed=True))
            )
            .order_by('-total')[:10]
        )
    }
    
    # Convert to JSON-serializable format
    delivery_data = convert_to_json_serializable(delivery_data)
    
    Report.objects.create(
        report_type='DELIVERY_ANALYSIS',
        title=f'Delivery Analysis Report - {today.strftime("%B %Y")}',
        description='Automatically generated delivery performance analysis',
        start_date=start_of_month,
        end_date=today,
        report_data=delivery_data,
        created_by=request.user
    )
    
    # Generate Monthly Summary Report
    monthly_cargos = Cargo.objects.filter(dispatch_date__gte=start_of_month)
    cargo_count = monthly_cargos.count()
    
    monthly_summary = {
        'generated_at': timezone.now().isoformat(),
        'total_cargos': cargo_count,
        'total_value': float(
            monthly_cargos.aggregate(total=Sum('declared_value'))['total'] or 0
        ),
        'active_suppliers': Supplier.objects.filter(status='ACTIVE').count(),
        'warehouses': Warehouse.objects.filter(is_active=True).count(),
        'alerts': Alert.objects.filter(
            is_resolved=False, 
            created_at__gte=start_of_month
        ).count(),
    }
    
    # Convert to JSON-serializable format
    monthly_summary = convert_to_json_serializable(monthly_summary)
    
    Report.objects.create(
        report_type='MONTHLY_SUMMARY',
        title=f'Monthly Summary - {today.strftime("%B %Y")}',
        description='Automatically generated monthly system summary',
        start_date=start_of_month,
        end_date=today,
        report_data=monthly_summary,
        created_by=request.user
    )
    
    # Add success message (optional - requires messages framework)
    from django.contrib import messages
    messages.success(request, f'Successfully generated 4 reports for {today.strftime("%B %Y")}')
    
    return redirect('reports_list')


# ============================================
# REPORTS LIST VIEW
# ============================================

@login_required
def reports_list(request):
    """List all generated reports with analytics charts."""
    reports = Report.objects.all().order_by('-created_at')

    # Chart 1: Reports by Type
    reports_by_type = (
        Report.objects.values('report_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    type_chart_data = {
        'labels': [
            r['report_type'].replace('_', ' ').title() 
            for r in reports_by_type
        ],
        'counts': [r['count'] for r in reports_by_type],
    }

    # Chart 2: Reports Created Over the Last 12 Months
    twelve_months_ago = timezone.now() - timedelta(days=365)
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

    # Simple Stats
    total_reports = reports.count()
    supplier_reports = reports.filter(report_type='SUPPLIER_PERFORMANCE').count()
    cargo_reports = reports.filter(report_type='CARGO_MOVEMENT').count()
    monthly_reports_count = reports.filter(report_type='MONTHLY_SUMMARY').count()

    # Pagination
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page', 1)
    reports_page = paginator.get_page(page_number)

    context = {
        'reports': reports_page,
        'total_reports': total_reports,
        'supplier_reports': supplier_reports,
        'cargo_reports': cargo_reports,
        'monthly_reports_count': monthly_reports_count,
        'type_chart_data': json.dumps(type_chart_data),
        'timeline_data': json.dumps(timeline_data),
    }

    return render(request, 'reports/list.html', context)


# ============================================
# REPORT DETAIL VIEW
# ============================================

@login_required
def report_detail(request, report_id):
    """View a specific report with detailed analytics"""
    report = get_object_or_404(Report, id=report_id)
    context = {'report': report}

    # Supplier Performance Report
    if report.report_type == 'SUPPLIER_PERFORMANCE':
        performances = (
            SupplierPerformance.objects.select_related('supplier')
            .order_by('-overall_performance_score')[:20]
        )
        performance_chart = {
            'labels': [p.supplier.name for p in performances],
            'scores': [float(p.overall_performance_score) for p in performances],
        }
        context['performance_chart'] = json.dumps(performance_chart)
        context['performances'] = performances

    # Cargo Movement Report
    elif report.report_type == 'CARGO_MOVEMENT':
        cargos = Cargo.objects.select_related('supplier', 'warehouse').order_by('-dispatch_date')[:20]
        cargo_chart = {
            'labels': [c.cargo_id for c in cargos],
            'weights': [float(c.weight_kg) for c in cargos],
        }
        context['cargo_chart'] = json.dumps(cargo_chart)
        context['cargos'] = cargos

    # Delivery Analysis Report
    elif report.report_type == 'DELIVERY_ANALYSIS':
        delayed = Cargo.objects.filter(is_delayed=True).count()
        on_time = Cargo.objects.filter(is_delayed=False, status='RECEIVED').count()
        delivery_chart = {
            'labels': ['On-Time', 'Delayed'],
            'counts': [on_time, delayed],
        }
        context['delivery_chart'] = json.dumps(delivery_chart)

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
