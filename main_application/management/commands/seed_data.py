"""
Django Management Command to Seed Cargo Tracking System with Kenyan Data
File: main_application/management/commands/seed_data.py

Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
from django.db import models


from main_application.models import (
    County, Supplier, Warehouse, CargoCategory, Cargo, 
    CargoStatusHistory, SupplierPerformance, Alert
)


class Command(BaseCommand):
    help = 'Seeds the database with realistic Kenyan cargo tracking data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))
        
        # Create admin user if doesn't exist
        self.create_admin_user()
        
        # Seed data in order
        self.seed_counties()
        self.seed_cargo_categories()
        self.seed_suppliers()
        self.seed_warehouses()
        self.seed_cargo()
        self.update_supplier_performance()
        self.seed_alerts()
        
        self.stdout.write(self.style.SUCCESS('✅ Data seeding completed successfully!'))
        self.print_summary()

    def clear_data(self):
        """Clear all existing data"""
        models_to_clear = [
            Alert, CargoStatusHistory, Cargo, SupplierPerformance,
            CargoCategory, Warehouse, Supplier, County
        ]
        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'  Deleted {count} {model.__name__} records')

    def create_admin_user(self):
        """Create or get admin user for audit trails"""
        self.admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cargotrack.co.ke',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            self.admin_user.set_password('admin123')
            self.admin_user.save()
            self.stdout.write(self.style.SUCCESS('  Created admin user'))
        else:
            self.stdout.write('  Admin user already exists')

    def seed_counties(self):
        """Seed Kenyan counties"""
        self.stdout.write('Seeding Counties...')
        
        kenyan_counties = [
            ('Nairobi', 'NRB'),
            ('Mombasa', 'MBA'),
            ('Kiambu', 'KIA'),
            ('Nakuru', 'NAK'),
            ('Kisumu', 'KSM'),
            ('Machakos', 'MCH'),
            ('Kajiado', 'KAJ'),
            ('Uasin Gishu', 'UGS'),
            ('Nyeri', 'NYR'),
            ('Meru', 'MRU'),
            ('Kirinyaga', 'KRG'),
            ('Murang\'a', 'MRG'),
        ]
        
        for name, code in kenyan_counties:
            County.objects.get_or_create(name=name, code=code)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(kenyan_counties)} counties'))

    def seed_cargo_categories(self):
        """Seed cargo categories"""
        self.stdout.write('Seeding Cargo Categories...')
        
        categories = [
            ('Electronics', 'ELEC', 'Electronic goods and appliances', True),
            ('Food & Beverages', 'FOOD', 'Perishable and non-perishable food items', True),
            ('Building Materials', 'BLDG', 'Construction materials and hardware', False),
            ('Textiles & Clothing', 'TEXT', 'Fabrics, clothing, and accessories', False),
            ('Agricultural Products', 'AGRI', 'Farm produce and supplies', True),
            ('Pharmaceuticals', 'PHAR', 'Medical supplies and medicines', True),
            ('Automotive Parts', 'AUTO', 'Vehicle parts and accessories', False),
            ('General Merchandise', 'GENM', 'General goods and supplies', False),
        ]
        
        for name, code, desc, special in categories:
            CargoCategory.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': desc,
                    'requires_special_handling': special,
                    'is_active': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(categories)} cargo categories'))

    def seed_suppliers(self):
        """Seed suppliers with realistic Kenyan data"""
        self.stdout.write('Seeding Suppliers...')
        
        suppliers_data = [
            {
                'name': 'Nairobi Electronics Ltd',
                'type': 'DISTRIBUTOR',
                'kra_pin': 'P051234567M',
                'contact': 'John Mwangi',
                'phone': '+254712345678',
                'email': 'sales@nbielectronics.co.ke',
                'county': 'Nairobi',
                'town': 'Industrial Area',
                'address': 'Enterprise Road, Off Mombasa Road',
                'goods': 'Consumer electronics, home appliances, computers',
                'payment': 'Net 30',
                'credit': 5000000,
            },
            {
                'name': 'Mombasa Imports & Exports',
                'type': 'IMPORTER',
                'kra_pin': 'P052345678N',
                'contact': 'Fatuma Hassan',
                'phone': '+254723456789',
                'email': 'info@mombasaimports.co.ke',
                'county': 'Mombasa',
                'town': 'Port Reitz',
                'address': 'Shimanzi Area, Near Port',
                'goods': 'General merchandise, textiles, building materials',
                'payment': 'Advance Payment',
                'credit': 8000000,
            },
            {
                'name': 'Central Kenya Farmers Cooperative',
                'type': 'LOCAL_PRODUCER',
                'kra_pin': 'P053456789O',
                'contact': 'Peter Kamau',
                'phone': '+254734567890',
                'email': 'manager@ckfc.co.ke',
                'county': 'Nyeri',
                'town': 'Nyeri Town',
                'address': 'Kimathi Way, Nyeri',
                'goods': 'Coffee, tea, vegetables, dairy products',
                'payment': 'COD',
                'credit': 2000000,
            },
            {
                'name': 'Nakuru Hardware Supplies',
                'type': 'WHOLESALER',
                'kra_pin': 'P054567890P',
                'contact': 'David Kipchoge',
                'phone': '+254745678901',
                'email': 'orders@nakuruhardware.co.ke',
                'county': 'Nakuru',
                'town': 'Nakuru CBD',
                'address': 'Kenyatta Avenue, Nakuru',
                'goods': 'Building materials, cement, steel, hardware',
                'payment': 'Net 15',
                'credit': 4000000,
            },
            {
                'name': 'Kisumu Pharma Distributors',
                'type': 'DISTRIBUTOR',
                'kra_pin': 'P055678901Q',
                'contact': 'Dr. Grace Otieno',
                'phone': '+254756789012',
                'email': 'info@kisumupharma.co.ke',
                'county': 'Kisumu',
                'town': 'Kisumu',
                'address': 'Oginga Odinga Road, Kisumu',
                'goods': 'Pharmaceuticals, medical supplies, laboratory equipment',
                'payment': 'Net 45',
                'credit': 6000000,
            },
            {
                'name': 'East Africa Textiles Manufacturing',
                'type': 'MANUFACTURER',
                'kra_pin': 'P056789012R',
                'contact': 'Sarah Wanjiru',
                'phone': '+254767890123',
                'email': 'sales@eatextiles.co.ke',
                'county': 'Kiambu',
                'town': 'Ruiru',
                'address': 'Thika Road, Ruiru Industrial Park',
                'goods': 'Textiles, fabrics, clothing, uniforms',
                'payment': 'Net 30',
                'credit': 3500000,
            },
        ]
        
        counties = {c.name: c for c in County.objects.all()}
        
        for data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                kra_pin=data['kra_pin'],
                defaults={
                    'name': data['name'],
                    'supplier_type': data['type'],
                    'primary_contact_person': data['contact'],
                    'phone_number': data['phone'],
                    'email': data['email'],
                    'county': counties[data['county']],
                    'town_city': data['town'],
                    'physical_address': data['address'],
                    'goods_supplied': data['goods'],
                    'payment_terms': data['payment'],
                    'credit_limit': data['credit'],
                    'status': 'ACTIVE',
                    'reliability_score': Decimal(random.uniform(75, 98)),
                    'created_by': self.admin_user,
                }
            )
            
            # Create performance record
            SupplierPerformance.objects.get_or_create(supplier=supplier)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(suppliers_data)} suppliers'))

    def seed_warehouses(self):
        """Seed warehouses"""
        self.stdout.write('Seeding Warehouses...')
        
        warehouses_data = [
            {
                'name': 'Nairobi Central Warehouse',
                'type': 'MAIN',
                'county': 'Nairobi',
                'town': 'Embakasi',
                'address': 'Mombasa Road, Embakasi',
                'gps': '-1.3167, 36.9333',
                'capacity': 5000,
                'manager': 'James Ochieng',
                'phone': '+254711111111',
                'email': 'manager.nairobi@warehouse.co.ke',
                'hours': 'Mon-Fri 7AM-7PM, Sat 8AM-5PM',
            },
            {
                'name': 'Mombasa Port Warehouse',
                'type': 'REGIONAL',
                'county': 'Mombasa',
                'town': 'Changamwe',
                'address': 'Port Reitz Road, Changamwe',
                'gps': '-4.0435, 39.6682',
                'capacity': 8000,
                'manager': 'Ali Mohammed',
                'phone': '+254722222222',
                'email': 'manager.mombasa@warehouse.co.ke',
                'hours': 'Mon-Sat 6AM-8PM',
            },
            {
                'name': 'Nakuru Distribution Center',
                'type': 'REGIONAL',
                'county': 'Nakuru',
                'town': 'Nakuru',
                'address': 'Nairobi-Nakuru Highway',
                'gps': '-0.3031, 36.0800',
                'capacity': 3000,
                'manager': 'Mary Chepkemoi',
                'phone': '+254733333333',
                'email': 'manager.nakuru@warehouse.co.ke',
                'hours': 'Mon-Fri 8AM-6PM, Sat 8AM-2PM',
            },
            {
                'name': 'Kisumu Storage Facility',
                'type': 'STORAGE',
                'county': 'Kisumu',
                'town': 'Kisumu',
                'address': 'Kisumu-Busia Road',
                'gps': '-0.0917, 34.7680',
                'capacity': 2500,
                'manager': 'Tom Otieno',
                'phone': '+254744444444',
                'email': 'manager.kisumu@warehouse.co.ke',
                'hours': 'Mon-Fri 8AM-5PM',
            },
        ]
        
        counties = {c.name: c for c in County.objects.all()}
        
        for data in warehouses_data:
            Warehouse.objects.get_or_create(
                name=data['name'],
                defaults={
                    'warehouse_type': data['type'],
                    'county': counties[data['county']],
                    'town_city': data['town'],
                    'physical_address': data['address'],
                    'gps_coordinates': data['gps'],
                    'total_capacity_sqm': data['capacity'],
                    'current_utilization_sqm': Decimal(random.uniform(500, data['capacity'] * 0.8)),
                    'manager_name': data['manager'],
                    'manager_phone': data['phone'],
                    'manager_email': data['email'],
                    'operating_hours': data['hours'],
                    'is_active': True,
                    'created_by': self.admin_user,
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(warehouses_data)} warehouses'))

    def seed_cargo(self):
        """Seed cargo shipments"""
        self.stdout.write('Seeding Cargo Shipments...')
        
        suppliers = list(Supplier.objects.all())
        warehouses = list(Warehouse.objects.all())
        categories = list(CargoCategory.objects.all())
        
        statuses = ['DISPATCHED', 'IN_TRANSIT', 'ARRIVED', 'RECEIVED', 'STORED']
        transport_modes = ['ROAD', 'RAIL', 'MULTIMODAL']
        priorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']
        
        cargo_descriptions = [
            'Carton of LED TVs - 32 inch',
            'Bags of Maize - Grade A',
            'Boxes of Paracetamol Tablets',
            'Cement bags - 50kg',
            'Rolls of Cotton Fabric',
            'Crates of Fresh Vegetables',
            'Boxes of Mobile Phones',
            'Steel Rods - 12mm diameter',
            'Cartons of Cooking Oil',
            'Pharmaceutical Supplies Mixed',
        ]
        
        # Create 25 cargo shipments
        for i in range(25):
            supplier = random.choice(suppliers)
            warehouse = random.choice(warehouses)
            category = random.choice(categories)
            
            dispatch_date = timezone.now() - timedelta(days=random.randint(1, 60))
            expected_hours = random.randint(12, 72)
            expected_arrival = dispatch_date + timedelta(hours=expected_hours)
            
            status = random.choice(statuses)
            
            # Determine actual arrival based on status
            if status in ['ARRIVED', 'RECEIVED', 'STORED']:
                delay_factor = random.uniform(-0.2, 0.3)  # -20% early to +30% late
                actual_hours = expected_hours * (1 + delay_factor)
                actual_arrival = dispatch_date + timedelta(hours=actual_hours)
                received_date = actual_arrival + timedelta(hours=random.randint(1, 8)) if status == 'RECEIVED' else None
            else:
                actual_arrival = None
                received_date = None
            
            cargo = Cargo.objects.create(
                supplier=supplier,
                warehouse=warehouse,
                category=category,
                description=random.choice(cargo_descriptions),
                quantity=random.randint(10, 500),
                unit_of_measurement=random.choice(['PCS', 'KG', 'BOXES', 'PALLETS']),
                weight_kg=Decimal(random.uniform(100, 5000)),
                volume_cbm=Decimal(random.uniform(5, 50)),
                declared_value=Decimal(random.uniform(50000, 5000000)),
                insurance_value=Decimal(random.uniform(60000, 5500000)),
                dispatch_date=dispatch_date,
                expected_arrival_date=expected_arrival,
                actual_arrival_date=actual_arrival,
                received_date=received_date,
                transport_mode=random.choice(transport_modes),
                vehicle_registration=f'KX{random.randint(100, 999)}{random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")}',
                driver_name=random.choice(['John Mwangi', 'Peter Kamau', 'James Otieno', 'David Kipchoge']),
                driver_phone=f'+2547{random.randint(10000000, 99999999)}',
                status=status,
                priority=random.choice(priorities),
                storage_location=f'Aisle {random.randint(1, 10)}, Bay {random.randint(1, 20)}' if status in ['RECEIVED', 'STORED'] else None,
                purchase_order_number=f'PO-2024-{random.randint(1000, 9999)}',
                invoice_number=f'INV-{random.randint(10000, 99999)}',
                condition_on_arrival=random.choice(['EXCELLENT', 'GOOD', 'GOOD', 'GOOD', 'FAIR']) if actual_arrival else None,
                quality_check_passed=random.choice([True, True, True, False]) if status == 'RECEIVED' else False,
                created_by=self.admin_user,
            )
            
            # Create status history
            if status != 'DISPATCHED':
                previous_statuses = ['DISPATCHED', 'IN_TRANSIT']
                if status in ['ARRIVED', 'RECEIVED', 'STORED']:
                    previous_statuses.append('ARRIVED')
                
                for prev_status in previous_statuses:
                    CargoStatusHistory.objects.create(
                        cargo=cargo,
                        from_status=prev_status if prev_status != previous_statuses[0] else 'PENDING',
                        to_status=prev_status,
                        change_reason='Normal progression',
                        location=warehouse.name,
                        created_by=self.admin_user,
                    )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Created 25 cargo shipments'))

    def update_supplier_performance(self):
        """Calculate supplier performance metrics"""
        self.stdout.write('Calculating Supplier Performance...')
        
        for performance in SupplierPerformance.objects.all():
            performance.calculate_metrics()
        
        self.stdout.write(self.style.SUCCESS('  ✓ Updated supplier performance metrics'))

    def seed_alerts(self):
        """Create some alerts"""
        self.stdout.write('Seeding Alerts...')
        
        delayed_cargos = Cargo.objects.filter(is_delayed=True)[:3]
        
        for cargo in delayed_cargos:
            Alert.objects.create(
                alert_type='DELAY',
                severity='WARNING',
                title=f'Delivery Delay - {cargo.cargo_id}',
                message=f'Cargo {cargo.cargo_id} from {cargo.supplier.name} is delayed by {cargo.estimated_delay_hours:.1f} hours.',
                cargo=cargo,
                supplier=cargo.supplier,
                warehouse=cargo.warehouse,
                is_read=False,
                created_by=self.admin_user,
            )
        
        # Warehouse capacity warning
        full_warehouses = Warehouse.objects.filter(
            current_utilization_sqm__gte=0.85 * models.F('total_capacity_sqm')
        )[:2]
        
        for warehouse in full_warehouses:
            Alert.objects.create(
                alert_type='CAPACITY',
                severity='WARNING',
                title=f'Warehouse Capacity Warning - {warehouse.name}',
                message=f'{warehouse.name} is at {warehouse.capacity_utilization_percentage:.1f}% capacity.',
                warehouse=warehouse,
                is_read=False,
                created_by=self.admin_user,
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Created alerts'))

    def print_summary(self):
        """Print summary of seeded data"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('DATA SEEDING SUMMARY'))
        self.stdout.write('='*50)
        self.stdout.write(f'Counties: {County.objects.count()}')
        self.stdout.write(f'Cargo Categories: {CargoCategory.objects.count()}')
        self.stdout.write(f'Suppliers: {Supplier.objects.count()}')
        self.stdout.write(f'Warehouses: {Warehouse.objects.count()}')
        self.stdout.write(f'Cargo Shipments: {Cargo.objects.count()}')
        self.stdout.write(f'Status History Records: {CargoStatusHistory.objects.count()}')
        self.stdout.write(f'Supplier Performance Records: {SupplierPerformance.objects.count()}')
        self.stdout.write(f'Alerts: {Alert.objects.count()}')
        self.stdout.write('='*50 + '\n')