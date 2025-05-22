import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for my rentals dashboard page"""
    
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
        {"label": "My Rentals", "url": "/my-rentals"}
    ]
    
    # Get filter parameters from URL
    view_type = frappe.form_dict.get('view', 'active')
    
    # Get customer linked to the current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        context.rentals = []
        context.error_message = "No customer account found for your user. Please contact support."
        return context
    
    # Get rentals based on view type
    if view_type == 'active':
        context.rentals = get_active_rentals(customer)
    elif view_type == 'upcoming':
        context.rentals = get_upcoming_rentals(customer)
    elif view_type == 'past':
        context.rentals = get_past_rentals(customer)
    else:
        context.rentals = get_active_rentals(customer)
    
    # Set active view
    context.active_view = view_type
    
    # Get rental statistics
    context.rental_stats = get_rental_statistics(customer)
    
    return context

def get_active_rentals(customer):
    """Get active rentals for the customer"""
    
    # Active rentals are those with status "In Progress" and current date is between start and end date
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={
                                 "customer": customer,
                                 "status": "In Progress",
                                 "booking_start_date": ["<=", nowdate()],
                                 "booking_end_date": [">=", nowdate()]
                             },
                             fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                    "status", "total_amount", "booking_reference", "delivery_method"],
                             order_by="booking_start_date desc")
    
    # Get items for each booking
    for booking in bookings:
        booking.items = frappe.get_all("Rental Booking Item", 
                                      filters={"parent": booking.name, "is_rental_item": 1},
                                      fields=["item_code", "item_name", "qty", "rate", "amount", "serial_no"])
        
        # Calculate days remaining
        booking.days_remaining = (getdate(booking.booking_end_date) - getdate(nowdate())).days
        booking.total_days = (getdate(booking.booking_end_date) - getdate(booking.booking_start_date)).days + 1
        booking.days_elapsed = booking.total_days - booking.days_remaining
        booking.progress_percent = min(100, max(0, int((booking.days_elapsed / booking.total_days) * 100)))
    
    return bookings

def get_upcoming_rentals(customer):
    """Get upcoming rentals for the customer"""
    
    # Upcoming rentals are those with status "Approved" and start date is in the future
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={
                                 "customer": customer,
                                 "status": "Approved",
                                 "booking_start_date": [">", nowdate()]
                             },
                             fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                    "status", "total_amount", "booking_reference", "delivery_method"],
                             order_by="booking_start_date asc")
    
    # Get items for each booking
    for booking in bookings:
        booking.items = frappe.get_all("Rental Booking Item", 
                                      filters={"parent": booking.name, "is_rental_item": 1},
                                      fields=["item_code", "item_name", "qty", "rate", "amount", "serial_no"])
        
        # Calculate days until start
        booking.days_until_start = (getdate(booking.booking_start_date) - getdate(nowdate())).days
        booking.total_rental_days = (getdate(booking.booking_end_date) - getdate(booking.booking_start_date)).days + 1
    
    return bookings

def get_past_rentals(customer):
    """Get past rentals for the customer"""
    
    # Past rentals are those with status "Completed" or end date is in the past
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={
                                 "customer": customer,
                                 "status": ["in", ["Completed", "In Progress"]],
                                 "booking_end_date": ["<", nowdate()]
                             },
                             fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                    "status", "total_amount", "booking_reference", "delivery_method"],
                             order_by="booking_end_date desc")
    
    # Get items for each booking
    for booking in bookings:
        booking.items = frappe.get_all("Rental Booking Item", 
                                      filters={"parent": booking.name, "is_rental_item": 1},
                                      fields=["item_code", "item_name", "qty", "rate", "amount", "serial_no"])
        
        # Calculate days since end
        booking.days_since_end = (getdate(nowdate()) - getdate(booking.booking_end_date)).days
        booking.total_rental_days = (getdate(booking.booking_end_date) - getdate(booking.booking_start_date)).days + 1
    
    return bookings

def get_rental_statistics(customer):
    """Get rental statistics for the customer"""
    
    # Initialize statistics
    stats = {
        "active_rentals": 0,
        "upcoming_rentals": 0,
        "past_rentals": 0,
        "total_rental_days": 0,
        "total_rental_value": 0
    }
    
    # Get active rentals count
    stats["active_rentals"] = frappe.db.count("Rental Booking Request", {
        "customer": customer,
        "status": "In Progress",
        "booking_start_date": ["<=", nowdate()],
        "booking_end_date": [">=", nowdate()]
    })
    
    # Get upcoming rentals count
    stats["upcoming_rentals"] = frappe.db.count("Rental Booking Request", {
        "customer": customer,
        "status": "Approved",
        "booking_start_date": [">", nowdate()]
    })
    
    # Get past rentals count
    stats["past_rentals"] = frappe.db.count("Rental Booking Request", {
        "customer": customer,
        "status": ["in", ["Completed", "In Progress"]],
        "booking_end_date": ["<", nowdate()]
    })
    
    # Get all completed and in-progress bookings
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={
                                 "customer": customer,
                                 "status": ["in", ["Completed", "In Progress"]]
                             },
                             fields=["booking_start_date", "booking_end_date", "total_amount"])
    
    # Calculate total rental days and value
    for booking in bookings:
        rental_days = (getdate(booking.booking_end_date) - getdate(booking.booking_start_date)).days + 1
        stats["total_rental_days"] += rental_days
        stats["total_rental_value"] += booking.total_amount
    
    return stats
