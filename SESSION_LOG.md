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


