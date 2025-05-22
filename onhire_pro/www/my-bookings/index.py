import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for my bookings page"""
    
    # Get rental portal settings
    settings = get_rental_portal_settings()
    
    # Check if portal is enabled
    if not settings.enable_rental_portal:
        frappe.throw(_("Customer Portal is not enabled"), frappe.PermissionError)
    
    # Add settings to context
    context.settings = settings
    
    # Add navigation items to context
    context.nav_items = get_portal_navigation_items()
    
    # Set breadcrumbs
    context.breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "My Bookings", "url": "/my-bookings"}
    ]
    
    # Get filter parameters from URL
    status = frappe.form_dict.get('status', 'All')
    
    # Get customer linked to the current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        context.bookings = []
        context.error_message = "No customer account found for your user. Please contact support."
        return context
    
    # Build filters for bookings query
    filters = {
        "customer": customer
    }
    
    if status != 'All':
        filters["status"] = status
    
    # Get bookings
    bookings = frappe.get_all("Rental Booking Request", 
                             filters=filters,
                             fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                    "status", "total_amount", "creation", "modified", "booking_reference"],
                             order_by="creation desc")
    
    # Get items for each booking
    for booking in bookings:
        booking.items = frappe.get_all("Rental Booking Item", 
                                      filters={"parent": booking.name},
                                      fields=["item_code", "item_name", "qty", "rate", "amount", "is_sales_item"])
        
        # Calculate days for rental items
        booking.rental_days = (getdate(booking.booking_end_date) - getdate(booking.booking_start_date)).days + 1
        
        # Determine if booking can be edited (only if status is "Pending Approval")
        booking.can_edit = booking.status == "Pending Approval"
        
        # Determine if booking can be cancelled (only if status is "Pending Approval" or "Approved")
        booking.can_cancel = booking.status in ["Pending Approval", "Approved"]
    
    context.bookings = bookings
    
    # Set active status filter
    context.active_status = status
    
    # Set status options
    context.status_options = [
        {"value": "All", "label": "All Bookings"},
        {"value": "Pending Approval", "label": "Pending Approval"},
        {"value": "Approved", "label": "Approved"},
        {"value": "In Progress", "label": "In Progress"},
        {"value": "Completed", "label": "Completed"},
        {"value": "Cancelled", "label": "Cancelled"},
        {"value": "Rejected", "label": "Rejected"}
    ]
    
    return context
