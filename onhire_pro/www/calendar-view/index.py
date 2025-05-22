import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours, get_first_day, get_last_day, add_months
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for calendar view page"""
    
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
        {"label": "Calendar View", "url": "/calendar-view"}
    ]
    
    # Get filter parameters from URL
    view_type = frappe.form_dict.get('view', 'month')
    month = frappe.form_dict.get('month', nowdate().split('-')[1])
    year = frappe.form_dict.get('year', nowdate().split('-')[0])
    event_type = frappe.form_dict.get('event_type', 'all')
    
    # Get customer linked to the current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        context.events = []
        context.error_message = "No customer account found for your user. Please contact support."
        return context
    
    # Set current date for calendar
    current_date = f"{year}-{month.zfill(2)}-01"
    
    # Get calendar data based on view type
    if view_type == 'month':
        context.calendar_data = get_month_calendar_data(customer, current_date, event_type)
    elif view_type == 'week':
        context.calendar_data = get_week_calendar_data(customer, current_date, event_type)
    elif view_type == 'day':
        day = frappe.form_dict.get('day', '01')
        current_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        context.calendar_data = get_day_calendar_data(customer, current_date, event_type)
    else:
        context.calendar_data = get_month_calendar_data(customer, current_date, event_type)
    
    # Set active view and filters
    context.active_view = view_type
    context.current_month = int(month)
    context.current_year = int(year)
    context.current_day = frappe.form_dict.get('day', '01')
    context.active_event_type = event_type
    
    # Get month name
    context.month_name = get_datetime(current_date).strftime('%B')
    
    # Get event type options
    context.event_type_options = [
        {"value": "all", "label": "All Events"},
        {"value": "rental_start", "label": "Rental Start"},
        {"value": "rental_end", "label": "Rental End"},
        {"value": "booking", "label": "Bookings"},
        {"value": "delivery", "label": "Deliveries"}
    ]
    
    # Get event legends
    context.event_legends = [
        {"type": "rental_start", "label": "Rental Start", "color": "success"},
        {"type": "rental_end", "label": "Rental End", "color": "danger"},
        {"type": "booking", "label": "Booking", "color": "primary"},
        {"type": "delivery", "label": "Delivery", "color": "warning"}
    ]
    
    return context

def get_month_calendar_data(customer, date_str, event_type):
    """Get calendar data for month view"""
    
    # Parse date
    date = getdate(date_str)
    
    # Get first and last day of month
    first_day = get_first_day(date)
    last_day = get_last_day(date)
    
    # Get events for the month
    events = get_events_for_period(customer, first_day, last_day, event_type)
    
    # Get previous and next month
    prev_month = add_months(first_day, -1)
    next_month = add_months(first_day, 1)
    
    # Get days in month
    days_in_month = (last_day - first_day).days + 1
    
    # Get first day of week (0 = Monday, 6 = Sunday)
    first_day_of_week = getdate(first_day).weekday()
    
    # Adjust for Sunday as first day of week
    first_day_of_week = (first_day_of_week + 1) % 7
    
    # Generate calendar grid
    calendar_grid = []
    
    # Add empty cells for days before first day of month
    week = []
    for i in range(first_day_of_week):
        week.append({"day": None, "events": []})
    
    # Add days of month
    for day in range(1, days_in_month + 1):
        current_date = getdate(f"{date.year}-{date.month:02d}-{day:02d}")
        day_events = [event for event in events if getdate(event["date"]) == current_date]
        
        week.append({
            "day": day,
            "date": current_date,
            "events": day_events,
            "is_today": current_date == getdate(nowdate())
        })
        
        # Start new week if Sunday or last day
        if (len(week) == 7) or (day == days_in_month):
            # Pad last week with empty cells
            if day == days_in_month and len(week) < 7:
                for i in range(7 - len(week)):
                    week.append({"day": None, "events": []})
            
            calendar_grid.append(week)
            week = []
    
    return {
        "grid": calendar_grid,
        "prev_month": {"month": prev_month.month, "year": prev_month.year},
        "next_month": {"month": next_month.month, "year": next_month.year},
        "events": events
    }

def get_week_calendar_data(customer, date_str, event_type):
    """Get calendar data for week view"""
    
    # Parse date
    date = getdate(date_str)
    
    # Get first day of week (Monday)
    weekday = date.weekday()
    first_day_of_week = add_days(date, -weekday)
    
    # Get last day of week (Sunday)
    last_day_of_week = add_days(first_day_of_week, 6)
    
    # Get events for the week
    events = get_events_for_period(customer, first_day_of_week, last_day_of_week, event_type)
    
    # Get previous and next week
    prev_week = add_days(first_day_of_week, -7)
    next_week = add_days(first_day_of_week, 7)
    
    # Generate week days
    week_days = []
    for i in range(7):
        current_date = add_days(first_day_of_week, i)
        day_events = [event for event in events if getdate(event["date"]) == current_date]
        
        week_days.append({
            "day": current_date.day,
            "date": current_date,
            "weekday": current_date.strftime('%A'),
            "events": day_events,
            "is_today": current_date == getdate(nowdate())
        })
    
    return {
        "days": week_days,
        "prev_week": {"month": prev_week.month, "year": prev_week.year, "day": prev_week.day},
        "next_week": {"month": next_week.month, "year": next_week.year, "day": next_week.day},
        "events": events
    }

def get_day_calendar_data(customer, date_str, event_type):
    """Get calendar data for day view"""
    
    # Parse date
    date = getdate(date_str)
    
    # Get events for the day
    events = get_events_for_period(customer, date, date, event_type)
    
    # Get previous and next day
    prev_day = add_days(date, -1)
    next_day = add_days(date, 1)
    
    # Generate hour slots
    hour_slots = []
    for hour in range(0, 24):
        hour_events = [event for event in events if event.get("hour") == hour]
        
        hour_slots.append({
            "hour": hour,
            "time": f"{hour:02d}:00",
            "events": hour_events
        })
    
    return {
        "date": date,
        "weekday": date.strftime('%A'),
        "hours": hour_slots,
        "prev_day": {"month": prev_day.month, "year": prev_day.year, "day": prev_day.day},
        "next_day": {"month": next_day.month, "year": next_day.year, "day": next_day.day},
        "events": events
    }

def get_events_for_period(customer, start_date, end_date, event_type):
    """Get events for a specific period"""
    
    events = []
    
    # Get bookings for the period
    bookings = frappe.get_all("Rental Booking Request", 
                             filters={
                                 "customer": customer,
                                 "status": ["in", ["Pending Approval", "Approved", "In Progress"]],
                                 "booking_start_date": ["<=", end_date],
                                 "booking_end_date": [">=", start_date]
                             },
                             fields=["name", "booking_title", "booking_start_date", "booking_end_date", 
                                    "status", "booking_reference", "delivery_method"])
    
    # Process bookings into events
    for booking in bookings:
        # Add rental start event
        if (event_type == 'all' or event_type == 'rental_start') and getdate(booking.booking_start_date) >= start_date and getdate(booking.booking_start_date) <= end_date:
            events.append({
                "title": booking.booking_title,
                "date": booking.booking_start_date,
                "type": "rental_start",
                "booking_reference": booking.booking_reference,
                "booking_id": booking.name,
                "status": booking.status,
                "hour": 9  # Default to 9 AM for day view
            })
        
        # Add rental end event
        if (event_type == 'all' or event_type == 'rental_end') and getdate(booking.booking_end_date) >= start_date and getdate(booking.booking_end_date) <= end_date:
            events.append({
                "title": booking.booking_title,
                "date": booking.booking_end_date,
                "type": "rental_end",
                "booking_reference": booking.booking_reference,
                "booking_id": booking.name,
                "status": booking.status,
                "hour": 17  # Default to 5 PM for day view
            })
        
        # Add booking event (for pending approvals)
        if (event_type == 'all' or event_type == 'booking') and booking.status == "Pending Approval":
            # Add event on the creation date
            booking_doc = frappe.get_doc("Rental Booking Request", booking.name)
            creation_date = getdate(booking_doc.creation)
            
            if creation_date >= start_date and creation_date <= end_date:
                events.append({
                    "title": f"Booking Request: {booking.booking_title}",
                    "date": creation_date,
                    "type": "booking",
                    "booking_reference": booking.booking_reference,
                    "booking_id": booking.name,
                    "status": booking.status,
                    "hour": int(get_datetime(booking_doc.creation).strftime('%H'))
                })
        
        # Add delivery event
        if (event_type == 'all' or event_type == 'delivery') and booking.delivery_method == "delivery" and booking.status in ["Approved", "In Progress"]:
            # Add delivery on start date
            if getdate(booking.booking_start_date) >= start_date and getdate(booking.booking_start_date) <= end_date:
                events.append({
                    "title": f"Delivery: {booking.booking_title}",
                    "date": booking.booking_start_date,
                    "type": "delivery",
                    "booking_reference": booking.booking_reference,
                    "booking_id": booking.name,
                    "status": booking.status,
                    "hour": 8  # Default to 8 AM for day view
                })
    
    return events
