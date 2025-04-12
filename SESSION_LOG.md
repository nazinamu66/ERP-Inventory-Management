# Session Log

## April 3, 2025
- Updated folder structure to include `erp_integration/services.py` and `erp_integration/utils.py`.
- Successfully pinged ERPNext API to confirm connectivity.
- Fixed Django settings issue to load settings in non-Django context using `os.environ` to set `DJANGO_SETTINGS_MODULE`.

## Next Steps:
- Implement additional features like product syncing and inventory updates.
- Integrate multi-store functionality and handle API responses for product management.

# Session Log

## 📅 April 8, 2025
- ✅ Fresh PostgreSQL DB setup
- ✅ Removed default/auth-related tables
- ✅ Recreated only necessary inventory tables via migration
- 🔁 Next: Refine models, implement role system, custom views

## Notes:
- Used user "Capo" (capitalized) to DROP the DB due to ownership
- Current DB: `erp_inventory`
- Roles and views will use `users` app
- Git strategy: Push after each stable/tested section

# Session Log – Capo's ERP Inventory System

## 📅 2025-04-08

### ✅ What was done:
- Successfully reset PostgreSQL database
- Rebuilt fresh migrations for `inventory` and `users`
- Applied all migrations with no errors

### 🔧 Next Steps:
- Set up Git for version control
- Create initial Git commit
- Begin implementing custom login and role-based redirect

📅 Date: April 10, 2025
🕒 Session: Evening Work Session
✅ What Was Done:
Fixed TemplateDoesNotExist error for dashboard/base.html by ensuring correct template path and naming.

Resolved NoReverseMatch error for logout by defining logout_view in users/views.py and importing it correctly in config/urls.py.

Removed incorrect import: from . import views from config/urls.py.

Verified all dashboard routes (admin_dashboard, manager_dashboard, etc.) render properly.

Ensured templates for each role (admin.html, manager.html, etc.) are loading without issues.

🛠️ Current Working State:
All dashboard templates render correctly based on user roles.

Login and logout functionality works.

Clean navigation between login → dashboard → logout.

🔜 Next Steps:
Start work on user role-specific permissions (e.g., restrict admin pages to admins only).

Implement sidebar or top menu navigation inside base.html.

Begin structuring models for Products and Inventory in inventory/models.py.
