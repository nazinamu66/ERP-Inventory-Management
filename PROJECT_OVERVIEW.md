
### 2. **Update `PROJECT_OVERVIEW.md`**
We can summarize the integration steps and the use of ERPNext:

```markdown
# Project Overview

This project is focused on developing a multi-user, multi-store ERP inventory management system. The system will be integrated with ERPNext via its API to manage inventory, products, users, and store-level details. The integration will allow fetching and pushing data to ERPNext for synchronization.

## Features:
- Multi-user, multi-store support.
- Integration with ERPNext for inventory management.
- API-based communication with ERPNext.
- Real-time synchronization of inventory and product data.

## ERPNext Integration:
We are utilizing the ERPNext API to:
- Ping ERPNext server.
- Fetch product details.
- Synchronize stock and inventory across different stores.

# ERP Inventory Management System

## 🎯 Goal
Multi-user, multi-store inventory management system with role-based access, tracking stock at both product and store levels, accessible online.

## 🔧 Tech Stack
- Backend: Django, Django REST Framework
- DB: PostgreSQL
- Frontend: (For future) React.js + Tailwind CSS / Bootstrap
- Deployment: DigitalOcean / AWS / Heroku (TBD)

## ✅ Key Features
- User Authentication
- Role-Based Access Control
- Product & Stock Management
- Store-Level Tracking
- Custom Views per Role
- Reporting & Notifications

## 🧠 Roles
- Admin
- Manager (oversees all stores)
- Storekeeper (restricted to one store)

## 📦 Current Apps
- `inventory`
- `users`

## 📈 Phases
**Phase 1: Setup & Core Models**
- [x] Database setup
- [x] Model creation & migrations
- [ ] Role system
- [ ] Custom views

**Phase 2: Views, Forms, and Templates**
**Phase 3: Transactions (Purchase/Sale/Stock Transfer)**
**Phase 4: Reporting + Notifications**
**Phase 5: Frontend polish & Deployment**

# Inventory Management System – Capo's ERP

## 🧭 Project Goal
A multi-user, multi-store inventory management system with role-based dashboards and core ERP modules like stock tracking, purchases, and transfers.

## 🏗️ Stack
- **Backend:** Django, Django REST Framework
- **Database:** PostgreSQL
- **Frontend:** Django Admin (for now), later ReactJS
- **Dev Tools:** VS Code, Git, GitHub, Postman, Docker (optional)

## 👥 User Roles
- **Admin** – Superuser with access to all modules
- **Store Manager** – Manages stock in their own store
- **Inventory Officer** – Handles purchases, stock transfers
- **Sales Rep** – Records sales per store

## 📦 Core Modules
- Product & Category Management
- Store Management
- Stock Tracking (by product/store)
- Purchases & Purchase Orders
- Sales
- Stock Transfers
- Supplier Management
- Reporting (later phase)

## 🌐 Accessibility
- Online deployment planned (Heroku/AWS/DigitalOcean)
