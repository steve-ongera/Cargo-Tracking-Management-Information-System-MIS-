# 🚚 Cargo Tracking Management Information System (MIS)

**Professional Cargo & Supplier Management Solution for Kenyan Businesses**

![Django](https://img.shields.io/badge/Django-5.0-green.svg)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-Commercial-red.svg)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Initial Setup](#initial-setup)
- [Database Schema](#database-schema)
- [User Roles](#user-roles)
- [Core Modules](#core-modules)
- [API Endpoints](#api-endpoints)
- [Reports & Analytics](#reports--analytics)
- [Kenya-Specific Features](#kenya-specific-features)
- [Security Features](#security-features)
- [Deployment Guide](#deployment-guide)
- [Troubleshooting](#troubleshooting)
- [Support & Contact](#support--contact)
- [License](#license)

---

## 🎯 Overview

The **Cargo Tracking MIS** is a comprehensive, enterprise-grade solution designed specifically for Kenyan warehouses and logistics operations. It tracks cargo shipments from multiple suppliers to warehouses, monitors delivery performance, and provides actionable insights for management decision-making.

### Problem Solved

- ✅ Eliminates manual tracking of supplier deliveries
- ✅ Provides real-time cargo status visibility
- ✅ Automates supplier performance analytics
- ✅ Reduces inventory discrepancies
- ✅ Improves supplier accountability
- ✅ Enables data-driven procurement decisions

### Target Market

- Wholesale & Distribution Companies
- Manufacturing Facilities
- Retail Chains with Multiple Suppliers
- Import/Export Businesses
- Third-Party Logistics (3PL) Providers
- Government Procurement Departments

---

## ⚡ Key Features

### 📦 Cargo Management
- **Unique Tracking IDs**: Auto-generated cargo IDs (CRG-202511-000001)
- **Multi-Status Tracking**: Dispatched → In Transit → Arrived → Received → Stored
- **Real-Time Updates**: Live status updates with timestamp tracking
- **Delivery Duration Calculation**: Automatic computation of delivery times
- **Delay Detection**: Automated alerts for late deliveries
- **Quality Control**: Record condition on arrival and inspection notes

### 🏢 Supplier Management
- **KRA PIN Validation**: Integrated Kenyan tax compliance
- **Performance Scoring**: Automated reliability scores (0-100)
- **Multi-Supplier Support**: Manage unlimited suppliers
- **Contact Management**: Complete supplier contact information
- **Document Storage**: Upload registration certificates and documents
- **Status Control**: Active, Inactive, Suspended, Blacklisted statuses

### 📊 Analytics & Reporting
- **Supplier Performance Dashboard**: Rankings by delivery efficiency
- **Delivery Analytics**: On-time vs delayed delivery analysis
- **Inventory Summaries**: Real-time warehouse stock levels
- **Custom Reports**: Generate periodic performance reports
- **Export Capabilities**: PDF and Excel report exports
- **Visual Dashboards**: Charts and graphs for key metrics

### 🏭 Warehouse Management
- **Multi-Warehouse Support**: Manage multiple storage facilities
- **Capacity Tracking**: Monitor warehouse utilization
- **Location Management**: Track cargo storage locations
- **County-Based Routing**: Kenya-specific location tracking
- **Manager Assignment**: Warehouse manager contact details

### 🔔 Smart Alerts
- **Delivery Delays**: Automatic notifications for late shipments
- **Capacity Warnings**: Alert when warehouse near capacity
- **Quality Issues**: Notifications for damaged cargo
- **Arrival Notifications**: Real-time arrival alerts
- **Supplier Issues**: Performance degradation alerts

### 🔐 Audit & Security
- **Complete Audit Trail**: Track who created/modified every record
- **User Authentication**: Secure login system
- **Role-Based Access**: Warehouse Manager, Logistics Officer, Admin
- **Data Integrity**: Validation on all critical fields
- **Change History**: Full history of cargo status changes

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | Django 5.0+ |
| **Database** | SQLite (Development) / PostgreSQL (Production) |
| **Programming Language** | Python 3.10+ |
| **Admin Interface** | Django Admin (Enhanced) |
| **Authentication** | Django Auth System |
| **Form Validation** | Django Validators |
| **Frontend** | Django Templates / Bootstrap 5 |

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, Ubuntu 20.04+, macOS 11+
- **Python**: 3.10 or higher
- **RAM**: 4GB minimum
- **Storage**: 10GB available space
- **Database**: SQLite (included) or PostgreSQL 12+

### Recommended for Production
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.11+
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Database**: PostgreSQL 15+
- **Web Server**: Nginx + Gunicorn

---

## 📥 Installation

### 1. Clone or Extract Project

```bash
# If using Git
git clone https://github.com/yourusername/cargo-tracking-mis.git
cd cargo-tracking-mis

# Or extract from ZIP
unzip cargo-tracking-mis.zip
cd cargo-tracking-mis
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install django==5.0
pip install pillow  # For image handling
pip install python-decouple  # For environment variables
pip install whitenoise  # For static files in production
```

### 4. Create Django Project Structure

```bash
django-admin startproject cargo_system .
python manage.py startapp tracking
```

### 5. Add Models and Admin Files

Copy the provided `models.py` and `admin.py` files into the `tracking` app directory:

```
tracking/
├── __init__.py
├── admin.py          # Copy provided admin.py here
├── models.py         # Copy provided models.py here
├── apps.py
├── views.py
└── migrations/
```

### 6. Configure Settings

Edit `cargo_system/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tracking',  # Add this
]

# Database (SQLite for development)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# For Production (PostgreSQL)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'cargo_tracking_db',
#         'USER': 'your_db_user',
#         'PASSWORD': 'your_db_password',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Timezone (Kenya)
TIME_ZONE = 'Africa/Nairobi'
USE_TZ = True
```

---

## 🚀 Initial Setup

### 1. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser

```bash
python manage.py createsuperuser

# Follow prompts:
# Username: admin
# Email: admin@kencomsoftware.co.ke
# Password: ********
```

### 3. Load Kenyan Counties (Optional)

Create a management command to load counties:

```python
# tracking/management/commands/load_counties.py
from django.core.management.base import BaseCommand
from tracking.models import County

class Command(BaseCommand):
    help = 'Load Kenyan counties'

    def handle(self, *args, **kwargs):
        counties = [
            ('Mombasa', '001'), ('Kwale', '002'), ('Kilifi', '003'),
            ('Tana River', '004'), ('Lamu', '005'), ('Taita Taveta', '006'),
            ('Garissa', '007'), ('Wajir', '008'), ('Mandera', '009'),
            ('Marsabit', '010'), ('Isiolo', '011'), ('Meru', '012'),
            ('Tharaka Nithi', '013'), ('Embu', '014'), ('Kitui', '015'),
            ('Machakos', '016'), ('Makueni', '017'), ('Nyandarua', '018'),
            ('Nyeri', '019'), ('Kirinyaga', '020'), ('Murang\'a', '021'),
            ('Kiambu', '022'), ('Turkana', '023'), ('West Pokot', '024'),
            ('Samburu', '025'), ('Trans Nzoia', '026'), ('Uasin Gishu', '027'),
            ('Elgeyo Marakwet', '028'), ('Nandi', '029'), ('Baringo', '030'),
            ('Laikipia', '031'), ('Nakuru', '032'), ('Narok', '033'),
            ('Kajiado', '034'), ('Kericho', '035'), ('Bomet', '036'),
            ('Kakamega', '037'), ('Vihiga', '038'), ('Bungoma', '039'),
            ('Busia', '040'), ('Siaya', '041'), ('Kisumu', '042'),
            ('Homa Bay', '043'), ('Migori', '044'), ('Kisii', '045'),
            ('Nyamira', '046'), ('Nairobi', '047')
        ]
        
        for name, code in counties:
            County.objects.get_or_create(name=name, code=code)
            self.stdout.write(f'Created: {name}')
```

Run the command:

```bash
python manage.py load_counties
```

### 4. Start Development Server

```bash
python manage.py runserver
```

Access the system:
- **Admin Panel**: http://localhost:8000/admin
- **Login**: Use the superuser credentials created earlier

---

## 📊 Database Schema

### Core Tables

| Table | Description | Key Fields |
|-------|-------------|-----------|
| **County** | Kenyan counties | name, code |
| **Supplier** | Supplier information | supplier_id, name, kra_pin, reliability_score |
| **Warehouse** | Warehouse facilities | warehouse_id, name, capacity |
| **CargoCategory** | Cargo classifications | code, name |
| **Cargo** | Main cargo tracking | cargo_id, status, dispatch_date, supplier, warehouse |
| **CargoStatusHistory** | Audit trail | cargo, from_status, to_status, timestamp |
| **SupplierPerformance** | Performance metrics | supplier, total_deliveries, on_time_rate |
| **Alert** | System notifications | alert_type, severity, is_resolved |
| **Report** | Generated reports | report_type, start_date, end_date |

### Relationships
- Supplier → Cargo (One-to-Many)
- Warehouse → Cargo (One-to-Many)
- Cargo → CargoStatusHistory (One-to-Many)
- Supplier → SupplierPerformance (One-to-One)
- County → Supplier/Warehouse (One-to-Many)

---

## 👥 User Roles

### System Administrator
- Full system access
- User management
- System configuration
- Database maintenance
- Report generation

### Warehouse Manager
- View all cargo shipments
- Monitor warehouse operations
- Generate reports
- Review supplier performance
- Make strategic decisions

### Logistics Officer
- Register cargo dispatches
- Update cargo status
- Record supplier information
- Track deliveries
- Document quality issues

### Supplier (Optional Portal Access)
- View their shipments
- Update delivery status
- Upload documentation
- View performance metrics

---

## 🔧 Core Modules

### 1. Supplier Management Module

**Features:**
- Add/Edit/Delete suppliers
- KRA PIN validation
- Performance tracking
- Contact management
- Document uploads

**Key Operations:**
```python
# Create supplier
supplier = Supplier.objects.create(
    name="ABC Distributors",
    kra_pin="P051234567M",
    supplier_type="DISTRIBUTOR",
    phone_number="+254712345678",
    email="info@abcdist.co.ke",
    county=county_nairobi
)

# Calculate performance
performance = supplier.performance
performance.calculate_metrics()
```

### 2. Cargo Tracking Module

**Features:**
- Register new cargo
- Update status
- Track location
- Calculate delivery time
- Flag delays

**Status Workflow:**
```
DISPATCHED → IN_TRANSIT → ARRIVED → RECEIVED → STORED
```

**Key Operations:**
```python
# Register cargo
cargo = Cargo.objects.create(
    supplier=supplier,
    warehouse=warehouse,
    description="Electronics - 100 TV Units",
    quantity=100,
    weight_kg=500,
    dispatch_date=timezone.now(),
    expected_arrival_date=timezone.now() + timedelta(days=3)
)

# Update status
cargo.status = 'IN_TRANSIT'
cargo.save()
```

### 3. Analytics Module

**Available Metrics:**
- Total shipments per supplier
- Average delivery time
- On-time delivery percentage
- Delayed shipments count
- Cargo value totals
- Warehouse utilization

**Generate Report:**
```python
from tracking.models import Report

report = Report.objects.create(
    report_type='SUPPLIER_PERFORMANCE',
    title='Q4 2025 Supplier Analysis',
    start_date='2025-10-01',
    end_date='2025-12-31',
    report_data={...}
)
```

---

## 📈 Reports & Analytics

### Available Reports

1. **Supplier Performance Report**
   - Delivery reliability scores
   - On-time delivery rates
   - Average delivery times
   - Quality metrics

2. **Cargo Movement Report**
   - Total shipments by period
   - Status distribution
   - Delayed shipments analysis

3. **Inventory Summary**
   - Current stock levels
   - Warehouse utilization
   - Storage locations

4. **Monthly Summary Report**
   - Executive dashboard
   - KPIs and trends
   - Comparative analysis

### Accessing Reports

1. Navigate to **Admin Panel**
2. Go to **Reports** section
3. Click **Add Report**
4. Select report type and date range
5. Click **Generate**
6. Download as PDF or Excel

---

## 🇰🇪 Kenya-Specific Features

### 1. KRA PIN Validation
Validates Kenyan tax registration numbers:
- Format: P051234567M (for companies) or A051234567M (for individuals)
- Automatic validation on supplier registration

### 2. Phone Number Validation
Kenyan phone format:
- Format: +254712345678 or +254722345678
- Safaricom, Airtel, Telkom networks supported

### 3. County-Based Location System
- All 47 Kenyan counties pre-loaded
- Used for supplier and warehouse location
- Regional analytics and routing

### 4. Currency & Pricing
- All valuations in Kenya Shillings (KES)
- Supports large transaction values
- Decimal precision for accuracy

### 5. Local Business Compliance
- VAT tracking capability
- Credit terms management
- Payment terms documentation

---

## 🔐 Security Features

### Authentication & Authorization
- Django built-in authentication
- Role-based access control
- Session management
- Password encryption (PBKDF2)

### Data Protection
- SQL injection prevention
- XSS protection
- CSRF tokens
- Input validation
- Secure file uploads

### Audit Trail
- User action logging
- Created by / Updated by tracking
- Timestamp on all operations
- Change history for cargo status

### Best Practices
```python
# In settings.py for production
DEBUG = False
ALLOWED_HOSTS = ['kencomsoftware.co.ke', 'www.kencomsoftware.co.ke']
SECRET_KEY = env('SECRET_KEY')  # Use environment variable
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🌐 Deployment Guide

### Production Checklist

- [ ] Set `DEBUG = False`
- [ ] Configure allowed hosts
- [ ] Use PostgreSQL database
- [ ] Set up static file serving
- [ ] Configure media file storage
- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Set up backup system
- [ ] Configure monitoring
- [ ] Set up error logging

### Deployment on Ubuntu Server

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib

# 3. Create database
sudo -u postgres psql
CREATE DATABASE cargo_tracking_db;
CREATE USER cargo_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE cargo_tracking_db TO cargo_user;
\q

# 4. Clone project
cd /var/www
git clone your-repo.git cargo-tracking
cd cargo-tracking

# 5. Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# 7. Run migrations
python manage.py migrate
python manage.py collectstatic

# 8. Set up Gunicorn
pip install gunicorn
gunicorn cargo_system.wsgi:application --bind 0.0.0.0:8000

# 9. Configure Nginx (see nginx config below)

# 10. Set up supervisor for process management
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name kencomsoftware.co.ke;

    location /static/ {
        alias /var/www/cargo-tracking/staticfiles/;
    }

    location /media/ {
        alias /var/www/cargo-tracking/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: Migration errors
```bash
# Solution: Reset migrations
python manage.py migrate --fake tracking zero
python manage.py migrate tracking
```

**Issue**: Static files not loading
```bash
# Solution: Collect static files
python manage.py collectstatic --clear
```

**Issue**: Permission denied errors
```bash
# Solution: Fix file permissions
chmod -R 755 /var/www/cargo-tracking
chown -R www-data:www-data /var/www/cargo-tracking
```

**Issue**: Database connection errors
```bash
# Solution: Check PostgreSQL service
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

---

##  Support & Contact

### Technical Support
- **Email**: steveongera001@gmail.com
- **Phone**: +254 700 000 000
- **WhatsApp**: +254 700 000 000

### Business Inquiries
- **Sales**: sales@kencomsoftware.co.ke
- **Website**: www.kencomsoftware.co.ke

### Documentation
- **User Manual**: Available in PDF format
- **Video Tutorials**: YouTube channel
- **FAQs**: Check website knowledge base

---

## 📄 License

**Commercial License**

This software is proprietary and commercial. Unauthorized copying, distribution, or modification is strictly prohibited.

### Licensing Options

1. **Single Warehouse License**: KES 150,000 (one-time)
2. **Multi-Warehouse License**: KES 250,000 (one-time)
3. **Enterprise License**: Contact for pricing

### Includes:
- Installation & setup support
- 1 year of updates
- Technical support (email/phone)
- User training (2 sessions)
- Custom modifications (basic)

### Annual Maintenance: 20% of license fee
- Software updates
- Technical support
- Cloud backup (optional)
- Performance optimization

---

## 🚀 Version History

### Version 1.0.0 (Current)
- Initial release
- Core cargo tracking features
- Supplier management
- Basic analytics
- Admin interface

### Planned Features (v1.1.0)
- Mobile app for drivers
- SMS notifications
- Barcode scanning
- Advanced reporting
- API for third-party integration

---

## 🙏 Credits

Developed with Love for Kenyan businesses

**Development Team:**
- Backend: Django/Python
- Database: PostgreSQL
- UI/UX: Bootstrap 5

---

**Ready to Transform Your Logistics Operations?**

Contact us today for a demo: **sales@steveongera.co.ke** | **+254 700 000 000**