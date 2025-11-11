"""
Cargo Tracking Management Information System - Django Models
Professional-grade models for tracking cargo shipments from multiple suppliers to warehouses in Kenya.
Designed for scalability, audit trails, and comprehensive supplier performance analytics.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class TimeStampedModel(models.Model):
    """Abstract base model for timestamp and audit tracking"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='%(class)s_created', verbose_name='Created By'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_updated', verbose_name='Last Updated By'
    )

    class Meta:
        abstract = True


class County(models.Model):
    """Kenyan Counties for location tracking"""
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=3, unique=True)
    
    class Meta:
        verbose_name_plural = 'Counties'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Supplier(TimeStampedModel):
    """Supplier/Vendor management with KRA PIN validation"""
    SUPPLIER_TYPE_CHOICES = [
        ('MANUFACTURER', 'Manufacturer'),
        ('DISTRIBUTOR', 'Distributor'),
        ('IMPORTER', 'Importer'),
        ('WHOLESALER', 'Wholesaler'),
        ('LOCAL_PRODUCER', 'Local Producer'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('BLACKLISTED', 'Blacklisted'),
    ]
    
    supplier_id = models.CharField(
        max_length=20, unique=True, editable=False,
        help_text='Auto-generated unique supplier ID'
    )
    name = models.CharField(max_length=200, db_index=True)
    supplier_type = models.CharField(max_length=20, choices=SUPPLIER_TYPE_CHOICES)
    
    # Kenyan-specific fields
    kra_pin = models.CharField(
        max_length=11, unique=True, 
        validators=[RegexValidator(
            regex=r'^[AP]\d{9}[A-Z]$',
            message='Enter valid KRA PIN (e.g., P051234567M)'
        )],
        verbose_name='KRA PIN Number'
    )
    
    # Contact information
    primary_contact_person = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+254[17]\d{8}$',
            message='Enter valid Kenyan phone number (+254...)'
        )]
    )
    email = models.EmailField()
    alternative_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Physical address
    physical_address = models.TextField()
    county = models.ForeignKey(County, on_delete=models.PROTECT)
    town_city = models.CharField(max_length=100)
    postal_address = models.CharField(max_length=100, blank=True, null=True)
    
    # Business details
    goods_supplied = models.TextField(
        help_text='Description of goods/products supplied'
    )
    payment_terms = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='e.g., Net 30, COD, Advance Payment'
    )
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Status and ratings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    reliability_score = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Auto-calculated based on delivery performance (0-100)'
    )
    
    # Notes and attachments
    notes = models.TextField(blank=True, null=True)
    registration_certificate = models.FileField(
        upload_to='suppliers/certificates/', blank=True, null=True
    )
    
    class Meta:
        ordering = ['-reliability_score', 'name']
        indexes = [
            models.Index(fields=['status', 'supplier_type']),
            models.Index(fields=['kra_pin']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.supplier_id:
            # Generate unique supplier ID: SUP-YYYY-XXXXX
            year = timezone.now().year
            last_supplier = Supplier.objects.filter(
                supplier_id__startswith=f'SUP-{year}-'
            ).order_by('supplier_id').last()
            
            if last_supplier:
                last_num = int(last_supplier.supplier_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.supplier_id = f'SUP-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.supplier_id} - {self.name}"


class Warehouse(TimeStampedModel):
    """Warehouse/Storage facility management"""
    WAREHOUSE_TYPE_CHOICES = [
        ('MAIN', 'Main Warehouse'),
        ('REGIONAL', 'Regional Distribution Center'),
        ('STORAGE', 'Storage Facility'),
        ('COLD_STORAGE', 'Cold Storage'),
    ]
    
    warehouse_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=200)
    warehouse_type = models.CharField(max_length=20, choices=WAREHOUSE_TYPE_CHOICES)
    
    # Location
    county = models.ForeignKey(County, on_delete=models.PROTECT)
    town_city = models.CharField(max_length=100)
    physical_address = models.TextField()
    gps_coordinates = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='Latitude, Longitude'
    )
    
    # Capacity
    total_capacity_sqm = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Total Capacity (Square Meters)'
    )
    current_utilization_sqm = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Current Utilization (Square Meters)'
    )
    
    # Contact
    manager_name = models.CharField(max_length=100)
    manager_phone = models.CharField(max_length=15)
    manager_email = models.EmailField()
    
    # Operational details
    operating_hours = models.CharField(
        max_length=100, 
        help_text='e.g., Mon-Fri 8AM-6PM, Sat 8AM-2PM'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.warehouse_id:
            year = timezone.now().year
            last_wh = Warehouse.objects.filter(
                warehouse_id__startswith=f'WH-{year}-'
            ).order_by('warehouse_id').last()
            
            if last_wh:
                last_num = int(last_wh.warehouse_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.warehouse_id = f'WH-{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.warehouse_id} - {self.name}"
    
    @property
    def capacity_utilization_percentage(self):
        """Calculate warehouse capacity utilization"""
        if self.total_capacity_sqm > 0:
            return (self.current_utilization_sqm / self.total_capacity_sqm) * 100
        return 0


class CargoCategory(models.Model):
    """Cargo classification for better tracking"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, null=True)
    requires_special_handling = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Cargo Categories'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Cargo(TimeStampedModel):
    """Main cargo shipment tracking"""
    STATUS_CHOICES = [
        ('DISPATCHED', 'Dispatched'),
        ('IN_TRANSIT', 'In Transit'),
        ('ARRIVED', 'Arrived at Warehouse'),
        ('RECEIVED', 'Received in Warehouse'),
        ('STORED', 'Stored'),
        ('DELAYED', 'Delayed'),
        ('CANCELLED', 'Cancelled'),
        ('DAMAGED', 'Damaged'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('URGENT', 'Urgent'),
    ]
    
    # Identification
    cargo_id = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    tracking_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Relationships
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name='cargos'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name='cargos'
    )
    category = models.ForeignKey(
        CargoCategory, on_delete=models.PROTECT, related_name='cargos'
    )
    
    # Cargo details
    description = models.TextField(help_text='Detailed description of goods')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_of_measurement = models.CharField(
        max_length=20, default='PCS',
        help_text='e.g., PCS, KG, TONS, BOXES, PALLETS'
    )
    weight_kg = models.DecimalField(
        max_digits=10, decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Weight (KG)'
    )
    volume_cbm = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Volume (Cubic Meters)'
    )
    
    # Valuation
    declared_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Value in KES'
    )
    insurance_value = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text='Insurance value in KES'
    )
    
    # Shipment details
    dispatch_date = models.DateTimeField(db_index=True)
    expected_arrival_date = models.DateTimeField(db_index=True)
    actual_arrival_date = models.DateTimeField(blank=True, null=True)
    received_date = models.DateTimeField(blank=True, null=True)
    
    # Transport details
    transport_mode = models.CharField(
        max_length=20,
        choices=[
            ('ROAD', 'Road Transport'),
            ('RAIL', 'Rail Transport'),
            ('AIR', 'Air Freight'),
            ('SEA', 'Sea Freight'),
            ('MULTIMODAL', 'Multimodal'),
        ],
        default='ROAD'
    )
    vehicle_registration = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Vehicle/Container registration number'
    )
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    driver_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Status and priority
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, 
        default='DISPATCHED', db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM'
    )
    
    # Performance metrics
    delivery_duration_hours = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text='Auto-calculated delivery time in hours'
    )
    is_delayed = models.BooleanField(default=False, db_index=True)
    delay_reason = models.TextField(blank=True, null=True)
    
    # Storage details
    storage_location = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Specific location within warehouse (e.g., Aisle 3, Bay 5)'
    )
    
    # Documentation
    purchase_order_number = models.CharField(max_length=50, blank=True, null=True)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    delivery_note_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Quality and condition
    condition_on_arrival = models.CharField(
        max_length=20,
        choices=[
            ('EXCELLENT', 'Excellent'),
            ('GOOD', 'Good'),
            ('FAIR', 'Fair'),
            ('DAMAGED', 'Damaged'),
        ],
        blank=True, null=True
    )
    quality_check_passed = models.BooleanField(default=False)
    inspection_notes = models.TextField(blank=True, null=True)
    
    # Additional fields
    special_instructions = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = 'Cargos'
        ordering = ['-dispatch_date']
        indexes = [
            models.Index(fields=['status', 'warehouse']),
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['dispatch_date', 'expected_arrival_date']),
            models.Index(fields=['is_delayed']),
        ]
    
    def save(self, *args, **kwargs):
        # Generate cargo ID
        if not self.cargo_id:
            year = timezone.now().year
            month = timezone.now().month
            last_cargo = Cargo.objects.filter(
                cargo_id__startswith=f'CRG-{year}{month:02d}-'
            ).order_by('cargo_id').last()
            
            if last_cargo:
                last_num = int(last_cargo.cargo_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.cargo_id = f'CRG-{year}{month:02d}-{new_num:06d}'
        
        # Calculate delivery duration
        if self.actual_arrival_date and self.dispatch_date:
            duration = self.actual_arrival_date - self.dispatch_date
            self.delivery_duration_hours = Decimal(duration.total_seconds() / 3600)
        
        # Check if delayed
        if self.actual_arrival_date and self.expected_arrival_date:
            self.is_delayed = self.actual_arrival_date > self.expected_arrival_date
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cargo_id} - {self.description[:50]}"
    
    @property
    def estimated_delay_hours(self):
        """Calculate estimated delay in hours"""
        if self.is_delayed and self.actual_arrival_date:
            delay = self.actual_arrival_date - self.expected_arrival_date
            return delay.total_seconds() / 3600
        return 0


class CargoStatusHistory(TimeStampedModel):
    """Track all status changes for audit trail"""
    cargo = models.ForeignKey(
        Cargo, on_delete=models.CASCADE, related_name='status_history'
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    change_reason = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = 'Cargo Status Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cargo', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.cargo.cargo_id}: {self.from_status} → {self.to_status}"


class SupplierPerformance(models.Model):
    """Aggregated supplier performance metrics"""
    supplier = models.OneToOneField(
        Supplier, on_delete=models.CASCADE, related_name='performance'
    )
    
    # Delivery metrics
    total_deliveries = models.PositiveIntegerField(default=0)
    on_time_deliveries = models.PositiveIntegerField(default=0)
    delayed_deliveries = models.PositiveIntegerField(default=0)
    cancelled_deliveries = models.PositiveIntegerField(default=0)
    
    # Time metrics
    average_delivery_time_hours = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    fastest_delivery_hours = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    slowest_delivery_hours = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    
    # Quality metrics
    total_cargo_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    damaged_cargo_count = models.PositiveIntegerField(default=0)
    quality_issues_count = models.PositiveIntegerField(default=0)
    
    # Performance score (0-100)
    overall_performance_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Ratings
    on_time_delivery_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Percentage of on-time deliveries'
    )
    
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Supplier Performance Records'
        ordering = ['-overall_performance_score']

    @property
    def quality_score(self):
        total = self.total_deliveries or 1
        good_quality = total - (self.damaged_cargo_count + self.quality_issues_count)
        return (good_quality / total) * 100
    
    def __str__(self):
        return f"{self.supplier.name} - Score: {self.overall_performance_score}"
    
    def calculate_metrics(self):
        """Recalculate all performance metrics"""
        from django.db.models import Avg, Count, Q
        
        cargos = Cargo.objects.filter(supplier=self.supplier)
        
        self.total_deliveries = cargos.count()
        self.on_time_deliveries = cargos.filter(is_delayed=False, status='RECEIVED').count()
        self.delayed_deliveries = cargos.filter(is_delayed=True).count()
        self.cancelled_deliveries = cargos.filter(status='CANCELLED').count()
        
        # Calculate average delivery time
        avg_time = cargos.filter(
            delivery_duration_hours__isnull=False
        ).aggregate(Avg('delivery_duration_hours'))
        self.average_delivery_time_hours = avg_time['delivery_duration_hours__avg'] or 0
        
        # On-time delivery rate
        if self.total_deliveries > 0:
            self.on_time_delivery_rate = (self.on_time_deliveries / self.total_deliveries) * 100
        
        # Calculate overall performance score
        if self.total_deliveries > 0:
            on_time_weight = 50
            quality_weight = 30
            volume_weight = 20
            
            on_time_score = (self.on_time_deliveries / self.total_deliveries) * on_time_weight
            quality_score = ((self.total_deliveries - self.damaged_cargo_count - self.quality_issues_count) / 
                           self.total_deliveries) * quality_weight
            volume_score = min((self.total_deliveries / 100) * volume_weight, volume_weight)
            
            self.overall_performance_score = on_time_score + quality_score + volume_score
        
        self.save()


class Alert(TimeStampedModel):
    """System alerts and notifications"""
    ALERT_TYPE_CHOICES = [
        ('DELAY', 'Delivery Delay'),
        ('ARRIVAL', 'Cargo Arrival'),
        ('CAPACITY', 'Warehouse Capacity Warning'),
        ('SUPPLIER_ISSUE', 'Supplier Performance Issue'),
        ('QUALITY', 'Quality Concern'),
        ('SYSTEM', 'System Alert'),
    ]
    
    SEVERITY_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    cargo = models.ForeignKey(
        Cargo, on_delete=models.CASCADE, blank=True, null=True,
        related_name='alerts'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, blank=True, null=True,
        related_name='alerts'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, blank=True, null=True,
        related_name='alerts'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='resolved_alerts'
    )
    resolution_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_read', 'severity']),
            models.Index(fields=['alert_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.severity} - {self.title}"


class Report(TimeStampedModel):
    """Generated reports for management"""
    REPORT_TYPE_CHOICES = [
        ('SUPPLIER_PERFORMANCE', 'Supplier Performance Report'),
        ('CARGO_MOVEMENT', 'Cargo Movement Report'),
        ('INVENTORY_SUMMARY', 'Inventory Summary'),
        ('DELIVERY_ANALYSIS', 'Delivery Analysis'),
        ('MONTHLY_SUMMARY', 'Monthly Summary'),
        ('CUSTOM', 'Custom Report'),
    ]
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Report data (stored as JSON)
    report_data = models.JSONField()
    
    # File attachment
    report_file = models.FileField(
        upload_to='reports/%Y/%m/', blank=True, null=True,
        help_text='PDF or Excel export of the report'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"