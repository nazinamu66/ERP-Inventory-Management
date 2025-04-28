(venv) venvCapo@Capos ERP-Inventory-Management %   tree -L 4

.
├── FOLDER_STRUCTURE.md
├── PROJECT_OVERVIEW.md
├── README.md
├── SESSION_LOG.md
├── SYSTEM_INTEGRATION_PLAN.md
├── Save Comms.txt
├── config
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── settings.cpython-313.pyc
│   │   ├── urls.cpython-313.pyc
│   │   └── wsgi.cpython-313.pyc
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── erp_integration
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── admin.cpython-313.pyc
│   │   ├── apps.cpython-313.pyc
│   │   ├── config.cpython-313.pyc
│   │   ├── models.cpython-313.pyc
│   │   ├── services.cpython-313.pyc
│   │   └── utils.cpython-313.pyc
│   ├── admin.py
│   ├── apps.py
│   ├── config.py
│   ├── migrations
│   │   ├── __init__.py
│   │   └── __pycache__
│   │       └── __init__.cpython-313.pyc
│   ├── models.py
│   ├── services.py
│   ├── tests.py
│   ├── utils.py
│   └── views.py
├── inventory
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── admin.cpython-313.pyc
│   │   ├── apps.cpython-313.pyc
│   │   ├── forms.cpython-313.pyc
│   │   ├── models.cpython-313.pyc
│   │   ├── urls.cpython-313.pyc
│   │   └── views.cpython-313.pyc
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── integrations
│   │   └── erpnext
│   │       ├── __pycache__
│   │       └── sync.py
│   ├── management
│   │   └── commands
│   │       ├── __pycache__
│   │       ├── sync_products.py
│   │       └── sync_suppliers.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   ├── 0002_initial.py
│   │   ├── 0003_alter_stock_product.py
│   │   ├── 0004_item_price.py
│   │   ├── 0005_remove_stocktransfer_transfer_date_and_more.py
│   │   ├── 0006_product_quantity.py
│   │   ├── 0007_stockadjustment.py
│   │   ├── 0008_stockadjustment_store.py
│   │   ├── 0009_product_total_quantity_alter_stockadjustment_store.py
│   │   ├── 0010_remove_purchase_item_remove_sale_item_and_more.py
│   │   ├── 0011_stockadjustment_adjustment_type_and_more.py
│   │   ├── 0012_auditlog.py
│   │   ├── 0013_purchase_note_purchase_purchased_by_and_more.py
│   │   ├── 0014_sale_sold_by_alter_sale_sale_date.py
│   │   ├── 0015_companyprofile.py
│   │   ├── 0016_purchaseorder_status.py
│   │   ├── 0017_customer_remove_sale_product_remove_sale_quantity_and_more.py
│   │   ├── 0018_bankaccount_sale_receipt_number_sale_bank.py
│   │   ├── 0019_sale_total_amount_alter_sale_receipt_number.py
│   │   ├── 0020_alter_sale_receipt_number_salereturn_salereturnitem.py
│   │   ├── __init__.py
│   │   └── __pycache__
│   │       ├── 0001_initial.cpython-313.pyc
│   │       ├── 0002_initial.cpython-313.pyc
│   │       ├── 0003_alter_stock_product.cpython-313.pyc
│   │       ├── 0004_item_price.cpython-313.pyc
│   │       ├── 0005_remove_stocktransfer_transfer_date_and_more.cpython-313.pyc
│   │       ├── 0006_product_quantity.cpython-313.pyc
│   │       ├── 0007_stockadjustment.cpython-313.pyc
│   │       ├── 0008_stockadjustment_store.cpython-313.pyc
│   │       ├── 0009_product_total_quantity_alter_stockadjustment_store.cpython-313.pyc
│   │       ├── 0010_remove_purchase_item_remove_sale_item_and_more.cpython-313.pyc
│   │       ├── 0011_stockadjustment_adjustment_type_and_more.cpython-313.pyc
│   │       ├── 0012_auditlog.cpython-313.pyc
│   │       ├── 0013_purchase_note_purchase_purchased_by_and_more.cpython-313.pyc
│   │       ├── 0014_sale_sold_by_alter_sale_sale_date.cpython-313.pyc
│   │       ├── 0015_companyprofile.cpython-313.pyc
│   │       ├── 0016_purchaseorder_status.cpython-313.pyc
│   │       ├── 0017_customer_remove_sale_product_remove_sale_quantity_and_more.cpython-313.pyc
│   │       ├── 0018_bankaccount_sale_receipt_number_sale_bank.cpython-313.pyc
│   │       ├── 0019_alter_sale_receipt_number.cpython-313.pyc
│   │       ├── 0019_sale_total_amount_alter_sale_receipt_number.cpython-313.pyc
│   │       ├── 0020_alter_sale_receipt_number.cpython-313.pyc
│   │       ├── 0020_alter_sale_receipt_number_salereturn_salereturnitem.cpython-313.pyc
│   │       └── __init__.cpython-313.pyc
│   ├── models.py
│   ├── services
│   │   └── erpnext_service.py
│   ├── templatetags
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   ├── dict_extras.cpython-313.pyc
│   │   │   └── math_filters.cpython-313.pyc
│   │   ├── dict_extras.py
│   │   └── math_filters.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── manage.py
├── media
│   └── company_logos
│       └── Screenshot_2025-02-17_at_5.16.24PM.png
├── templates
│   ├── dashboard
│   │   ├── admin.html
│   │   ├── audit_log_list.html
│   │   ├── base.html
│   │   ├── customer_form.html
│   │   ├── default.html
│   │   ├── inventory.html
│   │   ├── inventory_report.html
│   │   ├── manager.html
│   │   ├── product_confirm_delete.html
│   │   ├── product_form.html
│   │   ├── product_list.html
│   │   ├── purchase_form.html
│   │   ├── purchase_order_detail.html
│   │   ├── purchase_order_form.html
│   │   ├── purchase_order_list.html
│   │   ├── purchase_order_pdf.html
│   │   ├── receive_purchase_order.html
│   │   ├── sale_detail.html
│   │   ├── sale_form.html
│   │   ├── sale_list.html
│   │   ├── sale_report_pdf.html
│   │   ├── sale_return_form.html
│   │   ├── staff.html
│   │   ├── stock_adjustment_form.html
│   │   ├── stock_list.html
│   │   ├── stock_transfer.html
│   │   ├── stock_transfer_list.html
│   │   ├── store.html
│   │   ├── supplier_form.html
│   │   └── supplier_list.html
│   ├── errors
│   │   └── permission_denied.html
│   ├── pdf
│   │   ├── inventory_report_pdf.html
│   │   ├── po_receipt.html
│   │   ├── purchase_orders_report_pdf.html
│   │   └── sale_receipt.html
│   └── users
│       ├── login.html
│       ├── user_confirm_delete.html
│       ├── user_form.html
│       └── user_list.html
├── users
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── admin.cpython-313.pyc
│   │   ├── apps.cpython-313.pyc
│   │   ├── decorators.cpython-313.pyc
│   │   ├── forms.cpython-313.pyc
│   │   ├── models.cpython-313.pyc
│   │   ├── urls.cpython-313.pyc
│   │   └── views.cpython-313.pyc
│   ├── admin.py
│   ├── apps.py
│   ├── decorators.py
│   ├── forms.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   ├── 0002_alter_user_role.py
│   │   ├── 0003_alter_user_role.py
│   │   ├── 0004_user_can_view_transfers.py
│   │   ├── 0005_user_can_adjust_stock_user_can_transfer_stock.py
│   │   ├── __init__.py
│   │   └── __pycache__
│   │       ├── 0001_initial.cpython-313.pyc
│   │       ├── 0002_alter_user_role.cpython-313.pyc
│   │       ├── 0003_alter_user_role.cpython-313.pyc
│   │       ├── 0004_user_can_view_transfers.cpython-313.pyc
│   │       ├── 0005_user_can_adjust_stock_user_can_transfer_stock.cpython-313.pyc
│   │       └── __init__.cpython-313.pyc
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
└── venv
    ├── bin
    │   ├── Activate.ps1
    │   ├── activate
    │   ├── activate.csh
    │   ├── activate.fish
    │   ├── chardetect
    │   ├── django-admin
    │   ├── fonttools
    │   ├── normalizer
    │   ├── pip
    │   ├── pip3
    │   ├── pip3.13
    │   ├── pisa
    │   ├── pybidi
    │   ├── pyftmerge
    │   ├── pyftsubset
    │   ├── pyhanko
    │   ├── python -> python3.13
    │   ├── python3 -> python3.13
    │   ├── python3.13 -> /usr/local/opt/python@3.13/bin/python3.13
    │   ├── qr
    │   ├── sqlformat
    │   ├── svg2pdf
    │   ├── ttx
    │   ├── weasyprint
    │   └── xhtml2pdf
    ├── include
    │   └── python3.13
    ├── lib
    │   └── python3.13
    │       └── site-packages
    ├── pyvenv.cfg
    └── share
        └── man
            └── man1

41 directories, 198 files