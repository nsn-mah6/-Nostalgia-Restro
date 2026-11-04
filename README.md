# Restaurant Management System (Django)

This project is a Django-based Restaurant Management System for handling:
- Order placement
- Kitchen status tracking
- Inventory updates based on recipes
- Payment processing
- Sales reporting
- Simple AI-based future sales prediction

## Features
- Create customer orders with dine-in or takeaway options
- Update kitchen status: Pending → Preparing → Ready
- Automatically reduce stock from recipe ingredients when an order is created
- Accept payment via cash, QR, or card
- Track sales reports and forecast future demand
- Staff login/logout with secure password hashing
- Password reset flow for staff accounts
- Personal profile editing and secure password changes
- Role-based access for Admin, Manager, Waiter, Cashier, Kitchen Staff, and Inventory Staff
- Role-specific dashboard views
- Staff account management and detailed activity tracking

## Run locally

1. Open the project folder
2. Create and activate a virtual environment if needed
3. Install dependencies:
   ```bash
   python3 -m pip install django
   ```
4. Run database migrations:
   ```bash
   python3 manage.py migrate
   ```
5. Set up staff roles and create the default admin user:
   ```bash
   python3 manage.py setup_roles
   ```
6. Load sample menu and inventory data:
   ```bash
   python3 manage.py seed_data
   ```
7. Start the server:
   ```bash
   python3 manage.py runserver
   ```
8. Open http://127.0.0.1:8000/login/

## Default login
- Username: admin
- Password: admin123

## Main pages
- Login: http://127.0.0.1:8000/login/
- Password Reset: http://127.0.0.1:8000/password-reset/
- Profile: http://127.0.0.1:8000/profile/
- Dashboard: http://127.0.0.1:8000/
- Orders: http://127.0.0.1:8000/orders/
- Kitchen: http://127.0.0.1:8000/kitchen/
- Inventory: http://127.0.0.1:8000/inventory/
- Reports: http://127.0.0.1:8000/reports/
- Staff Management: http://127.0.0.1:8000/staff/
