"""
Django Management Command: Generate Automatic Reports
Save this as: main_application/management/commands/generate_reports.py

Usage: python manage.py generate_reports
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, Min, Max
from datetime import timedelta, datetime, date
from decimal import Decimal

from main_application.models import (
    Report, Cargo, Supplier, SupplierPerformance, 
    Warehouse, CargoCategory, Alert
)


class Command(BaseCommand):
    help = 'Generate automatic reports with system data'

    def convert_to_json_serializable(self, obj):
        """
        Recursively convert Decimal, datetime, and date objects to JSON-serializable types
        """
        if isinstance(obj, list):
            return [self.convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.convert_to_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif obj is None:
            return None
        else:
            return obj

    def handle(self, *args, **options):
        self.stdout.write('Starting automatic report generation...')
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        # 1. Generate Supplier Performance Report
        self.stdout.write('Generating Supplier Performance Report...')
        supplier_performances = SupplierPerformance.objects.select_related('supplier').all()
        
        supplier_report_data = {
            'generated_at': timezone.now().isoformat(),
            'total_suppliers': supplier_performances.count(),
            'active_suppliers': Supplier.objects.filter(status='ACTIVE').count(),
            'top_performers': list(
                supplier_performances.order_by('-overall_performance_score')[:10]
                .values(
                    'supplier__name', 
                    'supplier__supplier_id',
                    'overall_performance_score', 
                    'on_time_delivery_rate',
                    'total_deliveries',
                    'on_time_deliveries',
                    'delayed_deliveries'
                )
            ),
            'bottom_performers': list(
                supplier_performances.order_by('overall_performance_score')[:10]
                .values(
                    'supplier__name',
                    'supplier__supplier_id', 
                    'overall_performance_score',
                    'delayed_deliveries'
                )
            ),
            'statistics': {
                'avg_performance_score': float(
                    supplier_performances.aggregate(
                        avg=Avg('overall_performance_score')
                    )['avg'] or 0
                ),
                'total_deliveries': supplier_performances.aggregate(
                    total=Sum('total_deliveries')
                )['total'] or 0,
                'on_time_deliveries': supplier_performances.aggregate(
                    total=Sum('on_time_deliveries')
                )['total'] or 0,
                'delayed_deliveries': supplier_performances.aggregate(
                    total=Sum('delayed_deliveries')
                )['total'] or 0,
            }
        }
        
        # Convert all Decimal values to float
        supplier_report_data = self.convert_to_json_serializable(supplier_report_data)
        
        Report.objects.create(
            report_type='SUPPLIER_PERFORMANCE',
            title=f'Supplier Performance Report - {today.strftime("%B %Y")}',
            description='Automatically generated monthly supplier performance analysis',
            start_date=start_of_month,
            end_date=today,
            report_data=supplier_report_data
        )
        self.stdout.write(self.style.SUCCESS('✓ Supplier Performance Report created'))
        
        # 2. Generate Cargo Movement Report
        self.stdout.write('Generating Cargo Movement Report...')
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
            'summary': {
                'total_cargos': cargo_stats['total'],
                'in_transit': cargo_stats['in_transit'],
                'delivered': cargo_stats['delivered'],
                'delayed': cargo_stats['delayed'],
                'cancelled': cargo_stats['cancelled'],
                'damaged': cargo_stats['damaged'],
                'total_weight_kg': float(cargo_stats['total_weight'] or 0),
                'total_value_kes': float(cargo_stats['total_value'] or 0)
            },
            'by_status': list(
                Cargo.objects.values('status')
                .annotate(
                    count=Count('id'), 
                    total_value=Sum('declared_value'),
                    total_weight=Sum('weight_kg')
                )
                .order_by('-count')
            ),
            'by_warehouse': list(
                Cargo.objects.values('warehouse__name', 'warehouse__warehouse_id')
                .annotate(
                    count=Count('id'),
                    total_weight=Sum('weight_kg')
                )
                .order_by('-count')[:10]
            ),
            'by_category': list(
                Cargo.objects.values('category__name', 'category__code')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            ),
            'recent_shipments': list(
                Cargo.objects.order_by('-dispatch_date')[:20]
                .values(
                    'cargo_id', 
                    'status', 
                    'supplier__name',
                    'warehouse__name',
                    'dispatch_date',
                    'expected_arrival_date'
                )
            )
        }
        
        # Convert all Decimal and datetime values
        cargo_report_data = self.convert_to_json_serializable(cargo_report_data)
        
        Report.objects.create(
            report_type='CARGO_MOVEMENT',
            title=f'Cargo Movement Report - {today.strftime("%B %Y")}',
            description='Automatically generated cargo movement analysis',
            start_date=start_of_month,
            end_date=today,
            report_data=cargo_report_data
        )
        self.stdout.write(self.style.SUCCESS('✓ Cargo Movement Report created'))
        
        # 3. Generate Delivery Analysis Report
        self.stdout.write('Generating Delivery Analysis Report...')
        delivery_data = {
            'generated_at': timezone.now().isoformat(),
            'on_time_deliveries': Cargo.objects.filter(
                is_delayed=False, status='RECEIVED'
            ).count(),
            'delayed_deliveries': Cargo.objects.filter(is_delayed=True).count(),
            'average_delivery_time_hours': float(
                Cargo.objects.filter(delivery_duration_hours__isnull=False)
                .aggregate(avg=Avg('delivery_duration_hours'))['avg'] or 0
            ),
            'fastest_delivery_hours': float(
                Cargo.objects.filter(delivery_duration_hours__isnull=False)
                .aggregate(min=Min('delivery_duration_hours'))['min'] or 0
            ),
            'slowest_delivery_hours': float(
                Cargo.objects.filter(delivery_duration_hours__isnull=False)
                .aggregate(max=Max('delivery_duration_hours'))['max'] or 0
            ),
            'by_supplier': list(
                Cargo.objects.values('supplier__name', 'supplier__supplier_id')
                .annotate(
                    total=Count('id'),
                    delayed=Count('id', filter=Q(is_delayed=True)),
                    on_time=Count('id', filter=Q(is_delayed=False, status='RECEIVED'))
                )
                .order_by('-total')[:15]
            ),
            'by_transport_mode': list(
                Cargo.objects.values('transport_mode')
                .annotate(
                    count=Count('id'),
                    avg_time=Avg('delivery_duration_hours'),
                    delayed=Count('id', filter=Q(is_delayed=True))
                )
                .order_by('-count')
            )
        }
        
        # Convert all Decimal values
        delivery_data = self.convert_to_json_serializable(delivery_data)
        
        Report.objects.create(
            report_type='DELIVERY_ANALYSIS',
            title=f'Delivery Analysis Report - {today.strftime("%B %Y")}',
            description='Automatically generated delivery performance analysis',
            start_date=start_of_month,
            end_date=today,
            report_data=delivery_data
        )
        self.stdout.write(self.style.SUCCESS('✓ Delivery Analysis Report created'))
        
        # 4. Generate Inventory Summary Report
        self.stdout.write('Generating Inventory Summary Report...')
        warehouse_data = []
        for warehouse in Warehouse.objects.filter(is_active=True):
            cargo_count = Cargo.objects.filter(
                warehouse=warehouse,
                status__in=['STORED', 'RECEIVED', 'ARRIVED']
            ).count()
            
            total_weight = Cargo.objects.filter(
                warehouse=warehouse,
                status__in=['STORED', 'RECEIVED', 'ARRIVED']
            ).aggregate(total=Sum('weight_kg'))['total'] or 0
            
            warehouse_data.append({
                'warehouse_id': warehouse.warehouse_id,
                'name': warehouse.name,
                'county': warehouse.county.name,
                'cargo_count': cargo_count,
                'total_weight_kg': float(total_weight),
                'capacity_utilization': float(warehouse.capacity_utilization_percentage)
            })
        
        inventory_report_data = {
            'generated_at': timezone.now().isoformat(),
            'total_warehouses': Warehouse.objects.filter(is_active=True).count(),
            'warehouses': warehouse_data,
            'categories': list(
                CargoCategory.objects.annotate(
                    stored_count=Count(
                        'cargos',
                        filter=Q(cargos__status__in=['STORED', 'RECEIVED', 'ARRIVED'])
                    )
                ).values('name', 'code', 'stored_count').order_by('-stored_count')
            ),
            'total_stored_cargo': Cargo.objects.filter(
                status__in=['STORED', 'RECEIVED', 'ARRIVED']
            ).count()
        }
        
        # Convert all Decimal values
        inventory_report_data = self.convert_to_json_serializable(inventory_report_data)
        
        Report.objects.create(
            report_type='INVENTORY_SUMMARY',
            title=f'Inventory Summary - {today.strftime("%B %Y")}',
            description='Automatically generated inventory summary',
            start_date=start_of_month,
            end_date=today,
            report_data=inventory_report_data
        )
        self.stdout.write(self.style.SUCCESS('✓ Inventory Summary Report created'))
        
        # 5. Generate Monthly Summary Report
        self.stdout.write('Generating Monthly Summary Report...')
        
        # Calculate cargo count safely
        monthly_cargos = Cargo.objects.filter(dispatch_date__gte=start_of_month)
        cargo_count = monthly_cargos.count()
        
        # Calculate on-time rate safely
        if cargo_count > 0:
            on_time_count = Cargo.objects.filter(
                dispatch_date__gte=start_of_month,
                is_delayed=False,
                status='RECEIVED'
            ).count()
            on_time_rate = (on_time_count / cargo_count) * 100
        else:
            on_time_rate = 0.0
        
        monthly_summary = {
            'generated_at': timezone.now().isoformat(),
            'period': {
                'start': start_of_month.isoformat(),
                'end': today.isoformat(),
                'month': today.strftime('%B %Y')
            },
            'cargos': {
                'total': cargo_count,
                'total_value_kes': float(
                    monthly_cargos.aggregate(total=Sum('declared_value'))['total'] or 0
                ),
                'total_weight_kg': float(
                    monthly_cargos.aggregate(total=Sum('weight_kg'))['total'] or 0
                )
            },
            'suppliers': {
                'active': Supplier.objects.filter(status='ACTIVE').count(),
                'total': Supplier.objects.count()
            },
            'warehouses': {
                'active': Warehouse.objects.filter(is_active=True).count(),
                'total': Warehouse.objects.count()
            },
            'alerts': {
                'unresolved': Alert.objects.filter(
                    is_resolved=False,
                    created_at__gte=start_of_month
                ).count(),
                'critical': Alert.objects.filter(
                    severity='CRITICAL',
                    created_at__gte=start_of_month
                ).count()
            },
            'performance': {
                'on_time_rate': float(on_time_rate)
            }
        }
        
        # Convert all values to JSON-serializable types
        monthly_summary = self.convert_to_json_serializable(monthly_summary)
        
        Report.objects.create(
            report_type='MONTHLY_SUMMARY',
            title=f'Monthly Summary - {today.strftime("%B %Y")}',
            description='Automatically generated monthly system summary',
            start_date=start_of_month,
            end_date=today,
            report_data=monthly_summary
        )
        self.stdout.write(self.style.SUCCESS('✓ Monthly Summary Report created'))
        
        self.stdout.write(self.style.SUCCESS('\n✓✓✓ All reports generated successfully! ✓✓✓'))
        self.stdout.write(self.style.SUCCESS(f'Total reports created: 5'))
        self.stdout.write(self.style.SUCCESS(f'Period: {start_of_month} to {today}'))