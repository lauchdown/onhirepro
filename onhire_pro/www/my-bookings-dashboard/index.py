import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for my bookings dashboard page"""
    
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
        {"label": "My Bookings Dashboard", "url": "/my-bookings-dashboard"}
    ]
    
    # Get customer linked to the current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        context.bookings = []
        context.error_message = "No customer account found for your user. Please contact support."
        return context
    
    # Get booking statistics
    context.booking_stats = get_booking_statistics(customer)
    
    # Get recent bookings
    context.recent_bookings = get_recent_bookings(customer)
    
    # Get SLA metrics
    context.sla_metrics = get_sla_metrics(customer)
    
    # Get upcoming events
    context.upcoming_events = get_upcoming_events(customer)
    
    return context

def get_booking_statistics(customer):
    """Get booking statistics for the customer"""
    
    # Initialize statistics
    stats = {
        "total_bookings": 0,
        "pending_approval": 0,
        "approved": 0,
        "in_progress": 0,
        "completed": 0,
        "cancelled": 0,
        "rejected": 0
    }
    
    # Get counts for each status
    for status in stats.keys():
        if status == "total_bookings":
            stats[status] = frappe.db.count("Rental Booking Request", {"customer": customer})
        else:
            status_key = status.replace("_", " ").title()
            stats[status] = frappe.db.count("Rental Booking Request", {"customer": customer, "status": status_key})
    
    return stats

def get_recent_bookings(customer, limit=5):
    """Get recent bookings for the customer"""
    
    # Get recent bookings
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={"customer": customer},
                             fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                    "status", "total_amount", "creation", "modified", "booking_reference"],
                             order_by="creation desc",
                             limit=limit)
    
    # Calculate SLA metrics for each booking
    for booking in bookings:
        # Calculate days for rental items
        booking.rental_days = (getdate(booking.booking_end_date) - getdate(booking.booking_start_date)).days + 1
        
        # Calculate time since creation
        booking.time_since_creation = time_diff_in_hours(nowdate(), booking.creation)
        
        # Calculate SLA status
        booking.sla_status = get_booking_sla_status(booking)
        
        # Determine if booking can be edited (only if status is "Pending Approval")
        booking.can_edit = booking.status == "Pending Approval"
        
        # Determine if booking can be cancelled (only if status is "Pending Approval" or "Approved")
        booking.can_cancel = booking.status in ["Pending Approval", "Approved"]
    
    return bookings

def get_sla_metrics(customer):
    """Get SLA metrics for the customer"""
    
    # Initialize SLA metrics
    sla_metrics = {
        "avg_approval_time": 0,
        "avg_response_time": 0,
        "pending_approvals": 0,
        "overdue_approvals": 0
    }
    
    # Get all bookings for the customer
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={"customer": customer},
                             fields=["name", "status", "creation", "modified", "approved_date"])
    
    # Calculate metrics
    approval_times = []
    response_times = []
    pending_approvals = 0
    overdue_approvals = 0
    
    for booking in bookings:
        # Calculate approval time for approved bookings
        if booking.approved_date:
            approval_time = time_diff_in_hours(booking.approved_date, booking.creation)
            approval_times.append(approval_time)
        
        # Calculate response time for all bookings (time to first status change)
        if booking.modified != booking.creation:
            response_time = time_diff_in_hours(booking.modified, booking.creation)
            response_times.append(response_time)
        
        # Count pending approvals
        if booking.status == "Pending Approval":
            pending_approvals += 1
            
            # Check if approval is overdue (more than 24 hours)
            if time_diff_in_hours(nowdate(), booking.creation) > 24:
                overdue_approvals += 1
    
    # Calculate averages
    if approval_times:
        sla_metrics["avg_approval_time"] = sum(approval_times) / len(approval_times)
    
    if response_times:
        sla_metrics["avg_response_time"] = sum(response_times) / len(response_times)
    
    sla_metrics["pending_approvals"] = pending_approvals
    sla_metrics["overdue_approvals"] = overdue_approvals
    
    return sla_metrics

def get_upcoming_events(customer, limit=5):
    """Get upcoming events for the customer"""
    
    # Get upcoming bookings (start date in the future)
    upcoming_bookings = frappe.get_all("Rental Booking Request", 
                                      filters={
                                          "customer": customer,
                                          "status": ["in", ["Approved", "In Progress"]],
                                          "booking_start_date": [">=", nowdate()]
                                      },
                                      fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                             "status", "booking_reference"],
                                      order_by="booking_start_date asc",
                                      limit=limit)
    
    # Format events
    events = []
    for booking in upcoming_bookings:
        events.append({
            "title": booking.booking_title,
            "date": booking.booking_start_date,
            "type": "start",
            "booking_reference": booking.booking_reference,
            "booking_id": booking.name,
            "status": booking.status
        })
        
        events.append({
            "title": booking.booking_title,
            "date": booking.booking_end_date,
            "type": "end",
            "booking_reference": booking.booking_reference,
            "booking_id": booking.name,
            "status": booking.status
        })
    
    # Sort events by date
    events.sort(key=lambda x: x["date"])
    
    # Limit to requested number
    return events[:limit]

def get_booking_sla_status(booking):
    """Get SLA status for a booking"""
    
    # Define SLA thresholds (in hours)
    sla_thresholds = {
        "good": 8,  # Less than 8 hours
        "warning": 16,  # Between 8 and 16 hours
        "overdue": 24  # More than 24 hours
    }
    
    # If booking is not pending approval, it's not subject to SLA
    if booking.status != "Pending Approval":
        return None
    
    # Calculate time since creation
    hours_since_creation = time_diff_in_hours(nowdate(), booking.creation)
    
    # Determine SLA status
    if hours_since_creation < sla_thresholds["good"]:
        return "good"
    elif hours_since_creation < sla_thresholds["warning"]:
        return "warning"
    else:
        return "overdue"
