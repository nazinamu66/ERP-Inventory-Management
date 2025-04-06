# PROJECT_TRACKER.md

## 🧠 Overview:
This document tracks development, key decisions, and steps taken for the Inventory Management System. Goal: A cloud-agnostic, ERP-flexible system.

---

## 🧩 Key Design Choices:
- **ERP Independence:** Avoid tight integration with ERPNext or any provider.
- **Modular API Layer:** Create plug-and-play APIs for ERPNext, others.
- **Abstract Models:** Structure data in a generic way, not vendor-specific.

---

## ✅ Done So Far:
- Clean setup of Django project.
- Installed Django and started the app.
- VS Code environment ready.
- Planning structure for flexible cloud integration.

---

## 🔄 In Progress:
- Abstract models: `Supplier`, `Product`, `Store`.
- Placeholder API layer for ERPNext.
- Markdown-based tracking of steps and progress.

---

## 📌 Next Steps:
- Finalize and migrate abstract models.
- Add basic CRUD views and serializers.
- Simulate ERPNext data exchange via dummy endpoints.
- Set up initial cloud deployment strategy (cloud-agnostic).

---

## 🧪 Testing Strategy:
- Local testing with SQLite and mock ERPNext API.
- Prepare for switch to PostgreSQL when production-ready.

