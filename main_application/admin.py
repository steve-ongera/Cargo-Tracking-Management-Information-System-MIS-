"""
Django Admin Configuration for Cargo Tracking Management Information System
Professional admin interface with advanced filtering, search, and analytics
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from .models import (
    County, Supplier, Warehouse, CargoCategory, Cargo,
    CargoStatusHistory, SupplierPerformance, Alert, Report
)


# Custom Filters
class DelayedCargoFilter(SimpleListFilter):
    title = 'Delay Status'
    parameter_name = 'delayed'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Delayed Shipments'),
            ('no', 'On-Time Shipments'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_delayed=True)
        if self.value() == 'no':
            return queryset.filter(is_delayed=False)


class SupplierPerformanceFilter(SimpleListFilter):
    title = 'Performance Level'
    parameter_name = 'performance'

    def lookups(self, request, model_admin):
        return (
            ('excellent', 'Excellent (80-100)'),
            ('good', 'Good (60-79)'),
            ('average', 'Average (40-59)'),
            ('poor', 'Poor (0-39)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'excellent':
            return queryset.filter(reliability_score__gte=80)
        if self.value() == 'good':
            return queryset.filter(reliability_score__gte=60, reliability_score__lt=80)
        if self.value() == 'average':
            return queryset.filter(reliability_score__gte=40, reliability_score__lt=60)
        if self.value() == 'poor':
            return queryset.filter(reliability_score__lt=40)


# Inline Admin Classes
class CargoStatusHistoryInline(admin.TabularInline):
    model = CargoStatusHistory
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'created_at', 'created_by')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class CargoInline(admin.TabularInline):
    model = Cargo
    extra = 0
    fields = ('cargo_id', 'description', 'status', 'dispatch_date', 'expected_arrival_date')
    readonly_fields = ('cargo_id',)
    show_change_link = True
    can_delete = False


# Admin Classes
@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'supplier_count', 'warehouse_count')
    search_fields = ('name', 'code')
    ordering = ('name',)
    
    def supplier_count(self, obj):
        return obj.supplier_set.count()
    supplier_count.short_description = 'Suppliers'
    
    def warehouse_count(self, obj):
        return obj.warehouse_set.count()
    warehouse_count.short_description = 'Warehouses'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'supplier_id', 'name', 'supplier_type', 'kra_pin', 'county',
        'status_badge', 'reliability_badge', 'total_cargos', 'created_at'
    )
    list_filter = (
        'status', 'supplier_type', SupplierPerformanceFilter, 
        'county', 'created_at'
    )
    search_fields = (
        'supplier_id', 'name', 'kra_pin', 'phone_number', 
        'email', 'primary_contact_person'
    )
    readonly_fields = (
        'supplier_id', 'reliability_score', 'created_at', 
        'updated_at', 'created_by', 'updated_by'
    )
    
    fieldsets = (
        ('Supplier Information', {
            'fields': (
                'supplier_id', 'name', 'supplier_type', 'kra_pin', 
                'goods_supplied', 'status'
            )
        }),
        ('Contact Details', {
            'fields': (
                'primary_contact_person', 'phone_number', 'alternative_phone',
                'email'
            )
        }),
        ('Address Information', {
            'fields': (
                'physical_address', 'county', 'town_city', 'postal_address'
            )
        }),
        ('Business Details', {
            'fields': (
                'payment_terms', 'credit_limit', 'reliability_score'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'registration_certificate'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CargoInline]
    
    actions = ['activate_suppliers', 'suspend_suppliers', 'calculate_performance']
    
    def status_badge(self, obj):
        colors = {
            'ACTIVE': 'green',
            'INACTIVE': 'gray',
            'SUSPENDED': 'orange',
            'BLACKLISTED': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def reliability_badge(self, obj):
        score = float(obj.reliability_score)
        if score >= 80:
            color = 'green'
            label = 'Excellent'
        elif score >= 60:
            color = 'blue'
            label = 'Good'
        elif score >= 40:
            color = 'orange'
            label = 'Average'
        else:
            color = 'red'
            label = 'Poor'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{} ({})</span>',
            color, label, score
        )
    reliability_badge.short_description = 'Reliability'
    
    def total_cargos(self, obj):
        return obj.cargos.count()
    total_cargos.short_description = 'Total Shipments'
    
    def activate_suppliers(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'{updated} supplier(s) activated successfully.')
    activate_suppliers.short_description = 'Activate selected suppliers'
    
    def suspend_suppliers(self, request, queryset):
        updated = queryset.update(status='SUSPENDED')
        self.message_user(request, f'{updated} supplier(s) suspended.')
    suspend_suppliers.short_description = 'Suspend selected suppliers'
    
    def calculate_performance(self, request, queryset):
        for supplier in queryset:
            performance, created = SupplierPerformance.objects.get_or_create(
                supplier=supplier
            )
            performance.calculate_metrics()
        self.message_user(request, 'Performance metrics recalculated successfully.')
    calculate_performance.short_description = 'Recalculate performance metrics'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        'warehouse_id', 'name', 'warehouse_type', 'county', 'town_city',
        'capacity_badge', 'manager_name', 'is_active'
    )
    list_filter = ('warehouse_type', 'county', 'is_active', 'created_at')
    search_fields = (
        'warehouse_id', 'name', 'town_city', 'manager_name', 'manager_phone'
    )
    readonly_fields = (
        'warehouse_id', 'capacity_utilization_percentage', 
        'created_at', 'updated_at', 'created_by', 'updated_by'
    )
    
    fieldsets = (
        ('Warehouse Information', {
            'fields': (
                'warehouse_id', 'name', 'warehouse_type', 'is_active'
            )
        }),
        ('Location', {
            'fields': (
                'county', 'town_city', 'physical_address', 'gps_coordinates'
            )
        }),
        ('Capacity Management', {
            'fields': (
                'total_capacity_sqm', 'current_utilization_sqm',
                'capacity_utilization_percentage'
            )
        }),
        ('Manager Details', {
            'fields': (
                'manager_name', 'manager_phone', 'manager_email', 'operating_hours'
            )
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CargoInline]
    
    def capacity_badge(self, obj):
        utilization = obj.capacity_utilization_percentage
        if utilization >= 90:
            color = 'red'
        elif utilization >= 70:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{:.1f}%</span>',
            color, utilization
        )
    capacity_badge.short_description = 'Capacity Usage'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CargoCategory)
class CargoCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'requires_special_handling', 'cargo_count', 'is_active'
    )
    list_filter = ('requires_special_handling', 'is_active')
    search_fields = ('name', 'code', 'description')
    
    def cargo_count(self, obj):
        return obj.cargos.count()
    cargo_count.short_description = 'Total Cargos'


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = (
        'cargo_id', 'supplier', 'warehouse', 'description_short',
        'quantity', 'status_badge', 'dispatch_date', 'expected_arrival_date',
        'delay_indicator', 'priority_badge'
    )
    list_filter = (
        'status', DelayedCargoFilter, 'priority', 'transport_mode',
        'warehouse', 'category', 'dispatch_date'
    )
    search_fields = (
        'cargo_id', 'tracking_number', 'description', 
        'supplier__name', 'purchase_order_number', 'invoice_number'
    )
    readonly_fields = (
        'cargo_id', 'tracking_number', 'delivery_duration_hours',
        'is_delayed', 'estimated_delay_hours',
        'created_at', 'updated_at', 'created_by', 'updated_by'
    )
    date_hierarchy = 'dispatch_date'
    
    fieldsets = (
        ('Cargo Identification', {
            'fields': (
                'cargo_id', 'tracking_number', 'category', 'priority'
            )
        }),
        ('Shipment Details', {
            'fields': (
                'supplier', 'warehouse', 'description', 'quantity',
                'unit_of_measurement', 'weight_kg', 'volume_cbm'
            )
        }),
        ('Valuation', {
            'fields': ('declared_value', 'insurance_value')
        }),
        ('Schedule', {
            'fields': (
                'dispatch_date', 'expected_arrival_date', 'actual_arrival_date',
                'received_date', 'delivery_duration_hours', 'is_delayed',
                'estimated_delay_hours', 'delay_reason'
            )
        }),
        ('Transport Information', {
            'fields': (
                'transport_mode', 'vehicle_registration', 'driver_name', 'driver_phone'
            )
        }),
        ('Status & Quality', {
            'fields': (
                'status', 'condition_on_arrival', 'quality_check_passed',
                'inspection_notes'
            )
        }),
        ('Storage', {
            'fields': ('storage_location',)
        }),
        ('Documentation', {
            'fields': (
                'purchase_order_number', 'invoice_number', 'delivery_note_number'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('special_instructions', 'notes'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CargoStatusHistoryInline]
    
    actions = [
        'mark_as_in_transit', 'mark_as_arrived', 'mark_as_received',
        'generate_delivery_report'
    ]
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'
    
    def status_badge(self, obj):
        colors = {
            'DISPATCHED': 'blue',
            'IN_TRANSIT': 'cyan',
            'ARRIVED': 'orange',
            'RECEIVED': 'green',
            'STORED': 'darkgreen',
            'DELAYED': 'red',
            'CANCELLED': 'gray',
            'DAMAGED': 'darkred'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        colors = {
            'LOW': 'lightgray',
            'MEDIUM': 'blue',
            'HIGH': 'orange',
            'URGENT': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.priority, 'gray'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def delay_indicator(self, obj):
        if obj.is_delayed:
            delay_hours = obj.estimated_delay_hours
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ {} hrs</span>',
                f'{delay_hours:.1f}'
            )
        return format_html('<span style="color: green;">✓ On Time</span>')
    delay_indicator.short_description = 'Delay Status'
    
    def mark_as_in_transit(self, request, queryset):
        updated = queryset.update(status='IN_TRANSIT')
        self.message_user(request, f'{updated} cargo(s) marked as In Transit.')
    mark_as_in_transit.short_description = 'Mark as In Transit'
    
    def mark_as_arrived(self, request, queryset):
        updated = queryset.update(status='ARRIVED', actual_arrival_date=timezone.now())
        self.message_user(request, f'{updated} cargo(s) marked as Arrived.')
    mark_as_arrived.short_description = 'Mark as Arrived'
    
    def mark_as_received(self, request, queryset):
        updated = queryset.update(status='RECEIVED', received_date=timezone.now())
        self.message_user(request, f'{updated} cargo(s) marked as Received.')
    mark_as_received.short_description = 'Mark as Received'
    
    def generate_delivery_report(self, request, queryset):
        # Placeholder for report generation
        self.message_user(
            request, 
            f'Delivery report generated for {queryset.count()} cargo(s).'
        )
    generate_delivery_report.short_description = 'Generate Delivery Report'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        
        # Track status changes
        if change and 'status' in form.changed_data:
            old_status = Cargo.objects.get(pk=obj.pk).status
            CargoStatusHistory.objects.create(
                cargo=obj,
                from_status=old_status,
                to_status=obj.status,
                created_by=request.user
            )
        
        super().save_model(request, obj, form, change)


@admin.register(CargoStatusHistory)
class CargoStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'cargo', 'from_status', 'to_status', 'location', 
        'created_at', 'created_by'
    )
    list_filter = ('from_status', 'to_status', 'created_at')
    search_fields = ('cargo__cargo_id', 'location', 'remarks')
    readonly_fields = ('cargo', 'from_status', 'to_status', 'created_at', 'created_by')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupplierPerformance)
class SupplierPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        'supplier', 'total_deliveries', 'on_time_delivery_rate_display',
        'average_delivery_time_hours', 'performance_score_badge',
        'last_calculated'
    )
    list_filter = ('last_calculated',)
    search_fields = ('supplier__name', 'supplier__supplier_id')
    readonly_fields = (
        'supplier', 'total_deliveries', 'on_time_deliveries',
        'delayed_deliveries', 'cancelled_deliveries',
        'average_delivery_time_hours', 'fastest_delivery_hours',
        'slowest_delivery_hours', 'total_cargo_value',
        'damaged_cargo_count', 'quality_issues_count',
        'overall_performance_score', 'on_time_delivery_rate',
        'last_calculated'
    )
    
    actions = ['recalculate_metrics']
    
    def performance_score_badge(self, obj):
        score = float(obj.overall_performance_score)
        if score >= 80:
            color = 'green'
        elif score >= 60:
            color = 'blue'
        elif score >= 40:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{:.2f}</span>',
            color, score
        )
    performance_score_badge.short_description = 'Performance Score'
    
    def on_time_delivery_rate_display(self, obj):
        rate = float(obj.on_time_delivery_rate)
        color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    on_time_delivery_rate_display.short_description = 'On-Time Rate'
    
    def recalculate_metrics(self, request, queryset):
        for performance in queryset:
            performance.calculate_metrics()
        self.message_user(request, 'Performance metrics recalculated successfully.')
    recalculate_metrics.short_description = 'Recalculate performance metrics'
    
    def has_add_permission(self, request):
        return False


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        'severity_badge', 'alert_type', 'title', 'cargo', 'supplier',
        'is_read', 'is_resolved', 'created_at'
    )
    list_filter = (
        'severity', 'alert_type', 'is_read', 'is_resolved', 'created_at'
    )
    search_fields = ('title', 'message', 'cargo__cargo_id', 'supplier__name')
    readonly_fields = ('created_at', 'created_by', 'resolved_at', 'resolved_by')
    
    actions = ['mark_as_read', 'mark_as_resolved']
    
    def severity_badge(self, obj):
        colors = {
            'INFO': 'blue',
            'WARNING': 'orange',
            'CRITICAL': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.severity, 'gray'),
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} alert(s) marked as read.')
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            is_resolved=True, 
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{updated} alert(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark as resolved'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'report_type', 'start_date', 'end_date', 
        'created_at', 'created_by'
    )
    list_filter = ('report_type', 'start_date', 'end_date', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# Customize Admin Site
admin.site.site_header = "Cargo Tracking MIS - Administration"
admin.site.site_title = "Cargo Tracking MIS Admin"
admin.site.index_title = "Welcome to Cargo Tracking Management System"