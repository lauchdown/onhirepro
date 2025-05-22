import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for checkout page"""
    
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
        {"label": "Checkout", "url": "/checkout"}
    ]
    
    # Get cart items
    cart = frappe.cache().hget("shopping_cart", frappe.session.user)
    if not cart or not cart.get("items"):
        frappe.local.flags.redirect_location = "/cart"
        raise frappe.Redirect
    
    context.cart = cart
    
    # Get customer details
    if frappe.session.user != "Guest":
        customer = get_customer_details()
        context.customer = customer
    
    # Get booking form field configuration from settings
    context.booking_fields = get_booking_form_fields(settings)
    
    # Get job reference field configuration from settings
    context.job_reference_fields = get_job_reference_fields(settings)
    
    # Get contact details field configuration from settings
    context.contact_fields = get_contact_fields(settings)
    
    return context

def get_customer_details():
    """Get customer details for the logged in user"""
    customer = None
    
    # Get customer linked to the current user
    customer_name = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if customer_name:
        customer = frappe.get_doc("Customer", customer_name)
    
    return customer

def get_booking_form_fields(settings):
    """Get booking form fields configuration from settings"""
    
    # Default booking form fields
    booking_fields = [
        {
            "fieldname": "booking_title",
            "label": "Booking Title",
            "fieldtype": "Data",
            "required": 1,
            "description": "A short title for this booking"
        },
        {
            "fieldname": "booking_start_date",
            "label": "Start Date",
            "fieldtype": "Date",
            "required": 1,
            "default": nowdate(),
            "description": "When do you need the rental items?"
        },
        {
            "fieldname": "booking_end_date",
            "label": "End Date",
            "fieldtype": "Date",
            "required": 1,
            "default": add_days(nowdate(), 7),
            "description": "When will you return the rental items?"
        },
        {
            "fieldname": "booking_notes",
            "label": "Booking Notes",
            "fieldtype": "Text",
            "required": 0,
            "description": "Any additional information about this booking"
        }
    ]
    
    # TODO: Override with settings if configured
    
    return booking_fields

def get_job_reference_fields(settings):
    """Get job reference fields configuration from settings"""
    
    # Default job reference fields
    job_reference_fields = [
        {
            "fieldname": "job_reference_number",
            "label": "Job Reference Number",
            "fieldtype": "Data",
            "required": 0,
            "description": "Your internal reference number for this job"
        },
        {
            "fieldname": "project_name",
            "label": "Project Name",
            "fieldtype": "Data",
            "required": 0,
            "description": "The name of the project these items are for"
        },
        {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Data",
            "required": 0,
            "description": "Department responsible for this booking"
        }
    ]
    
    # TODO: Override with settings if configured
    
    return job_reference_fields

def get_contact_fields(settings):
    """Get contact details fields configuration from settings"""
    
    # Default contact fields
    contact_fields = [
        {
            "fieldname": "contact_name",
            "label": "Contact Name",
            "fieldtype": "Data",
            "required": 1,
            "description": "Name of the primary contact for this booking"
        },
        {
            "fieldname": "contact_email",
            "label": "Contact Email",
            "fieldtype": "Data",
            "required": 1,
            "description": "Email address for booking communications"
        },
        {
            "fieldname": "contact_phone",
            "label": "Contact Phone",
            "fieldtype": "Data",
            "required": 1,
            "description": "Phone number for urgent communications"
        },
        {
            "fieldname": "alternate_contact_name",
            "label": "Alternate Contact Name",
            "fieldtype": "Data",
            "required": 0,
            "description": "Name of an alternate contact (optional)"
        },
        {
            "fieldname": "alternate_contact_phone",
            "label": "Alternate Contact Phone",
            "fieldtype": "Data",
            "required": 0,
            "description": "Phone number for the alternate contact"
        }
    ]
    
    # TODO: Override with settings if configured
    
    return contact_fields
