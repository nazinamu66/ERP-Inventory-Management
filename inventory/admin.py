from django.contrib import admin
from .models import Store, Supplier, Product, Stock, Purchase, Sale, StockTransfer
from .models import AuditLog
from .models import CompanyProfile


admin.site.register(Store)
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(Stock)
admin.site.register(Purchase)
admin.site.register(Sale)
admin.site.register(StockTransfer)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'description')
    list_filter = ('action', 'timestamp')


