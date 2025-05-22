import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours, flt
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for project details page"""
    
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
        {"label": "Cart", "url": "/cart"},
        {"label": "Project Details", "url": "/project-details"}
    ]
    
    # Get booking ID from URL
    booking_id = frappe.form_dict.get('booking_id')
    
    if not booking_id:
        frappe.throw(_("No booking ID provided"))
    
    # Get booking details
    booking = get_booking_details(booking_id)
    context.booking = booking
    context.booking_id = booking_id
    
    # Get project detail fields from settings
    context.project_fields = settings.project_detail_fields
    
    return context

def get_booking_details(booking_id):
    """Get booking details for the given booking ID"""
    
    # Get booking from session or database
    booking_data = frappe.cache().get_value(f"booking_draft_{booking_id}")
    
    if not booking_data:
        frappe.throw(_("Booking not found or session expired"))
    
    # Calculate booking duration
    start_date = getdate(booking_data.get("start_date"))
    end_date = getdate(booking_data.get("end_date"))
    duration = (end_date - start_date).days + 1
    
    # Get items
    items = booking_data.get("items", [])
    total_items = sum(item.get("qty", 0) for item in items)
    
    # Calculate totals
    subtotal = sum(item.get("amount", 0) for item in items)
    
    # Get tax rate from settings
    settings = get_rental_portal_settings()
    tax_rate = flt(settings.default_tax_rate)
    tax_amount = flt(subtotal * tax_rate / 100)
    total = flt(subtotal + tax_amount)
    
    # Prepare booking summary
    booking_summary = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "duration": duration,
        "total_items": total_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total
    }
    
    return booking_summary
