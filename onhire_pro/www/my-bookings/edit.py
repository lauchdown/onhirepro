import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for booking edit page"""
    
    # Get rental portal settings
    settings = get_rental_portal_settings()
    
    # Check if portal is enabled
    if not settings.enable_rental_portal:
        frappe.throw(_("Customer Portal is not enabled"), frappe.PermissionError)
    
    # Add settings to context
    context.settings = settings
    
    # Add navigation items to context
    context.nav_items = get_portal_navigation_items()
    
    # Get booking ID from URL
    booking_id = frappe.form_dict.get('booking')
    if not booking_id:
        frappe.local.flags.redirect_location = "/my-bookings"
        raise frappe.Redirect
    
    # Get customer linked to the current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        frappe.throw(_("No customer account found for your user. Please contact support."))
    
    # Get booking details
    try:
        booking = frappe.get_doc("Rental Booking Request", booking_id)
        
        # Check if booking belongs to the current customer
        if booking.customer != customer:
            frappe.throw(_("You do not have permission to edit this booking."))
        
        # Check if booking can be edited (only if status is "Pending Approval")
        if booking.status != "Pending Approval":
            frappe.throw(_("This booking cannot be edited because its status is {0}.").format(booking.status))
        
    except frappe.DoesNotExistError:
        frappe.throw(_("Booking not found."))
    
    # Set breadcrumbs
    context.breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "My Bookings", "url": "/my-bookings"},
        {"label": "Edit Booking", "url": "/my-bookings/edit?booking=" + booking_id}
    ]
    
    # Add booking to context
    context.booking = booking
    
    # Get booking items
    context.booking_items = frappe.get_all("Rental Booking Item", 
                                         filters={"parent": booking.name},
                                         fields=["item_code", "item_name", "qty", "rate", "amount", 
                                                "is_sales_item", "is_rental_item"])
    
    # Get booking form field configuration from settings
    context.booking_fields = get_booking_form_fields(settings, booking)
    
    # Get job reference field configuration from settings
    context.job_reference_fields = get_job_reference_fields(settings, booking)
    
    # Get contact details field configuration from settings
    context.contact_fields = get_contact_fields(settings, booking)
    
    return context

def get_booking_form_fields(settings, booking):
    """Get booking form fields configuration from settings with values from booking"""
    
    # Default booking form fields
    booking_fields = [
        {
            "fieldname": "booking_title",
            "label": "Booking Title",
            "fieldtype": "Data",
            "required": 1,
            "value": booking.booking_title,
            "description": "A short title for this booking"
        },
        {
            "fieldname": "booking_start_date",
            "label": "Start Date",
            "fieldtype": "Date",
            "required": 1,
            "value": booking.booking_start_date,
            "description": "When do you need the rental items?"
        },
        {
            "fieldname": "booking_end_date",
            "label": "End Date",
            "fieldtype": "Date",
            "required": 1,
            "value": booking.booking_end_date,
            "description": "When will you return the rental items?"
        },
        {
            "fieldname": "booking_notes",
            "label": "Booking Notes",
            "fieldtype": "Text",
            "required": 0,
            "value": booking.booking_notes,
            "description": "Any additional information about this booking"
        }
    ]
    
    # TODO: Override with settings if configured
    
    return booking_fields

def get_job_reference_fields(settings, booking):
    """Get job reference fields configuration from settings with values from booking"""
    
    # Default job reference fields
    job_reference_fields = [
        {
            "fieldname": "job_reference_number",
            "label": "Job Reference Number",
            "fieldtype": "Data",
            "required": 0,
            "value": booking.job_reference_number,
            "description": "Your internal reference number for this job"
        },
        {
            "fieldname": "project_name",
            "label": "Project Name",
            "fieldtype": "Data",
            "required": 0,
            "value": booking.project_name,
            "description": "The name of the project these items are for"
        },
        {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Data",
            "required": 0,
            "value": booking.department,
            "description": "Department responsible for this booking"
        }
    ]
    
    # TODO: Override with settings if configured
    
    return job_reference_fields

def get_contact_fields(settings, booking):
    """Get contact details fields configuration from settings with values from booking"""
    
    # Default contact fields
    contact_fields = [
        {
            "fieldname": "contact_name",
            "label": "Contact Name",
            "fieldtype": "Data",
            "required": 1,
            "value": booking.contact_name,
            "description": "Name of the primary contact for this booking"
        },
        {
            "fieldname": "contact_email",
            "label": "Contact Email",
            "fieldtype": "Data",
            "required": 1,
            "value": booking.contact_email,
            "description": "Email address for booking communications"
        },
        {
            "fieldname": "contact_phone",
            "label": "Contact Phone",
            "fieldtype": "Data",
            "required": 1,
            "value": booking.contact_phone,
            "description": "Phone number for urgent communications"
        },
        {
            "fieldname": "alternate_contact_name",
            "label": "Alternate Contact Name",
            "fieldtype": "Data",
            "required": 0,
            "value": booking.alternate_contact_name,
            "description": "Name of an alternate contact (optional)"
        },
        {
            "fieldname": "alternate_contact_phone",
            "label": "Alternate Contact Phone",
            "fieldtype": "Data",
            "required": 0,
            "value": booking.alternate_contact_phone,
            "description": "Phone number for the alternate contact"
        }
    ]
    
    # TODO: Override with settings if configured
    
    return contact_fields
