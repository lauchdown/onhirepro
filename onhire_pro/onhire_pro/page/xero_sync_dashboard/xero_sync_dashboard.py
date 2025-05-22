import frappe
from frappe import _
from frappe.utils import get_datetime, add_days

@frappe.whitelist()
def get_dashboard_data(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    
    date_filters = {}
    if filters.get('date_range'):
        date_filters['modified'] = ['between', filters['date_range']]
    
    status_filters = {}
    if filters.get('sync_status'):
        status_filters['xero_sync_status'] = filters['sync_status']
    
    # Get stats
    stats = get_sync_stats(date_filters, status_filters)
    
    # Get failed syncs
    failed_syncs = get_failed_syncs(date_filters)
    
    return {
        'stats': stats,
        'failed_syncs': failed_syncs
    }

def get_sync_stats(date_filters, status_filters):
    base_filters = {
        'docstatus': 1,
        **date_filters,
        **status_filters
    }
    
    total_syncs = frappe.db.count('Sales Invoice', filters=base_filters)
    
    successful_syncs = frappe.db.count('Sales Invoice', filters={
        **base_filters,
        'xero_sync_status': 'Synced'
    })
    
    failed_syncs = frappe.db.count('Sales Invoice', filters={
        **base_filters,
        'xero_sync_status': 'Failed'
    })
    
    pending_syncs = frappe.db.count('Sales Invoice', filters={
        **base_filters,
        'xero_sync_status': ['in', ['Not Synced', 'In Progress']]
    })
    
    return {
        'total_syncs': total_syncs,
        'successful_syncs': successful_syncs,
        'failed_syncs': failed_syncs,
        'pending_syncs': pending_syncs
    }

def get_failed_syncs(date_filters):
    filters = {
        'docstatus': 1,
        'xero_sync_status': 'Failed',
        **date_filters
    }
    
    failed_syncs = frappe.get_all(
        'Sales Invoice',
        filters=filters,
        fields=[
            'name',
            'customer_name',
            'grand_total',
            'currency',
            'xero_last_sync_attempt',
            'xero_sync_attempts'
        ],
        order_by='xero_last_sync_attempt desc'
    )
    
    # Get error messages from comments
    for sync in failed_syncs:
        last_error = frappe.get_all(
            'Comment',
            filters={
                'reference_doctype': 'Sales Invoice',
                'reference_name': sync.name,
                'comment_type': 'Comment'
            },
            fields=['content'],
            order_by='creation desc',
            limit=1
        )
        
        sync['error_message'] = last_error[0].content if last_error else None
    
    return failed_syncs
