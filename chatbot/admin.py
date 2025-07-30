from django.contrib import admin
from .models import PoolCustomer


@admin.register(PoolCustomer)
class PoolCustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'api_key_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer_id',)
    readonly_fields = ('created_at',)

    def api_key_preview(self, obj):
        return f"{obj.api_key[:15]}..." if len(obj.api_key) > 15 else obj.api_key

    api_key_preview.short_description = 'API Key Preview'

    fieldsets = (
        (None, {
            'fields': ('customer_id', 'api_key'),
            'description': 'Add pool customers with their poolcopilot.com API keys'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )